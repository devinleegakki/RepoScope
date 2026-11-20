"""Repositorytext：Pathtext、validtextcheck、Recently openedtextrepository。

text（text 4.1）text，text"textrepository"text
text：Pathtextvalidtextanalyze。text，text
"text"。

checktext，text：
1. directorytext
2. text Git repository（text ``.git``）
3. textdirectory（text）

text（textrepository、textcommits）textanalyzetextreport，textPathtext。
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
    """textrepository → check → Start analysis。"""

    analyze_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader(
            "Repository",
            "Selecttextlocal Git repositorydirectory。text，text，text。",
        )
        outer.addWidget(self.header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        label = QLabel("repositoryPath")
        label.setObjectName("formLabel")
        card_layout.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("text D:/projects/RepoScope")
        self.path_edit.textChanged.connect(self._validate)
        row.addWidget(self.path_edit, 1)

        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        card_layout.addLayout(row)

        self.status = QLabel("textSelectdirectory")
        self.status.setObjectName("pageHint")
        self.status.setWordWrap(True)
        card_layout.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton("Start analysis")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._emit_analyze)
        actions.addWidget(self.analyze_btn)

        self.settings_hint = QLabel("thresholdtextCommit conventiontext「Analysis Settings」text")
        self.settings_hint.setObjectName("pageHint")
        actions.addWidget(self.settings_hint)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        outer.addWidget(card)

        recent_card = Card()
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(20, 16, 20, 16)
        recent_layout.setSpacing(8)
        title = QLabel("Recently opened")
        title.setObjectName("sectionTitle")
        recent_layout.addWidget(title)

        self.recent = QListWidget()
        self.recent.setObjectName("recentList")
        self.recent.itemDoubleClicked.connect(self._pick_recent)
        recent_layout.addWidget(self.recent, 1)
        outer.addWidget(recent_card, 1)

        self._load_recent()

    # -- text ------------------------------------------------------------
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
        """Pathtextcheck。checktext，text。"""
        raw = self.path_edit.text().strip()
        if not raw:
            self.status.setText("textSelectdirectory")
            self.analyze_btn.setEnabled(False)
            return
        path = Path(raw)
        if not path.exists():
            self.status.setText("✗ textPathdoes not exist")
            self.analyze_btn.setEnabled(False)
            return
        if not path.is_dir():
            self.status.setText("✗ textfiles，textdirectory。textSelectrepositorytextroot directory。")
            self.analyze_btn.setEnabled(False)
            return
        if not (path / ".git").exists():
            self.status.setText("✗ directorytext .git，text Git repository（textsubdirectory）")
            self.analyze_btn.setEnabled(False)
            return
        self.status.setText(f"✓ text Git repository：{path.name}")
        self.analyze_btn.setEnabled(True)

    # -- Recently opened --------------------------------------------------------
    def _load_recent(self) -> None:
        settings = QSettings()
        for path in settings.value(_RECENT_KEY, [], type=list) or []:
            self._add_recent_row(str(path))
        if self.recent.count() == 0:
            hint = QListWidgetItem("textanalyzetextrepository，textdirectorytext")
            hint.setFlags(Qt.NoItemFlags)
            self.recent.addItem(hint)

    def _add_recent_row(self, path: str) -> None:
        item = QListWidgetItem(path)
        item.setData(0x0100, path)
        self.recent.addItem(item)

    def remember(self, path: str) -> None:
        """textrepositorytext，text。"""
        settings = QSettings()
        items = [p for p in (settings.value(_RECENT_KEY, [], type=list) or []) if p != path]
        items.insert(0, path)
        settings.setValue(_RECENT_KEY, items[:_MAX_RECENT])

        self.recent.clear()
        for existing in items[:_MAX_RECENT]:
            self._add_recent_row(existing)
