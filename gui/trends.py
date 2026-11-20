"""Commit Trendstext：text（text / text / text）+ GitHub text。

text：
* **text**text"text"，text；
* **text**text"text"，text。

text / text / text**text ``commit_calendar`` text**，text，
text，text。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisView
from .plotting import TrendChart
from .widgets import Card, PageHeader

_WEEKDAYS = ("text", "text", "text", "text", "text", "text", "text")
_LEVEL_COLORS = ("#21262d", "#0e4429", "#006d32", "#26a641", "#39d353")
_MAX_WEEKS = 60


def _level(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def _parse(calendar: dict[str, int]) -> list[tuple[datetime, int]]:
    rows: list[tuple[datetime, int]] = []
    for key, count in calendar.items():
        try:
            rows.append((datetime.strptime(key, "%Y-%m-%d"), count))
        except ValueError:
            continue
    rows.sort(key=lambda item: item[0])
    return rows


def aggregate(rows: list[tuple[datetime, int]], mode: str) -> list[tuple[datetime, int]]:
    """textcommit counttext。``mode`` text ``text`` / ``text`` / ``text``。"""
    if mode == "text":
        return rows
    buckets: dict[datetime, int] = {}
    for moment, count in rows:
        if mode == "text":
            key = moment - timedelta(days=moment.weekday())
        else:
            key = moment.replace(day=1)
        buckets[key] = buckets.get(key, 0) + count
    return sorted(buckets.items(), key=lambda item: item[0])


class HeatmapWidget(QWidget):
    """GitHub textcommitstext：7 text（text）× N text（text）。

    text ``QTableWidget`` text：
    text QSS text ``::item`` text（text 15px text 23px），
    text ``text × 15`` text；text
    text，text，text。
    ``paintEvent`` text，text。
    """

    CELL = 11      # text
    GAP = 2        # text
    GUTTER = 22    # texttagstext

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("heatmap")
        self.setMouseTracking(True)
        self._days: dict[date, int] = {}
        self._start: date | None = None
        self._last: date | None = None
        self._weeks = 0
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_calendar(self, calendar: dict[str, int]) -> None:
        days: dict[date, int] = {}
        for key, count in calendar.items():
            try:
                days[datetime.strptime(key, "%Y-%m-%d").date()] = count
            except ValueError:
                continue
        self._days = days
        if not days:
            self._start = self._last = None
            self._weeks = 0
            self.setFixedSize(0, 0)
            return

        first = min(days)
        self._start = first - timedelta(days=first.weekday())
        self._last = max(days)
        self._weeks = min(_MAX_WEEKS, ((self._last - self._start).days // 7) + 1)
        step = self.CELL + self.GAP
        self.setFixedSize(
            self.GUTTER + self._weeks * step,
            7 * step,
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt text)
        if not self._weeks or self._start is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        step = self.CELL + self.GAP

        for row in range(7):
            painter.setPen(QColor("#6e7681"))
            painter.drawText(
                0, row * step, self.GUTTER - 6, self.CELL,
                Qt.AlignCenter, _WEEKDAYS[row],
            )
            painter.setPen(Qt.NoPen)
            for column in range(self._weeks):
                day = self._start + timedelta(days=column * 7 + row)
                if self._last is not None and day > self._last:
                    continue
                color = _LEVEL_COLORS[_level(self._days.get(day, 0))]
                painter.setBrush(QColor(color))
                painter.drawRoundedRect(
                    QRectF(self.GUTTER + column * step, row * step, self.CELL, self.CELL),
                    2, 2,
                )

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._weeks or self._start is None:
            return
        step = self.CELL + self.GAP
        x = event.position().x() - self.GUTTER
        y = event.position().y()
        if x < 0 or y < 0:
            self.setToolTip("")
            return
        column, row = int(x // step), int(y // step)
        if column >= self._weeks or row > 6:
            self.setToolTip("")
            return
        day = self._start + timedelta(days=column * 7 + row)
        if self._last is not None and day > self._last:
            return
        self.setToolTip(f"{day.isoformat()} · {self._days.get(day, 0)} textcommits")


class TrendPage(QWidget):
    """Commit Trendstext。"""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[datetime, int]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.mode = QComboBox()
        self.mode.addItems(["text", "text", "text"])
        self.mode.setCurrentIndex(1)
        self.mode.currentIndexChanged.connect(self._redraw)

        self.header = PageHeader("Commit Trends", "No repository analyzed yet")
        self.header.add_right(self.mode)
        outer.addWidget(self.header)

        chart_card = Card()
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(12, 10, 12, 10)
        chart_layout.setSpacing(6)
        self.chart_hint = QLabel("—")
        self.chart_hint.setObjectName("pageHint")
        self.chart = TrendChart()
        self.chart.setMinimumHeight(220)
        chart_layout.addWidget(self.chart_hint)
        chart_layout.addWidget(self.chart, 1)
        outer.addWidget(chart_card, 3)

        heat_card = Card()
        heat_layout = QVBoxLayout(heat_card)
        heat_layout.setContentsMargins(12, 10, 12, 10)
        heat_layout.setSpacing(8)
        self.heat_hint = QLabel("—")
        self.heat_hint.setObjectName("pageHint")
        heat_layout.addWidget(self.heat_hint)

        self.heatmap = HeatmapWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addWidget(self.heatmap, 0, Qt.AlignLeft)
        holder_layout.addStretch(1)
        scroll.setWidget(holder)
        heat_layout.addWidget(scroll, 1)

        legend = QHBoxLayout()
        legend.setSpacing(4)
        legend.addWidget(QLabel("text"))
        for color in _LEVEL_COLORS:
            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f"background:{color}; border-radius:2px;")
            legend.addWidget(swatch)
        legend.addWidget(QLabel("text"))
        legend.addStretch(1)
        heat_layout.addLayout(legend)
        outer.addWidget(heat_card, 2)

    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        calendar = dict(view.commit_calendar)
        self._rows = _parse(calendar)
        total = sum(calendar.values())
        self.header.set_hint(
            f"text {total:,} textcommits · text {len(calendar)} text · "
            f"text{self.mode.currentText().removeprefix('text')}text"
        )
        self.heat_hint.setText(
            f"text，text {len(calendar)} text；textcommitstext"
        )
        self.heatmap.set_calendar(calendar)
        self._redraw()

    def _redraw(self) -> None:
        if not self._rows:
            return
        mode = self.mode.currentText().removeprefix("text")
        points = aggregate(self._rows, mode)
        self.chart.set_points(points)
        if points:
            peak_day, peak = max(points, key=lambda item: item[1])
            label = "text" if mode == "text" else ("text" if mode == "text" else "text")
            self.chart_hint.setText(
                f"text {len(points)} text{label} · text {peak} text"
                f"（{peak_day.strftime('%Y-%m-%d')}）· "
                f"text {sum(c for _, c in points) / max(1, len(points)):.1f} text/{label}"
            )
