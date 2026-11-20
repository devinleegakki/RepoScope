"""repository

repository"repository"，repository"repository"。
repository

TODO(Wyh): ``services.batch`` / ``cli.py`` Notes
Notes ``run_all()`` Notes
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
    ("repository", lambda row: row.repo_name, Qt.AlignLeft | Qt.AlignVCenter),
    ("commits", lambda row: f"{row.commits:,}", Qt.AlignCenter),
    ("authors", lambda row: str(row.authors), Qt.AlignCenter),
    ("health", lambda row: f"{row.health_score:.0f}", Qt.AlignCenter),
    ("Hotspots", lambda row: str(row.hotspot_count), Qt.AlignCenter),
    ("Stale files", lambda row: str(row.stale_count), Qt.AlignCenter),
    ("Risk", lambda row: LEVEL_TEXT.get(row.risk_level, row.risk_level), Qt.AlignCenter),
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
    """queue + Notes"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.header = PageHeader(
            "Repository comparison",
            "Analyze multiple repositories side by side",
        )
        outer.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)

        queue_card = Card()
        queue_layout = QVBoxLayout(queue_card)
        queue_layout.setContentsMargins(12, 12, 12, 12)
        queue_layout.setSpacing(8)
        title = QLabel("Repository queue")
        title.setObjectName("sectionTitle")
        queue_layout.addWidget(title)

        self.queue = QListWidget()
        self.queue.setObjectName("batchQueue")
        queue_layout.addWidget(self.queue, 1)

        buttons = QHBoxLayout()
        add = QPushButton("Add")
        add.clicked.connect(self._add)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.queue.clear)
        for button in (add, remove, clear):
            buttons.addWidget(button)
        queue_layout.addLayout(buttons)

        self.run_btn = QPushButton("Compare repositories")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run_all)
        queue_layout.addWidget(self.run_btn)
        body.addWidget(queue_card, 1)

        table_card = Card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)
        head = QHBoxLayout()
        table_title = QLabel("Comparison results")
        table_title.setObjectName("sectionTitle")
        self.status = QLabel("No results yet")
        self.status.setObjectName("pageHint")
        head.addWidget(table_title)
        head.addWidget(self.status)
        head.addStretch(1)
        table_layout.addLayout(head)

        self.model = SummaryModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(False)   # Notes V
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.table, 1)

        self.empty = QLabel(
            "Add Git repositories\nUse the Add button to build a comparison queue"
        )
        self.empty.setObjectName("emptyState")
        self.empty.setAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.empty, 1)
        self._sync_empty()
        body.addWidget(table_card, 3)

        outer.addLayout(body, 1)

    # -- queue ------------------------------------------------------------
    def _add(self) -> None:
        selected = dialogs.ask_repository(self)
        if not selected:
            return
        if self.queue.findItems(selected, Qt.MatchExactly):
            dialogs.show_info(self, "queue", selected)
            return
        self.queue.addItem(selected)

    def _remove(self) -> None:
        for item in self.queue.selectedItems():
            self.queue.takeItem(self.queue.row(item))

    def paths(self) -> list[str]:
        return [self.queue.item(i).text() for i in range(self.queue.count())]

    # -- analysis --------------------------------------------------------
    def run_all(self) -> None:
        """repository

        TODO(Wyh): Notes ``batch.analyse(paths)``，Notes QThread Notes
        repository
        Notes 20 information
        """
        paths = self.paths()
        if not paths:
            dialogs.show_info(self, "Repository queue", "Add at least one repository first.")
            return
        if len(paths) > 20:
            dialogs.show_error(self, "Repository queue", "You can compare at most 20 repositories.")
            return

        summaries: list[RepoSummary] = []
        failed: list[str] = []
        for path in paths:
            if not (Path(path) / ".git").exists():
                summaries.append(RepoSummary(
                    repo_name=f"{Path(path).name} (missing .git)",
                    path=path,
                    risk_level="high",
                ))
                failed.append(Path(path).name)
                continue
            try:
                view = mock_data.build(path)
            except Exception:  # repository
                summaries.append(RepoSummary(
                    repo_name=f"{Path(path).name} (analysis failed)",
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
        message = f"Compared {len(summaries)} repositories"
        if worst is not None and not failed:
            message += f" · lowest health: {worst.repo_name} ({worst.health_score:.0f})"
        if failed:
            message += f" · {len(failed)} failed: {', '.join(failed)}"
        self.status.setText(message)

    def _sync_empty(self) -> None:
        """information"""
        has_rows = self.model.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty.setVisible(not has_rows)



