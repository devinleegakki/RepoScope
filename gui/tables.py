"""数据分析页：热点文件、大文件、陈旧文件三个榜单。

用 ``QAbstractTableModel`` + ``QTableView``（不是 ``QTableWidget``）：

* 数据量大了也不掉帧，因为视图只取可见行；
* 排序和筛选交给 ``QSortFilterProxyModel``，模型只负责"第 n 行第 m 列是什么"；
* 这是 Qt 的 Model/View 架构，报告里可以写成技术点，而 QTableWidget 只是"摆字符串"。
"""

from __future__ import annotations

from typing import Callable, Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTabWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisView, FileStat
from .widgets import Card, PageHeader


def human_size(size_bytes: int) -> str:
    """把字节数变成人能读的大小，例如 ``1.4 MB``。"""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def human_lines(count: int) -> str:
    if count >= 10_000:
        return f"{count / 1000:.1f}k 行"
    return f"{count:,} 行"


_COLUMNS: dict[str, tuple[str, Callable[[FileStat], str]]] = {
    "path": ("文件", lambda row: row.path),
    "change_count": ("修改次数", lambda row: str(row.change_count)),
    "author_count": ("作者数", lambda row: str(row.author_count)),
    "changed_lines": ("累计改动", lambda row: human_lines(row.changed_lines)),
    "size": ("大小", lambda row: human_size(row.size_bytes)),
    "type": ("类型", lambda row: row.file_type or "—"),
    "days": ("距今天数", lambda row: str(row.days_since_change)),
}


class FileTableModel(QAbstractTableModel):
    """把 ``FileStat`` 列表包成 Qt 模型。列由构造函数决定，一个模型三种用法。"""

    def __init__(self, columns: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._columns = list(columns)
        self._rows: list[FileStat] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._columns[index.column()]
        if role == Qt.DisplayRole:
            return _COLUMNS[key][1](row)
        if role == Qt.TextAlignmentRole and key != "path":
            return int(Qt.AlignCenter)
        if role == Qt.ForegroundRole and key == "days" and row.days_since_change >= 180:
            return QColor("#EF9F27")
        if role == Qt.ToolTipRole and key == "changed_lines" and row.changed_lines == 0:
            return "该字段待后端提供（metrics.py 的 changed_lines）"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return _COLUMNS[self._columns[section]][0]

    def set_rows(self, rows: Sequence[FileStat]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()


class _RankTab(QWidget):
    """一个榜单 = 模型 + 过滤器 + 视图。三个榜单复用同一个类。"""

    def __init__(self, columns: Sequence[str], empty_hint: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        self.model = FileTableModel(columns, self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(0)          # 按文件路径过滤
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        # 关掉表头的排序箭头：QSS 换了表头配色后，Qt 默认画的箭头会变成一个
        # 孤立的小 V 浮在表头文字上方，看起来像界面出了 bug。排序功能照旧。
        self.view.horizontalHeader().setSortIndicatorShown(False)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.view, 1)

        self.empty = QLabel(empty_hint)
        self.empty.setObjectName("pageHint")
        self.empty.setVisible(False)
        layout.addWidget(self.empty)

    def set_rows(self, rows: Sequence[FileStat], empty_hint: str) -> None:
        self.model.set_rows(rows)
        self.empty.setText(empty_hint)
        self.empty.setVisible(len(rows) == 0)


class FilesPage(QWidget):
    """数据分析页：三个榜单 + 一个全局筛选框。"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("按文件名筛选…")
        self.search.textChanged.connect(self._apply_filter)

        self.header = PageHeader("数据分析", "尚未分析任何仓库")
        self.header.add_right(self.search)
        outer.addWidget(self.header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        head = QHBoxLayout()
        note = QLabel("点表头可排序；三个榜单的判定阈值在「分析配置」里改")
        note.setObjectName("pageHint")
        head.addWidget(note)
        head.addStretch(1)
        card_layout.addLayout(head)

        self.tabs = QTabWidget()
        self.hot = _RankTab(["path", "change_count", "author_count", "changed_lines"],
                            "没有文件达到热点阈值（可在分析配置里调低）")
        self.large = _RankTab(["path", "size", "type", "change_count"],
                              "没有文件超过大文件阈值")
        self.stale = _RankTab(["path", "days", "change_count", "size"],
                              "没有文件超过陈旧天数阈值")
        self.tabs.addTab(self.hot, "热点文件")
        self.tabs.addTab(self.large, "大文件")
        self.tabs.addTab(self.stale, "陈旧文件")
        card_layout.addWidget(self.tabs, 1)
        outer.addWidget(card, 1)

    def _apply_filter(self, text: str) -> None:
        for tab in (self.hot, self.large, self.stale):
            tab.proxy.setFilterFixedString(text)

    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self.hot.set_rows(view.hotspot_files, "没有文件达到热点阈值（可在分析配置里调低）")
        self.large.set_rows(view.large_files, "没有文件超过大文件阈值")
        self.stale.set_rows(view.stale_files, "没有文件超过陈旧天数阈值")
        self.tabs.setTabText(0, f"热点文件 ({len(view.hotspot_files)})")
        self.tabs.setTabText(1, f"大文件 ({len(view.large_files)})")
        self.tabs.setTabText(2, f"陈旧文件 ({len(view.stale_files)})")
        self.header.set_hint(
            f"热点 {len(view.hotspot_files)} · 大文件 {len(view.large_files)} · "
            f"陈旧 {len(view.stale_files)} · 共 {view.file_count:,} 个文件被扫描"
        )
