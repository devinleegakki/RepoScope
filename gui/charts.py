"""authors + Notes

Notes"Notes"，Notes"current"。
``recent_90d_share``（current 90 commits"high"Notes
display"—"，Notes
"""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisView, AuthorStat
from .plotting import AuthorBarChart
from .widgets import Card, PageHeader

_COLUMNS = (
    ("authors", lambda row: row.name, Qt.AlignLeft | Qt.AlignVCenter),
    ("commits", lambda row: str(row.commits), Qt.AlignCenter),
    ("Insertions", lambda row: f"+{row.insertions:,}", Qt.AlignCenter),
    ("Deletions", lambda row: f"-{row.deletions:,}", Qt.AlignCenter),
    ("commits", lambda row: f"{row.share:.0%}", Qt.AlignCenter),
    (
        "Recent 90-day share",
        lambda row: "—" if row.recent_90d_share < 0 else f"{row.recent_90d_share:.0%}",
        Qt.AlignCenter,
    ),
)


class AuthorTableModel(QAbstractTableModel):
    """``AuthorStat`` Notes → Qt Notes"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[AuthorStat] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        title, getter, _ = _COLUMNS[index.column()]
        if role == Qt.DisplayRole:
            return getter(row)
        if role == Qt.TextAlignmentRole:
            return int(_COLUMNS[index.column()][2])
        if role == Qt.ForegroundRole and title == "Recent 90-day share":
            if row.recent_90d_share < 0:
                return QColor("#6e7681")
            if row.recent_90d_share < 0.2:
                return QColor("#EF9F27")
        if role == Qt.ToolTipRole and title == "Recent 90-day share" and row.recent_90d_share < 0:
            return "Recent activity data is unavailable"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return _COLUMNS[section][0]

    def set_rows(self, rows: Sequence[AuthorStat]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()


class AuthorsPage(QWidget):
    """authors"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader("Author contributions", "Repository activity by author")
        outer.addWidget(self.header)

        chart_card = Card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(12, 10, 12, 10)
        chart_layout.setSpacing(6)
        self.chart = AuthorBarChart()
        self.chart.setMinimumHeight(200)
        chart_layout.addWidget(self.chart, 1)
        outer.addWidget(chart_card, 2)

        table_card = Card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 10, 12, 10)
        table_layout.setSpacing(6)
        note = QLabel("Top three contributors and their commit activity")
        note.setObjectName("pageHint")
        table_layout.addWidget(note)

        self.model = AuthorTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table_layout.addWidget(self.table, 1)
        outer.addWidget(table_card, 3)

    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        authors = list(view.author_stats)
        self.model.set_rows(authors)
        self.chart.set_authors([(a.name, a.commits) for a in authors])

        if not authors:
            self.header.set_hint("No author activity found")
            return
        top = authors[0]
        concentration = ", ".join(
            f"{a.name} {a.share:.0%}" for a in authors[:3]
        )
        self.header.set_hint(
            f"{len(authors)} authors · {top.name} contributes {top.share:.0%} of commits "
            f"({top.commits:,}) · Top three: {concentration}"
        )



