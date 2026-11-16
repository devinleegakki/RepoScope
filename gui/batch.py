"""多仓库对比页：把几个仓库排在一张表里比健康度。

单仓库分析回答"这个仓库怎么样"，多仓库对比回答"哪个仓库更该先修"。
演示时的用法：把本学期四个作业仓库拖进来，一次跑完，按健康度排序。

TODO(Wyh): ``services.batch`` / ``cli.py`` 的批量入口落地后，
把 ``run_all()`` 内部换成调用它；表格与页面结构不用改。
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from . import dialogs, mock_data
from .contract import RepoSummary, risk_of
from .widgets import LEVEL_COLOR, LEVEL_TEXT, Card, PageHeader

_COLUMNS = (
    ("仓库", lambda row: row.repo_name, Qt.AlignLeft | Qt.AlignVCenter),
    ("提交数", lambda row: f"{row.commits:,}", Qt.AlignCenter),
    ("作者数", lambda row: str(row.authors), Qt.AlignCenter),
    ("健康度", lambda row: f"{row.health_score:.0f}", Qt.AlignCenter),
    ("热点文件", lambda row: str(row.hotspot_count), Qt.AlignCenter),
    ("陈旧文件", lambda row: str(row.stale_count), Qt.AlignCenter),
    ("等级", lambda row: LEVEL_TEXT.get(row.risk_level, row.risk_level), Qt.AlignCenter),
)


class SummaryModel(QAbstractTableModel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[RepoSummary] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == Qt.DisplayRole:
            return _COLUMNS[index.column()][1](row)
        if role == Qt.TextAlignmentRole:
            return int(_COLUMNS[index.column()][2])
        if role == Qt.ForegroundRole and index.column() in (3, 6):
            return QColor(LEVEL_COLOR.get(row.risk_level, "#c9d1d9"))
        if role == Qt.ToolTipRole and index.column() == 0:
            return row.path
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return _COLUMNS[section][0]

    def set_rows(self, rows: Sequence[RepoSummary]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    @property
    def rows(self) -> list[RepoSummary]:
        return list(self._rows)


class BatchPage(QWidget):
    """队列 + 对比表。"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.header = PageHeader(
            "多仓库对比",
            "把几个仓库加进队列，一次分析完，按健康度排在一起看谁最该先修。",
        )
        outer.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)

        queue_card = Card()
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(8)
        title = QLabel("仓库队列")
        title.setObjectName("sectionTitle")
        queue_layout.addWidget(title)

        self.queue = QListWidget()
        self.queue.setObjectName("batchQueue")
        queue_layout.addWidget(self.queue, 1)

        buttons = QHBoxLayout()
        add = QPushButton("添加…")
        add.clicked.connect(self._add)
        remove = QPushButton("移除")
        remove.clicked.connect(self._remove)
        clear = QPushButton("清空")
        clear.clicked.connect(self.queue.clear)
        for button in (add, remove, clear):
            buttons.addWidget(button)
        queue_layout.addLayout(buttons)

        self.run_btn = QPushButton("开始批量分析")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run_all)
        queue_layout.addWidget(self.run_btn)
        body.addWidget(queue_card, 1)

        table_card = Card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)
        head = QHBoxLayout()
        table_title = QLabel("对比结果")
        table_title.setObjectName("sectionTitle")
        self.status = QLabel("队列为空")
        self.status.setObjectName("pageHint")
        head.addWidget(table_title)
        head.addWidget(self.status)
        head.addStretch(1)
        table_layout.addLayout(head)

        self.model = SummaryModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(False)   # 同上：避免表头出现孤立的小 V
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.table, 1)

        self.empty = QLabel(
            "还没有加入仓库。\n点左下「添加…」选一个本地 Git 仓库，可以加多个，再点「开始批量分析」。"
        )
        self.empty.setObjectName("emptyState")
        self.empty.setAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.empty, 1)
        self._sync_empty()
        body.addWidget(table_card, 3)

        outer.addLayout(body, 1)

    # -- 队列 ------------------------------------------------------------
    def _add(self) -> None:
        selected = dialogs.ask_repository(self)
        if not selected:
            return
        if self.queue.findItems(selected, Qt.MatchExactly):
            dialogs.show_info(self, "已在队列中", selected)
            return
        self.queue.addItem(selected)

    def _remove(self) -> None:
        for item in self.queue.selectedItems():
            self.queue.takeItem(self.queue.row(item))

    def paths(self) -> list[str]:
        return [self.queue.item(i).text() for i in range(self.queue.count())]

    # -- 批量分析 --------------------------------------------------------
    def run_all(self) -> None:
        """逐个仓库跑一次分析，汇总成对比表。

        TODO(Wyh): 换成 ``batch.analyse(paths)``，并用 QThread 串起来。
        壳阶段同步跑是因为每个仓库只要几百毫秒；仓库多了会卡界面，
        所以这里硬限制 20 个，并给状态行提示。
        """
        paths = self.paths()
        if not paths:
            dialogs.show_info(self, "队列为空", "请先添加至少一个仓库。")
            return
        if len(paths) > 20:
            dialogs.show_error(self, "队列过长", "一次最多分析 20 个仓库。")
            return

        summaries: list[RepoSummary] = []
        failed: list[str] = []
        for path in paths:
            if not (Path(path) / ".git").exists():
                summaries.append(RepoSummary(
                    repo_name=f"{Path(path).name}（无法读取）",
                    path=path,
                    risk_level="high",
                ))
                failed.append(Path(path).name)
                continue
            try:
                view = mock_data.build(path)
            except Exception:  # 单个失败不影响其它仓库
                summaries.append(RepoSummary(
                    repo_name=f"{Path(path).name}（无法读取）",
                    path=path,
                    risk_level="high",
                ))
                failed.append(Path(path).name)
                continue
            summaries.append(RepoSummary(
                repo_name=view.snapshot.repo_name,
                path=path,
                commits=view.total_commits,
                authors=view.author_count,
                health_score=view.health_score,
                hotspot_count=len(view.hotspot_files),
                stale_count=len(view.stale_files),
                risk_level=risk_of(view.health_score),
            ))

        summaries.sort(key=lambda row: row.health_score)
        self.model.set_rows(summaries)
        self._sync_empty()
        worst = summaries[0] if summaries else None
        message = f"已分析 {len(summaries)} 个仓库"
        if worst is not None and not failed:
            message += f" · 最需要修的是 {worst.repo_name}（{worst.health_score:.0f} 分）"
        if failed:
            message += f" · {len(failed)} 个无法读取：{', '.join(failed)}"
        self.status.setText(message)

    def _sync_empty(self) -> None:
        """有结果就显示表格，没结果就显示一句说明，别留一张空表让人以为坏了。"""
        has_rows = self.model.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty.setVisible(not has_rows)
