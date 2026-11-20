"""Dashboard：health score + textKey metrics + Risktext。

text**text**，text，text「Anti-pattern Center」。
text：text"textrepositorytext"，text。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisView
from .plotting import HealthDimensionChart, RiskDistributionChart, TrendChart
from .widgets import LEVEL_COLOR, LEVEL_TEXT, SEVERITY_TEXT, Badge, Card, MetricCard, PageHeader


class HealthCard(Card):
    """health scoretext：text + Level + text。"""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(210)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(6)

        label = QLabel("repositoryhealth score")
        label.setObjectName("metricLabel")
        self._value = QLabel("—")
        self._value.setObjectName("healthValue")
        self._badge = Badge("Pending analysis", "low")

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._value)
        row.addWidget(self._badge, 0, Qt.AlignBottom)
        row.addStretch(1)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)

        self._hint = QLabel("text 100 · textRulestext")
        self._hint.setObjectName("metricHint")

        layout.addWidget(label)
        layout.addLayout(row)
        layout.addWidget(self._bar)
        layout.addWidget(self._hint)

    def set_score(self, score: float, level: str) -> None:
        self._value.setText(f"{score:.0f}")
        self._value.setStyleSheet(f"color:{LEVEL_COLOR.get(level, '#c9d1d9')};")
        self._badge.setText(LEVEL_TEXT.get(level, level))
        self._badge.set_level(level)
        self._bar.setValue(round(score))


class DashboardPage(QWidget):
    """text。text ``AnalysisView``，text。"""

    open_patterns = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader("Dashboard", "No repository analyzed yet")
        outer.addWidget(self.header)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.health = HealthCard()
        top.addWidget(self.health, 0)

        self.commits = MetricCard("commitstext")
        self.authors = MetricCard("author count")
        self.files = MetricCard("file count")
        self.hygiene = MetricCard("Commit conventionpass rate")
        for card in (self.commits, self.authors, self.files, self.hygiene):
            top.addWidget(card, 1)
        outer.addLayout(top)

        visuals = QHBoxLayout()
        visuals.setSpacing(12)
        self.dimension_chart = HealthDimensionChart()
        self.dimension_chart.setMinimumHeight(150)
        self.risk_chart = RiskDistributionChart()
        self.risk_chart.setMinimumHeight(150)
        self.activity_chart = Card()
        activity_chart_layout = QVBoxLayout(self.activity_chart)
        activity_chart_layout.setContentsMargins(12, 10, 12, 10)
        activity_chart_layout.setSpacing(4)
        activity_chart_layout.addWidget(QLabel("Commit Trends"))
        self.trend_chart = TrendChart()
        self.trend_chart.setMinimumHeight(115)
        activity_chart_layout.addWidget(self.trend_chart, 1)
        visuals.addWidget(self.dimension_chart, 3)
        visuals.addWidget(self.risk_chart, 2)
        visuals.addWidget(self.activity_chart, 3)
        outer.addLayout(visuals)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        risk_card = Card()
        risk_layout = QVBoxLayout(risk_card)
        risk_layout.setContentsMargins(16, 12, 16, 12)
        risk_layout.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("Risktext")
        title.setObjectName("sectionTitle")
        self.risk_count = QLabel("")
        self.risk_count.setObjectName("pageHint")
        jump = QPushButton("textAnti-pattern Center →")
        jump.setObjectName("link")
        jump.clicked.connect(self.open_patterns.emit)
        head.addWidget(title)
        head.addWidget(self.risk_count)
        head.addStretch(1)
        head.addWidget(jump)
        risk_layout.addLayout(head)

        self.risk_list = QVBoxLayout()
        self.risk_list.setSpacing(6)
        risk_layout.addLayout(self.risk_list)
        risk_layout.addStretch(1)
        bottom.addWidget(risk_card, 3)

        activity_card = Card()
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 12, 16, 12)
        activity_layout.setSpacing(8)
        activity_title = QLabel("text")
        activity_title.setObjectName("sectionTitle")
        activity_layout.addWidget(activity_title)

        self.recent_rows = QVBoxLayout()
        self.recent_rows.setSpacing(6)
        activity_layout.addLayout(self.recent_rows)
        activity_layout.addStretch(1)
        bottom.addWidget(activity_card, 2)

        outer.addLayout(bottom, 1)

    # -- text ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        snapshot = view.snapshot
        self.header.set_hint(
            f"{snapshot.repo_name} · {snapshot.repo_path} · "
            f"{len(snapshot.branches)} textbranches · elapsed {view.elapsed_seconds:.1f}s"
        )

        level = getattr(view, "risk_level", "low")
        self.health.set_score(view.health_score, level)

        active_days = len(view.commit_calendar)
        self.commits.set_value(f"{view.total_commits:,}", f"text {active_days} text")
        self.authors.set_value(str(view.author_count),
                               self._concentration(view))
        self.files.set_value(f"{view.file_count:,}",
                             f"text {len(view.hotspot_files)} · text {len(view.stale_files)}")

        hygiene = getattr(view, "commit_hygiene", None)
        if hygiene is not None and hygiene.pass_rate >= 0:
            self.hygiene.set_value(
                f"{hygiene.pass_rate:.0%}",
                f"{hygiene.passed}/{hygiene.total} text",
            )
            tone = "low" if hygiene.pass_rate >= 0.8 else (
                "medium" if hygiene.pass_rate >= 0.6 else "high")
            self.hygiene.set_tone(tone)
        else:
            self.hygiene.set_value("—", "Not provided by backend")

        self._fill_risks(view)
        self._fill_recent(view)
        stats = getattr(view, "dashboard_stats", None)
        if stats is not None:
            self.dimension_chart.set_dimensions(stats.dimensions)
            self.risk_chart.set_counts(stats.risk_counts)
        points = []
        for day, count in sorted(dict(view.commit_calendar).items()):
            try:
                points.append((datetime.strptime(day, "%Y-%m-%d"), count))
            except ValueError:
                continue
        self.trend_chart.set_points(points[-90:])

    @staticmethod
    def _concentration(view: AnalysisView) -> str:
        stats = list(view.author_stats)
        if not stats:
            return "textauthor counttext"
        return f"text {stats[0].share:.0%}"

    def _clear(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _fill_risks(self, view: AnalysisView) -> None:
        self._clear(self.risk_list)
        warnings = list(view.warnings)
        self.risk_count.setText(f"text {len(warnings)} text" if warnings else "text")
        if not warnings:
            ok = QLabel("textanti-patternsRules")
            ok.setObjectName("pageHint")
            self.risk_list.addWidget(ok)
            return
        for warning in warnings[:3]:
            row = QLabel(
                f"<span style='color:{LEVEL_COLOR.get(warning.severity, '#c9d1d9')}'>"
                f"● {SEVERITY_TEXT.get(warning.severity, warning.severity)}</span>&nbsp; "
                f"<b>{warning.rule}</b> · {warning.message}"
            )
            row.setTextFormat(Qt.RichText)
            row.setWordWrap(True)
            row.setObjectName("riskRow")
            self.risk_list.addWidget(row)
        if len(warnings) > 3:
            more = QLabel(f"text {len(warnings) - 3} text，text「Anti-pattern Center」")
            more.setObjectName("pageHint")
            self.risk_list.addWidget(more)

    def _fill_recent(self, view: AnalysisView) -> None:
        self._clear(self.recent_rows)
        calendar = dict(view.commit_calendar)
        if not calendar:
            empty = QLabel("textcommitstext")
            empty.setObjectName("pageHint")
            self.recent_rows.addWidget(empty)
            return
        dates = sorted(calendar)
        last = dates[-1]
        end = datetime.strptime(last, "%Y-%m-%d")
        for days in (7, 30, 90):
            start = end - timedelta(days=days - 1)
            total = sum(
                count for day, count in calendar.items()
                if start.strftime("%Y-%m-%d") <= day <= last
            )
            row = QLabel(f"text {days} text · {total} textcommits")
            row.setObjectName("riskRow")
            self.recent_rows.addWidget(row)
        last_day = QLabel(f"textcommits：{last}")
        last_day.setObjectName("metricHint")
        self.recent_rows.addWidget(last_day)
