"""反模式中心：每条风险都要能回答"为什么算问题、差多少、怎么改"。

这是整个 GUI 里最能拿分的一页。普通工具只会说"有 3 个文件过大"，
这一页要求每条规则带上**四要素**：

    触发条件 ← 规则本身（rules.py 的 pattern / 阈值表达式）
    实际值   ← 这次算出来的数
    配置阈值 ← 用户在「分析配置」里设的数
    建议动作 ← 明确告诉使用者下一步做什么

四要素由后端 ``Warning`` 提供（字段已在本文件的契约里预留）。
后端没给全时，这里显示"待 rules.py 补齐"，绝不编造内容——因为一旦编造，
演示时被问"这个阈值哪来的"就答不上。
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
from .widgets import LEVEL_COLOR, LEVEL_TEXT, SEVERITY_TEXT, Badge, Card, PageHeader

_EVIDENCE_FIELDS = (
    ("触发条件", "condition"),
    ("实际值", "actual"),
    ("配置阈值", "threshold"),
    ("建议动作", "action"),
)


class PatternPage(QWidget):
    """反模式中心：左侧清单，右侧四要素详情。"""

    def __init__(self) -> None:
        super().__init__()
        self._warnings: list[Warning] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.filter = QComboBox()
        self.filter.addItems(["全部等级", "只看高风险", "只看中风险", "只看低风险"])
        self.filter.currentIndexChanged.connect(self._refresh_list)

        self.header = PageHeader("反模式中心", "尚未分析任何仓库")
        self.header.add_right(self.filter)
        outer.addWidget(self.header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = Card()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        list_title = QLabel("命中规则")
        list_title.setObjectName("sectionTitle")
        left_layout.addWidget(list_title)
        self.list = QListWidget()
        self.list.setObjectName("patternList")
        self.list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list.currentRowChanged.connect(self._show_detail)
        left_layout.addWidget(self.list, 1)
        splitter.addWidget(left)

        self.detail = _DetailCard()
        splitter.addWidget(self.detail)
        splitter.setSizes([280, 640])
        outer.addWidget(splitter, 1)

    # -- 数据 ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self._warnings = list(view.warnings)
        counts = {level: 0 for level in ("high", "medium", "low")}
        for warning in self._warnings:
            counts[warning.severity] = counts.get(warning.severity, 0) + 1
        self.header.set_hint(
            f"共 {len(self._warnings)} 条命中 · 高 {counts['high']} · "
            f"中 {counts['medium']} · 低 {counts['low']}"
            " · 每条规则都给出触发条件与实际值，便于直接整改"
        )
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
            item = QListWidgetItem("当前筛选下没有命中规则")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            self.detail.show_warning(None)
            return
        for warning in rows:
            text = f"{SEVERITY_TEXT.get(warning.severity, warning.severity)}｜{warning.rule}"
            item = QListWidgetItem(f"{text}\n{warning.message}")
            item.setForeground(QColor("#c9d1d9"))
            item.setData(Qt.UserRole, warning)
            color = LEVEL_COLOR.get(warning.severity, "#8b949e")
            item.setToolTip(f"{warning.message}\n涉及：{warning.target or '—'}")
            self.list.addItem(item)
            item.setSizeHint(QSize(0, 52))
            if not warning.has_evidence:
                item.setToolTip("四要素未齐，详情页会标注待补字段")
        self.list.setCurrentRow(0)

    def _show_detail(self, row: int) -> None:
        item = self.list.item(row)
        if item is None or item.data(Qt.UserRole) is None:
            self.detail.show_warning(None)
            return
        self.detail.show_warning(item.data(Qt.UserRole))


class _DetailCard(Card):
    """单条规则的详情：规则名、等级、四要素、涉及对象。"""

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

        self.message = QLabel("选择左侧一条规则查看详情")
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
            self.message.setText("当前没有可展示的规则命中")
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
            self._values[key].setText(raw or "待后端提供")
        self.target.setText(f"涉及对象：{warning.target or '—'}")

        missing = [label for label, key in _EVIDENCE_FIELDS if not getattr(warning, key)]
        if missing:
            self.pending.setText(
                "以下字段待 rules.py 补齐：" + "、".join(missing)
                + "（接口已在 gui/contract.py 的 Warning 里声明）"
            )
            self.pending.setVisible(True)
        else:
            self.pending.setVisible(False)
