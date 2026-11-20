"""repository

Notes 4.1）Notes"repository"Notes
analysis
"start"。

Notes
1. Notes
2. Notes Git repository ``.git``）
3. Notes

repository
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
    """repository → Notes → analysis"""

    analyze_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader(
            "repository",
            "select Git repository",
        )
        outer.addWidget(self.header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        label = QLabel("repository")
        label.setObjectName("formLabel")
        card_layout.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("e.g. D:/projects/RepoScope")
        self.path_edit.textChanged.connect(self._validate)
        row.addWidget(self.path_edit, 1)

        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        card_layout.addLayout(row)

        self.status = QLabel("select")
        self.status.setObjectName("pageHint")
        self.status.setWordWrap(True)
        card_layout.addWidget(self.status)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.analyze_btn = QPushButton("analysis")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._emit_analyze)
        actions.addWidget(self.analyze_btn)

        self.settings_hint = QLabel("commits")
        self.settings_hint.setObjectName("pageHint")
        actions.addWidget(self.settings_hint)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        outer.addWidget(card)

        recent_card = Card()
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(20, 16, 20, 16)
        recent_layout.setSpacing(8)
        title = QLabel("current")
        title.setObjectName("sectionTitle")
        recent_layout.addWidget(title)

        self.recent = QListWidget()
        self.recent.setObjectName("recentList")
        self.recent.itemDoubleClicked.connect(self._pick_recent)
        recent_layout.addWidget(self.recent, 1)
        outer.addWidget(recent_card, 1)

        self._load_recent()

    # -- Notes ------------------------------------------------------------
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
        """path"""
        raw = self.path_edit.text().strip()
        if not raw:
            self.status.setText("select")
            self.analyze_btn.setEnabled(False)
            return
        path = Path(raw)
        if not path.exists():
            self.status.setText("✗ Path does not exist")
            self.analyze_btn.setEnabled(False)
            return
        if not path.is_dir():
            self.status.setText("✗ The selected path is not a directory")
            self.analyze_btn.setEnabled(False)
            return
        if not (path / ".git").exists():
            self.status.setText("✗ No .git directory found; choose a Git repository")
            self.analyze_btn.setEnabled(False)
            return
        self.status.setText(f"✓ Git repository found: {path.name}")
        self.analyze_btn.setEnabled(True)

    # -- current --------------------------------------------------------
    def _load_recent(self) -> None:
        settings = QSettings()
        for path in settings.value(_RECENT_KEY, [], type=list) or []:
            self._add_recent_row(str(path))
        if self.recent.count() == 0:
            hint = QListWidgetItem("No recent repositories")
            hint.setFlags(Qt.NoItemFlags)
            self.recent.addItem(hint)

    def _add_recent_row(self, path: str) -> None:
        item = QListWidgetItem(path)
        item.setData(0x0100, path)
        self.recent.addItem(item)

    def remember(self, path: str) -> None:
        """repository"""
        settings = QSettings()
        items = [p for p in (settings.value(_RECENT_KEY, [], type=list) or []) if p != path]
        items.insert(0, path)
        settings.setValue(_RECENT_KEY, items[:_MAX_RECENT])

        self.recent.clear()
        for existing in items[:_MAX_RECENT]:
            self._add_recent_row(existing)



