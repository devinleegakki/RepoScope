"""总览仪表板：健康度 + 五个关键指标 + 风险摘要。

这里**不列全部警告**，只给前三条和总数，完整四要素放在「反模式中心」。
理由：总览页的职责是让人三秒内知道"这个仓库有没有病"，列长清单反而看不出重点。
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
from .widgets import LEVEL_COLOR, LEVEL_TEXT, SEVERITY_TEXT, Badge, Card, MetricCard, PageHeader


class HealthCard(Card):
    """健康度大卡：数字 + 等级 + 一条进度条。"""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(210)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(6)

        label = QLabel("仓库健康度")
        label.setObjectName("metricLabel")
        self._value = QLabel("—")
        self._value.setObjectName("healthValue")
        self._badge = Badge("待分析", "low")

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

        self._hint = QLabel("满分 100 · 由命中规则的严重度扣分")
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
    """总览页。所有数字都来自传入的 ``AnalysisView``，页面自己不做统计。"""

    open_patterns = Signal()

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader("总览仪表板", "尚未分析任何仓库")
        outer.addWidget(self.header)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.health = HealthCard()
        top.addWidget(self.health, 0)

        self.commits = MetricCard("提交总数")
        self.authors = MetricCard("作者数")
        self.files = MetricCard("文件数")
        self.hygiene = MetricCard("提交规范通过率")
        for card in (self.commits, self.authors, self.files, self.hygiene):
            top.addWidget(card, 1)
        outer.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        risk_card = Card()
        risk_layout = QVBoxLayout(risk_card)
        risk_layout.setContentsMargins(16, 12, 16, 12)
        risk_layout.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("风险摘要")
        title.setObjectName("sectionTitle")
        self.risk_count = QLabel("")
        self.risk_count.setObjectName("pageHint")
        jump = QPushButton("查看反模式中心 →")
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
        activity_title = QLabel("近期活跃度")
        activity_title.setObjectName("sectionTitle")
        activity_layout.addWidget(activity_title)

        self.recent_rows = QVBoxLayout()
        self.recent_rows.setSpacing(6)
        activity_layout.addLayout(self.recent_rows)
        activity_layout.addStretch(1)
        bottom.addWidget(activity_card, 2)

        outer.addLayout(bottom, 1)

    # -- 数据 ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        snapshot = view.snapshot
        self.header.set_hint(
            f"{snapshot.repo_name} · {snapshot.repo_path} · "
            f"{len(snapshot.branches)} 个分支 · 用时 {view.elapsed_seconds:.1f}s"
        )

        level = getattr(view, "risk_level", "low")
        self.health.set_score(view.health_score, level)

        active_days = len(view.commit_calendar)
        self.commits.set_value(f"{view.total_commits:,}", f"覆盖 {active_days} 个活跃日")
        self.authors.set_value(str(view.author_count),
                               self._concentration(view))
        self.files.set_value(f"{view.file_count:,}",
                             f"热点 {len(view.hotspot_files)} · 陈旧 {len(view.stale_files)}")

        hygiene = getattr(view, "commit_hygiene", None)
        if hygiene is not None and hygiene.pass_rate >= 0:
            self.hygiene.set_value(
                f"{hygiene.pass_rate:.0%}",
                f"{hygiene.passed}/{hygiene.total} 条符合约定格式",
            )
            tone = "low" if hygiene.pass_rate >= 0.8 else (
                "medium" if hygiene.pass_rate >= 0.6 else "high")
            self.hygiene.set_tone(tone)
        else:
            self.hygiene.set_value("—", "待后端提供")

        self._fill_risks(view)
        self._fill_recent(view)

    @staticmethod
    def _concentration(view: AnalysisView) -> str:
        stats = list(view.author_stats)
        if not stats:
            return "无作者数据"
        return f"最高占比 {stats[0].share:.0%}"

    def _clear(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _fill_risks(self, view: AnalysisView) -> None:
        self._clear(self.risk_list)
        warnings = list(view.warnings)
        self.risk_count.setText(f"共 {len(warnings)} 条" if warnings else "无")
        if not warnings:
            ok = QLabel("没有命中任何反模式规则")
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
            more = QLabel(f"另有 {len(warnings) - 3} 条，见「反模式中心」")
            more.setObjectName("pageHint")
            self.risk_list.addWidget(more)

    def _fill_recent(self, view: AnalysisView) -> None:
        self._clear(self.recent_rows)
        calendar = dict(view.commit_calendar)
        if not calendar:
            empty = QLabel("没有提交记录")
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
            row = QLabel(f"最近 {days} 天 · {total} 次提交")
            row.setObjectName("riskRow")
            self.recent_rows.addWidget(row)
        last_day = QLabel(f"最后一次提交：{last}")
        last_day.setObjectName("metricHint")
        self.recent_rows.addWidget(last_day)
