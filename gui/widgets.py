"""text。

text：text、text、Leveltext，
text"text 13px、textreporttext 14px"text，
text。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Level → text。text，text。
LEVEL_COLOR = {
    "high": "#F09595",
    "medium": "#EF9F27",
    "low": "#7FD1A0",
}

LEVEL_TEXT = {
    "high": "High risk",
    "medium": "Medium risk",
    "low": "Good",
}

SEVERITY_TEXT = {
    "high": "text",
    "medium": "text",
    "low": "text",
}


class Card(QFrame):
    """text。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class MetricCard(Card):
    """text：text，text，textNotice。"""

    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(2)

        label = QLabel(title)
        label.setObjectName("metricLabel")
        self._value = QLabel("—")
        self._value.setObjectName("metricValue")
        self._hint = QLabel(hint)
        self._hint.setObjectName("metricHint")

        layout.addWidget(label)
        layout.addWidget(self._value)
        layout.addWidget(self._hint)
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def set_value(self, text: str, hint: str | None = None) -> None:
        self._value.setText(text)
        if hint is not None:
            self._hint.setText(hint)

    def set_tone(self, level: str) -> None:
        """textLeveltext（high / medium / low）。"""
        color = LEVEL_COLOR.get(level)
        self._value.setStyleSheet(f"color: {color};" if color else "")


class Badge(QLabel):
    """texttags：RiskLevel、text。"""

    def __init__(self, text: str = "", level: str = "low") -> None:
        super().__init__(text)
        self.setObjectName("badge")
        self.setAlignment(Qt.AlignCenter)
        self.set_level(level)

    def set_level(self, level: str) -> None:
        color = LEVEL_COLOR.get(level, "#8b949e")
        self.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:9px;"
            "padding:1px 8px; font-size:11px;"
        )


class PageHeader(QWidget):
    """text：text + text。text（text、text）。"""

    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self._title = QLabel(title)
        self._title.setObjectName("pageTitle")
        row.addWidget(self._title)
        row.addStretch(1)
        self._right = row
        outer.addLayout(row)

        self._hint = QLabel(hint)
        self._hint.setObjectName("pageHint")
        self._hint.setWordWrap(True)
        outer.addWidget(self._hint)

    def set_hint(self, text: str) -> None:
        self._hint.setText(text)

    def add_right(self, widget: QWidget) -> None:
        self._right.addWidget(widget)


class EmptyState(QLabel):
    """textNotice：text"text"，text。"""

    def __init__(self, text: str = "No repository analyzed yet") -> None:
        super().__init__(text)
        self.setObjectName("emptyState")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
