"""Data Analysistext：Hot files、Large files、Stale filestext。

text ``QAbstractTableModel`` + ``QTableView``（text ``QTableWidget``）：

* text，text；
* text ``QSortFilterProxyModel``，text"text n text m text"；
* text Qt text Model/View text，reporttext，text QTableWidget text"text"。
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
    """text，text ``1.4 MB``。"""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def human_lines(count: int) -> str:
    if count >= 10_000:
        return f"{count / 1000:.1f}k text"
    return f"{count:,} text"


_COLUMNS: dict[str, tuple[str, Callable[[FileStat], str]]] = {
    "path": ("files", lambda row: row.path),
    "change_count": ("text", lambda row: str(row.change_count)),
    "author_count": ("author count", lambda row: str(row.author_count)),
    "changed_lines": ("text", lambda row: human_lines(row.changed_lines)),
    "size": ("text", lambda row: human_size(row.size_bytes)),
    "type": ("text", lambda row: row.file_type or "—"),
    "days": ("text", lambda row: str(row.days_since_change)),
}


class FileTableModel(QAbstractTableModel):
    """text ``FileStat`` text Qt text。text，text。"""

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
            return "textNot provided by backend（metrics.py text changed_lines）"
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
    """text = text + text + text。text。"""

    def __init__(self, columns: Sequence[str], empty_hint: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        self.model = FileTableModel(columns, self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(0)          # textfilesPathtext
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        # text：QSS text，Qt defaulttext
        # text V text，text bug。text。
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
    """Data Analysistext：text + text。"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("textfilestext…")
        self.search.textChanged.connect(self._apply_filter)

        self.header = PageHeader("Data Analysis", "No repository analyzed yet")
        self.header.add_right(self.search)
        outer.addWidget(self.header)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        head = QHBoxLayout()
        note = QLabel("text；textthresholdtext「Analysis Settings」text")
        note.setObjectName("pageHint")
        head.addWidget(note)
        head.addStretch(1)
        card_layout.addLayout(head)

        self.tabs = QTabWidget()
        self.hot = _RankTab(["path", "change_count", "author_count", "changed_lines"],
                            "textfilestextthreshold（textAnalysis Settingstext）")
        self.large = _RankTab(["path", "size", "type", "change_count"],
                              "textfilestextLarge filesthreshold")
        self.stale = _RankTab(["path", "days", "change_count", "size"],
                              "textfilestextthreshold")
        self.tabs.addTab(self.hot, "Hot files")
        self.tabs.addTab(self.large, "Large files")
        self.tabs.addTab(self.stale, "Stale files")
        card_layout.addWidget(self.tabs, 1)
        outer.addWidget(card, 1)

    def _apply_filter(self, text: str) -> None:
        for tab in (self.hot, self.large, self.stale):
            tab.proxy.setFilterFixedString(text)

    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self.hot.set_rows(view.hotspot_files, "textfilestextthreshold（textAnalysis Settingstext）")
        self.large.set_rows(view.large_files, "textfilestextLarge filesthreshold")
        self.stale.set_rows(view.stale_files, "textfilestextthreshold")
        self.tabs.setTabText(0, f"Hot files ({len(view.hotspot_files)})")
        self.tabs.setTabText(1, f"Large files ({len(view.large_files)})")
        self.tabs.setTabText(2, f"Stale files ({len(view.stale_files)})")
        self.header.set_hint(
            f"text {len(view.hotspot_files)} · Large files {len(view.large_files)} · "
            f"text {len(view.stale_files)} · text {view.file_count:,} textfilestext"
        )
