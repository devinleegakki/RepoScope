"""仓库选择页：路径输入、合法性校验、最近打开的仓库。

这一页独立出来（组长文档 4.1）而不是塞进顶部栏，是因为"选仓库"是这个工具
唯一必须前置的一步：路径不合法就没法分析。放在第一页，用户打开软件不会问
"我该从哪开始"。

校验只做三件事，够用且够快：
1. 目录是否存在
2. 是否是 Git 仓库（有 ``.git``）
3. 是否是一个可读的目录（权限）

更深入的问题（空仓库、没有提交）留给后台分析时报告，不在选路径阶段假装能查清。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import dialogs
from .widgets import Card, PageHeader

_RECENT_KEY = "recent_repositories"
_MAX_RECENT = 6


class SelectPage(QWidget):
    """选仓库 → 校验 → 开始分析。"""

    analyze_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader(
            "仓库选择",
            "选择一个本地 Git 仓库目录。全程离线读取，不会上传任何代码，也不需要网络。",
        )
        outer.addWidget(self.header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        label = QLabel("仓库路径")
        label.setObjectName("formLabel")
        card_layout.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("例如 D:/projects/RepoScope")
        self.path_edit.textChanged.connect(self._validate)
        row.addWidget(self.path_edit, 1)

        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        card_layout.addLayout(row)

        self.status = QLabel("还没有选择目录")
        self.status.setObjectName("pageHint")
        self.status.setWordWrap(True)
        card_layout.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._emit_analyze)
        actions.addWidget(self.analyze_btn)

        self.settings_hint = QLabel("阈值与提交规范在「分析配置」里改")
        self.settings_hint.setObjectName("pageHint")
        actions.addWidget(self.settings_hint)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        outer.addWidget(card)

        recent_card = Card()
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(20, 16, 20, 16)
        recent_layout.setSpacing(8)
        title = QLabel("最近打开")
        title.setObjectName("sectionTitle")
        recent_layout.addWidget(title)

        self.recent = QListWidget()
        self.recent.setObjectName("recentList")
        self.recent.itemDoubleClicked.connect(self._pick_recent)
        recent_layout.addWidget(self.recent, 1)
        outer.addWidget(recent_card, 1)

        self._load_recent()

    # -- 交互 ------------------------------------------------------------
    def _browse(self) -> None:
        selected = dialogs.ask_repository(self)
        if selected:
            self.path_edit.setText(selected)

    def _emit_analyze(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            return
        self.remember(path)
        self.analyze_requested.emit(path)

    def _pick_recent(self, item: QListWidgetItem) -> None:
        path = item.data(0x0100) or item.text()
        self.path_edit.setText(str(path))

    def _validate(self) -> None:
        """路径一变就校验。校验结果直接写进状态行，不弹窗打断输入。"""
        raw = self.path_edit.text().strip()
        if not raw:
            self.status.setText("还没有选择目录")
            self.analyze_btn.setEnabled(False)
            return
        path = Path(raw)
        if not path.exists():
            self.status.setText("✗ 这个路径不存在")
            self.analyze_btn.setEnabled(False)
            return
        if not path.is_dir():
            self.status.setText("✗ 这里是一个文件，不是目录。请选择仓库的根目录。")
            self.analyze_btn.setEnabled(False)
            return
        if not (path / ".git").exists():
            self.status.setText("✗ 目录里没有 .git，这不是一个 Git 仓库（可能是它的子目录）")
            self.analyze_btn.setEnabled(False)
            return
        self.status.setText(f"✓ 已识别 Git 仓库：{path.name}")
        self.analyze_btn.setEnabled(True)

    # -- 最近打开 --------------------------------------------------------
    def _load_recent(self) -> None:
        settings = QSettings()
        for path in settings.value(_RECENT_KEY, [], type=list) or []:
            self._add_recent_row(str(path))
        if self.recent.count() == 0:
            hint = QListWidgetItem("还没有分析过仓库，选一个目录开始")
            hint.setFlags(Qt.NoItemFlags)
            self.recent.addItem(hint)

    def _add_recent_row(self, path: str) -> None:
        item = QListWidgetItem(path)
        item.setData(0x0100, path)
        self.recent.addItem(item)

    def remember(self, path: str) -> None:
        """把打开过的仓库记下来，下次启动直接点。"""
        settings = QSettings()
        items = [p for p in (settings.value(_RECENT_KEY, [], type=list) or []) if p != path]
        items.insert(0, path)
        settings.setValue(_RECENT_KEY, items[:_MAX_RECENT])

        self.recent.clear()
        for existing in items[:_MAX_RECENT]:
            self._add_recent_row(existing)
