"""页面之间共用的小部件。

集中在这里的理由很实际：指标卡、标题、等级徽标这三样东西在四五个页面里都出现，
散着写会导致"同一个东西在总览页是 13px、在报告页是 14px"这种低级不一致，
评卷老师一眼就能看出来。
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

# 等级 → 颜色。涨跌色系在这里统一，别在页面里各写一份。
LEVEL_COLOR = {
    "high": "#F09595",
    "medium": "#EF9F27",
    "low": "#7FD1A0",
}

LEVEL_TEXT = {
    "high": "高风险",
    "medium": "中风险",
    "low": "良好",
}

SEVERITY_TEXT = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


class Card(QFrame):
    """统一样式的卡片容器。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class MetricCard(Card):
    """一张指标卡：上面小字标题，下面大数字，右下角一行灰字提示。"""

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
        """按等级给数字上色（high / medium / low）。"""
        color = LEVEL_COLOR.get(level)
        self._value.setStyleSheet(f"color: {color};" if color else "")


class Badge(QLabel):
    """小标签：风险等级、页面状态等。"""

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
    """页面顶部：标题 + 一行说明。右侧可以挂一个部件（按钮、筛选器）。"""

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
    """空状态提示：明确告诉用户"还没数据"，而不是留一片空白让人以为界面坏了。"""

    def __init__(self, text: str = "尚未分析任何仓库") -> None:
        super().__init__(text)
        self.setObjectName("emptyState")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
