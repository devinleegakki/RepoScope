"""anti-patterns"Notes"。

Notes GUI Notes"Notes 3 files"，
rules**Notes**：

    Notes ← rulesrules.py Notes pattern / Notes
    Notes   ← Notes
    configuration ← configuration
    Notes ← Notes

Notes ``Warning`` files
display"pending rules.py Notes"，Notes
Notes"Notes"Notes
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisView, Warning
from .widgets import LEVEL_TEXT, SEVERITY_TEXT, Badge, Card, PageHeader

_EVIDENCE_FIELDS = (
    ("Condition", "condition"),
    ("Observed value", "actual"),
    ("Threshold", "threshold"),
    ("Suggested action", "action"),
)


class PatternPage(QWidget):
    """anti-patterns"""

    def __init__(self) -> None:
        super().__init__()
        self._warnings: list[Warning] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.filter = QComboBox()
        self.filter.addItems(["All levels", "High", "Medium", "Low"])
        self.filter.currentIndexChanged.connect(self._refresh_list)

        self.header = PageHeader("Anti-pattern center", "Review repository findings")
        self.header.add_right(self.filter)
        outer.addWidget(self.header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = Card()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        self.list_title = QLabel("Findings")
        self.list_title.setObjectName("sectionTitle")
        left_layout.addWidget(self.list_title)
        self.list = QListWidget()
        self.list.setObjectName("patternList")
        self.list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list.setWordWrap(True)
        self.list.setTextElideMode(Qt.ElideNone)
        self.list.setMinimumHeight(220)
        self.list.currentRowChanged.connect(self._show_detail)
        left_layout.addWidget(self.list, 1)
        splitter.addWidget(left)

        self.detail = _DetailCard()
        splitter.addWidget(self.detail)
        splitter.setSizes([280, 640])
        outer.addWidget(splitter, 1)

    # -- Notes ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self._warnings = list(view.warnings)
        counts = {level: 0 for level in ("high", "medium", "low")}
        for warning in self._warnings:
            counts[warning.severity] = counts.get(warning.severity, 0) + 1
        self.header.set_hint(
            f"{len(self._warnings)} findings · high {counts['high']} · "
            f"medium {counts['medium']} · low {counts['low']}"
        )
        self.list_title.setText(f"Findings ({len(self._warnings)})")
        self.filter.setItemText(0, f"All levels ({len(self._warnings)})")
        self.filter.setItemText(1, f"High ({counts['high']})")
        self.filter.setItemText(2, f"Medium ({counts['medium']})")
        self.filter.setItemText(3, f"Low ({counts['low']})")
        self._refresh_list()

    def _visible(self) -> list[Warning]:
        index = self.filter.currentIndex()
        if index == 0:
            return self._warnings
        wanted = ("high", "medium", "low")[index - 1]
        return [w for w in self._warnings if w.severity == wanted]

    def _refresh_list(self) -> None:
        self.list.clear()
        rows = self._visible()
        if not rows:
            item = QListWidgetItem("No findings for this filter")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            self.detail.show_warning(None)
            return
        for warning in rows:
            text = f"{SEVERITY_TEXT.get(warning.severity, warning.severity)}｜{warning.rule}"
            item = QListWidgetItem(f"{text}\n{warning.message}")
            item.setForeground(QColor("#c9d1d9"))
            item.setData(Qt.UserRole, warning)
            item.setToolTip(f"{warning.message}\nTarget: {warning.target or '—'}")
            self.list.addItem(item)
            item.setSizeHint(QSize(0, 64))
            if not warning.has_evidence:
                item.setToolTip("pending")
        self.list.setCurrentRow(0)

    def _show_detail(self, row: int) -> None:
        item = self.list.item(row)
        if item is None or item.data(Qt.UserRole) is None:
            self.detail.show_warning(None)
            return
        self.detail.show_warning(item.data(Qt.UserRole))


class _DetailCard(Card):
    """rules"""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        self.title = QLabel("—")
        self.title.setObjectName("sectionTitle")
        self.badge = Badge("—", "low")
        head.addWidget(self.title)
        head.addWidget(self.badge, 0, Qt.AlignVCenter)
        head.addStretch(1)
        layout.addLayout(head)

        self.message = QLabel("Select a finding to review its evidence.")
        self.message.setObjectName("detailMessage")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        self.form = QFormLayout()
        self.form.setContentsMargins(0, 6, 0, 0)
        self.form.setSpacing(8)
        self.form.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._values: dict[str, QLabel] = {}
        for label, key in _EVIDENCE_FIELDS:
            name = QLabel(label)
            name.setObjectName("formLabel")
            value = QLabel("—")
            value.setObjectName("formValue")
            value.setWordWrap(True)
            self._values[key] = value
            self.form.addRow(name, value)
        layout.addLayout(self.form)

        self.target = QLabel("")
        self.target.setObjectName("pageHint")
        self.target.setWordWrap(True)
        layout.addWidget(self.target)

        self.pending = QLabel("")
        self.pending.setObjectName("pendingNote")
        self.pending.setWordWrap(True)
        self.pending.setVisible(False)
        layout.addWidget(self.pending)
        layout.addStretch(1)

    def show_warning(self, warning: Warning | None) -> None:
        if warning is None:
            self.title.setText("—")
            self.badge.setText("—")
            self.message.setText("Select a finding to review its evidence.")
            for value in self._values.values():
                value.setText("—")
            self.target.setText("")
            self.pending.setVisible(False)
            return

        self.title.setText(warning.rule)
        self.badge.setText(LEVEL_TEXT.get(warning.severity, warning.severity))
        self.badge.set_level(warning.severity)
        self.message.setText(warning.message)
        for _, key in _EVIDENCE_FIELDS:
            raw = getattr(warning, key) or ""
            self._values[key].setText(raw or "pending")
        self.target.setText(f"Target: {warning.target or '—'}")

        missing = [label for label, key in _EVIDENCE_FIELDS if not getattr(warning, key)]
        if missing:
            self.pending.setText(
                "Missing evidence: " + ", ".join(missing)
            )
            self.pending.setVisible(True)
        else:
            self.pending.setVisible(False)



