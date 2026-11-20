"""text：Commit Trendstext + Author Contributionstext。

text ``PySide6.QtCharts`` text pyqtgraph / matplotlib：

* QtCharts text ``pip install pyside6`` text，**requirements.txt text**，
  text PySide6 text，text"text"。
* matplotlib text Qt text，texttagstext，text。
* pyqtgraph text，textRisk。

text：text 7×52 text，text ``QTableWidget`` text，
text。

**text**：text QtCharts text（PySide6-Essentials text），
text ``CHARTS_AVAILABLE`` text False，text，text。
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QHBoxLayout,
)

from .widgets import Card, LEVEL_COLOR

try:  # pragma: no cover - text PySide6 text
    from PySide6.QtCharts import (
        QBarCategoryAxis,
        QBarSet,
        QChart,
        QChartView,
        QDateTimeAxis,
        QHorizontalBarSeries,
        QLineSeries,
        QValueAxis,
    )

    CHARTS_AVAILABLE = True
except Exception:  # pragma: no cover
    CHARTS_AVAILABLE = False


LINE_COLOR = "#58a6ff"
GRID_COLOR = "#30363d"
TEXT_COLOR = "#8b949e"


def _axis_font() -> QFont:
    font = QFont()
    font.setPointSize(9)
    return font


class TrendChart(QWidget):
    """Commit Trendstext：text，textcommitstext，text。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not CHARTS_AVAILABLE:
            self._fallback = _FallbackTable("text QtCharts，text")
            layout.addWidget(self._fallback)
            self._chart = None
            return

        self._fallback = None
        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.setAnimationOptions(QChart.NoAnimation)
        self._chart.legend().setVisible(False)
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setStyleSheet("background: transparent;")
        layout.addWidget(self._view)

    def set_points(self, points: list[tuple[datetime, int]], unit: str = "commits") -> None:
        """``points`` text，text（text）。"""
        if self._chart is None:
            self._fallback.set_rows([(d.strftime("%Y-%m-%d"), str(c)) for d, c in points],
                                    ("text", unit))
            return

        chart = self._chart
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            chart.removeAxis(axis)

        if not points:
            return

        line = QLineSeries()
        pen = QPen(QColor(LINE_COLOR))
        pen.setWidth(2)
        line.setPen(pen)
        line.setPointsVisible(len(points) <= 40)
        for moment, count in points:
            line.append(int(moment.timestamp() * 1000), count)

        axis_x = QDateTimeAxis()
        # text：text Qt text（yyyy / MM / dd），text strftime text %Y-%m。
        # text %Y-%m text。
        axis_x.setFormat("MM-dd" if (points[-1][0] - points[0][0]).days <= 120 else "yyyy-MM")
        axis_x.setTickCount(min(7, max(2, len(points))))
        axis_x.setLabelsColor(QColor(TEXT_COLOR))
        axis_x.setLabelsFont(_axis_font())
        axis_x.setGridLineColor(QColor(GRID_COLOR))
        axis_x.setLinePenColor(QColor(GRID_COLOR))

        peak = max(count for _, count in points)
        axis_y = QValueAxis()
        axis_y.setRange(0, max(1, peak * 1.15))
        axis_y.setLabelFormat("%d")
        axis_y.setTickCount(5)
        axis_y.setLabelsColor(QColor(TEXT_COLOR))
        axis_y.setLabelsFont(_axis_font())
        axis_y.setGridLineColor(QColor(GRID_COLOR))
        axis_y.setLinePenColor(QColor(GRID_COLOR))

        chart.addSeries(line)
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        line.attachAxis(axis_x)
        line.attachAxis(axis_y)


