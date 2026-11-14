"""图表封装：提交趋势折线 + 作者贡献条形。

为什么用 ``PySide6.QtCharts`` 而不是 pyqtgraph / matplotlib：

* QtCharts 随 ``pip install pyside6`` 一起装好，**requirements.txt 里不用多写一行**，
  评卷老师在自己的机器上装完 PySide6 就能跑，不会出现"少了图表库直接白屏"。
* matplotlib 嵌 Qt 要额外适配层，而且中文标签乱码是经典坑，演示前排查这个不值当。
* pyqtgraph 是独立包，同样是多一个安装风险。

热力图不用图表库：它是 7×52 的色块矩阵，用 ``QTableWidget`` 染色二十行就够，
用图表库反而绕。

**降级**：万一运行环境里 QtCharts 被裁掉（PySide6-Essentials 单独安装），
这里的 ``CHARTS_AVAILABLE`` 会变成 False，趋势图退化成表格，界面不会崩。
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
)

from .widgets import Card

try:  # pragma: no cover - 取决于安装的 PySide6 发行包
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
    """提交趋势折线图：横轴时间，纵轴提交次数，线下带淡色填充。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not CHARTS_AVAILABLE:
            self._fallback = _FallbackTable("未检测到 QtCharts，趋势已降级为表格")
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

    def set_points(self, points: list[tuple[datetime, int]], unit: str = "提交") -> None:
        """``points`` 必须按时间升序，由调用方保证（聚合时顺手排序）。"""
        if self._chart is None:
            self._fallback.set_rows([(d.strftime("%Y-%m-%d"), str(c)) for d, c in points],
                                    ("时间", unit))
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
        # 注意：这里要 Qt 的日期格式（yyyy / MM / dd），不是 strftime 的 %Y-%m。
        # 写成 %Y-%m 会被当成普通文字原样画在坐标轴上。
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
    """作者贡献横向条形图。名字太长时用表格而不是图表更清楚，所以这里限 10 人。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not CHARTS_AVAILABLE:
            self._fallback = _FallbackTable("未检测到 QtCharts，条形图已降级为表格")
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
            self._fallback.set_rows([(n, str(c)) for n, c in rows], ("作者", "提交数"))
            return

        chart = self._chart
        chart.removeAllSeries()
        for axis in list(chart.axes()):
            chart.removeAxis(axis)
        if not rows:
            return

        rows = rows[:10]
        bar_set = QBarSet("提交数")
        bar_set.setColor(QColor(LINE_COLOR))
        bar_set.setBorderColor(QColor(LINE_COLOR))
        for _, count in rows:
            bar_set.append(count)

        series = QHorizontalBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsPosition(QHorizontalBarSeries.LabelsInsideEnd)
        # 标签的颜色和字体属于 QBarSet；QBarSeries 只有位置/格式/精度这几个开关
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
    """QtCharts 不可用时的兜底：一张两列表格，功能不丢，只是不好看。"""

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
