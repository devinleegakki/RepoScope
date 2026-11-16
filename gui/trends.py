"""提交趋势页：折线图（日 / 周 / 月切换）+ GitHub 风格热力图。

两种读法不是重复：
* **折线**回答"趋势在涨还是在跌"，能看出某个时间段突然停更；
* **热力图**回答"哪几天在干活"，能看出周末加班或长期空窗。

日 / 周 / 月只是**同一份 ``commit_calendar`` 的三种切片**，不是三份新数据，
所以在展示层聚合，不向后端要字段。
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

_WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")
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
    """把按天的提交数聚合成按周或按月。``mode`` 取 ``日`` / ``周`` / ``月``。"""
    if mode == "日":
        return rows
    buckets: dict[datetime, int] = {}
    for moment, count in rows:
        if mode == "周":
            key = moment - timedelta(days=moment.weekday())
        else:
            key = moment.replace(day=1)
        buckets[key] = buckets.get(key, 0) + count
    return sorted(buckets.items(), key=lambda item: item[0])


class HeatmapWidget(QWidget):
    """GitHub 风格的提交热力图：7 行（周一到周日）× N 列（周）。

    为什么自己画而不是用 ``QTableWidget`` 染色：
    表格的行高会被 QSS 的 ``::item`` 内边距撑大（实测 15px 变 23px），
    按 ``行数 × 15`` 算出来的固定高度就只塞得下四行；而且单元格之间的缝隙
    没法控制，画出来是连成一片的色带，不是一格一格的方块。
    ``paintEvent`` 里画圆角矩形只有十几行，尺寸完全可控。
    """

    CELL = 11      # 方块边长
    GAP = 2        # 方块之间的缝隙
    GUTTER = 22    # 左侧星期标签的宽度

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

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt 的命名约定)
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
        self.setToolTip(f"{day.isoformat()} · {self._days.get(day, 0)} 次提交")


class TrendPage(QWidget):
    """提交趋势页。"""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[datetime, int]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.mode = QComboBox()
        self.mode.addItems(["按日", "按周", "按月"])
        self.mode.setCurrentIndex(1)
        self.mode.currentIndexChanged.connect(self._redraw)

        self.header = PageHeader("提交趋势", "尚未分析任何仓库")
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
        legend.addWidget(QLabel("少"))
        for color in _LEVEL_COLORS:
            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f"background:{color}; border-radius:2px;")
            legend.addWidget(swatch)
        legend.addWidget(QLabel("多"))
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
            f"共 {total:,} 次提交 · 覆盖 {len(calendar)} 个活跃日 · "
            f"按{self.mode.currentText().removeprefix('按')}查看"
        )
        self.heat_hint.setText(
            f"每格一天，共 {len(calendar)} 个活跃日；颜色越亮当天提交越多"
        )
        self.heatmap.set_calendar(calendar)
        self._redraw()

    def _redraw(self) -> None:
        if not self._rows:
            return
        mode = self.mode.currentText().removeprefix("按")
        points = aggregate(self._rows, mode)
        self.chart.set_points(points)
        if points:
            peak_day, peak = max(points, key=lambda item: item[1])
            label = "日" if mode == "日" else ("周" if mode == "周" else "月")
            self.chart_hint.setText(
                f"共 {len(points)} 个{label} · 峰值 {peak} 次"
                f"（{peak_day.strftime('%Y-%m-%d')}）· "
                f"平均 {sum(c for _, c in points) / max(1, len(points)):.1f} 次/{label}"
            )