class AuthorBarChart(QWidget):
    """Author Contributionstext。text，text 10 text。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not CHARTS_AVAILABLE:
            self._fallback = _FallbackTable("text QtCharts，text")
            layout.addWidget(self._fallback)
            self._chart = None
            return

        self._fallback = None
        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.setAnimationOptions(QChart.NoAnimation)
        self._chart.legend().setVisible(False)

        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setStyleSheet("background: transparent;")
        layout.addWidget(self._view)

    def set_authors(self, rows: list[tuple[str, int]]) -> None:
        if self._chart is None:
            self._fallback.set_rows([(n, str(c)) for n, c in rows], ("authors", "commit count"))
            return

        chart = self._chart
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            chart.removeAxis(axis)
        if not rows:
            return

        rows = rows[:10]
        bar_set = QBarSet("commit count")
        bar_set.setColor(QColor(LINE_COLOR))
        bar_set.setBorderColor(QColor(LINE_COLOR))
        for _, count in rows:
            bar_set.append(count)

        series = QHorizontalBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsPosition(QHorizontalBarSeries.LabelsInsideEnd)
        # tagstext QBarSet；QBarSeries text/text/text
        bar_set.setLabelColor(QColor("#0d1117"))
        bar_set.setLabelFont(_axis_font())

        axis_y = QBarCategoryAxis()
        axis_y.append([name for name, _ in rows])
        axis_y.setLabelsColor(QColor(TEXT_COLOR))
        axis_y.setLabelsFont(_axis_font())
        axis_y.setGridLineVisible(False)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(1, max(count for _, count in rows) * 1.12))
        axis_x.setTickCount(5)
        axis_x.setLabelFormat("%d")
        axis_x.setLabelsColor(QColor(TEXT_COLOR))
        axis_x.setLabelsFont(_axis_font())
        axis_x.setGridLineColor(QColor(GRID_COLOR))

        chart.addSeries(series)
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)


class _FallbackTable(Card):
    """QtCharts textelapsedtext：text，text，text。"""

    def __init__(self, note: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        label = QLabel(note)
        label.setObjectName("pageHint")
        layout.addWidget(label)

        self.table = QTableWidget(0, 2)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

    def set_rows(self, rows: list[tuple[str, str]], headers: tuple[str, str]) -> None:
        self.table.setHorizontalHeaderLabels(list(headers))
        self.table.setRowCount(len(rows))
        for index, (left, right) in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(left))
            item = QTableWidgetItem(right)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(index, 1, item)
        self.table.horizontalHeader().setStretchLastSection(True)


class HealthDimensionChart(Card):
    """Compact score bars for the dashboard health dimensions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(5)
        title = QLabel("text"); title.setObjectName("sectionTitle"); self._layout.addWidget(title)
        self._rows = QVBoxLayout()
        self._layout.addLayout(self._rows)

    def set_dimensions(self, dimensions) -> None:
        while self._rows.count():
            item = self._rows.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for dimension in dimensions:
            row = QWidget(); layout = QHBoxLayout(row); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(6)
            label = QLabel(dimension.name); label.setMinimumWidth(76); label.setObjectName("metricHint")
            bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(round(max(0, min(100, dimension.score)))); bar.setTextVisible(False); bar.setFixedHeight(8)
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {LEVEL_COLOR.get(dimension.level, LINE_COLOR)}; border-radius: 4px; }}")
            score = QLabel(f"{dimension.score:.0f}"); score.setMinimumWidth(28); score.setAlignment(Qt.AlignRight); score.setObjectName("metricHint")
            label.setToolTip(dimension.hint); bar.setToolTip(dimension.hint)
            layout.addWidget(label); layout.addWidget(bar, 1); layout.addWidget(score); self._rows.addWidget(row)


class RiskDistributionChart(Card):
    """Text-first risk distribution that remains legible without QtCharts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent); self._layout = QVBoxLayout(self); self._layout.setContentsMargins(12, 10, 12, 10); self._layout.setSpacing(8)
        title = QLabel("Risktext"); title.setObjectName("sectionTitle"); self._layout.addWidget(title)

    def set_counts(self, counts) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        total = sum(counts.values())
        for level, text in (("high", "High risk"), ("medium", "Medium risk"), ("low", "Low risk")):
            count = counts.get(level, 0); ratio = f"{count / total:.0%}" if total else "0%"
            row = QLabel(f"● {text}   {count} text   ({ratio})"); row.setObjectName("riskRow"); row.setStyleSheet(f"color:{LEVEL_COLOR[level]};")
            self._layout.addWidget(row)
        hint = QLabel(f"text {total} textRulestext" if total else "textMedium riskRules"); hint.setObjectName("metricHint"); self._layout.addWidget(hint)
