"""分析配置页：阈值、统计范围、提交规范。

为什么单独一页而不是塞进侧边栏的一个弹窗：
这些值**直接决定反模式中心报什么**。演示时最有说服力的一幕就是
"把热点阈值从 10 改成 3，重新分析，警告条数变了"——阈值必须是看得见、摸得着的，
藏起来就失去了"参数不是黑箱"这个卖点。

提交信息格式用正则，输入时立刻校验：写错一个括号就让整个分析跑不起来，
不如当场提示。
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .contract import AnalysisRequest
from .widgets import Card, PageHeader

_DEFAULTS = {
    "window": 0,
    "stale": 180,
    "large": 10,
    "hotspot": 10,
    "release_stale": 365,
    "maintainer": 70,
    "max_function": 80,
    "max_file": 500,
    "test_ratio": 5,
    "ownership": 80,
    "pattern": r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: ",
}


class SettingsPage(QWidget):
    """分析配置。改完不用点保存，开始分析时读当前值。"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader(
            "分析配置",
            "这些阈值决定哪些文件会被点名。改完直接去「仓库选择」点开始分析即可，不需要保存。",
        )
        outer.addWidget(self.header)

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.window = QComboBox()
        for label, days in (("全部历史", 0), ("最近一年", 365), ("最近 90 天", 90), ("最近 30 天", 30)):
            self.window.addItem(label, days)

        self.stale = QSpinBox()
        self.stale.setRange(7, 3650)
        self.stale.setValue(_DEFAULTS["stale"])
        self.stale.setSuffix(" 天")

        self.large = QSpinBox()
        self.large.setRange(1, 1024)
        self.large.setValue(_DEFAULTS["large"])
        self.large.setSuffix(" MB")

        self.hotspot = QSpinBox()
        self.hotspot.setRange(2, 500)
        self.hotspot.setValue(_DEFAULTS["hotspot"])
        self.hotspot.setSuffix(" 次")

        self.release_stale = QSpinBox()
        self.release_stale.setRange(7, 3650)
        self.release_stale.setValue(_DEFAULTS["release_stale"])
        self.release_stale.setSuffix(" 天")

        self.maintainer = QDoubleSpinBox()
        self.maintainer.setRange(1, 100)
        self.maintainer.setDecimals(0)
        self.maintainer.setValue(_DEFAULTS["maintainer"])
        self.maintainer.setSuffix(" %")

        self.max_function = QSpinBox()
        self.max_function.setRange(1, 10000)
        self.max_function.setValue(_DEFAULTS["max_function"])
        self.max_function.setSuffix(" 行")

        self.max_file = QSpinBox()
        self.max_file.setRange(1, 100000)
        self.max_file.setValue(_DEFAULTS["max_file"])
        self.max_file.setSuffix(" 行")

        self.test_ratio = QDoubleSpinBox()
        self.test_ratio.setRange(0, 100)
        self.test_ratio.setDecimals(0)
        self.test_ratio.setValue(_DEFAULTS["test_ratio"])
        self.test_ratio.setSuffix(" %")

        self.ownership = QDoubleSpinBox()
        self.ownership.setRange(1, 100)
        self.ownership.setDecimals(0)
        self.ownership.setValue(_DEFAULTS["ownership"])
        self.ownership.setSuffix(" %")

        self.dependency_scan = QCheckBox("启用依赖扫描")
        self.dependency_scan.setChecked(True)
        self.secret_scan = QCheckBox("启用疑似秘密扫描")
        self.secret_scan.setChecked(True)

        self.pattern = QLineEdit(_DEFAULTS["pattern"])
        self.pattern.textChanged.connect(self._validate_pattern)
        self.pattern_note = QLabel("")
        self.pattern_note.setObjectName("pageHint")

        form.addRow("统计时间范围", self.window)
        form.addRow("陈旧文件阈值", self._with_hint(self.stale, "距最后一次提交超过这个天数，且仍在仓库里的文件"))
        form.addRow("大文件阈值", self._with_hint(self.large, "单文件超过这个体积会进入大文件榜"))
        form.addRow("热点阈值", self._with_hint(self.hotspot, "被修改次数达到这个值算热点文件"))
        form.addRow("发布停滞阈值", self._with_hint(self.release_stale, "仓库仍有近期提交，但最新 tag 超过这个天数"))
        form.addRow("单一维护者占比", self._with_hint(self.maintainer, "最近窗口内单个作者占比达到这个值时提示协作风险"))
        form.addRow("最大函数长度", self._with_hint(self.max_function, "Python 函数超过这个行数时提示代码质量风险"))
        form.addRow("最大文件长度", self._with_hint(self.max_file, "Python 文件超过这个行数时提示代码质量风险"))
        form.addRow("最低测试文件比例", self._with_hint(self.test_ratio, "测试文件占 Python 文件比例低于此值时提示"))
        form.addRow("文件作者集中度", self._with_hint(self.ownership, "单个作者修改同一文件达到此占比时提示所有权风险"))
        form.addRow("扫描开关", self._with_hint(self.dependency_scan, "关闭后不分析依赖清单和锁文件"))
        form.addRow("", self._with_hint(self.secret_scan, "关闭后不扫描疑似 API key、token、密码和私钥"))
        form.addRow("提交信息格式", self.pattern)
        form.addRow("", self.pattern_note)

        outer.addWidget(card)

        actions = QHBoxLayout()
        restore = QPushButton("恢复默认值")
        restore.clicked.connect(self.reset)
        actions.addWidget(restore)
        actions.addStretch(1)
        outer.addLayout(actions)
        outer.addStretch(1)

        self._validate_pattern(self.pattern.text())

    @staticmethod
    def _with_hint(widget: QWidget, hint: str) -> QWidget:
        """把输入框和一行说明包在一起，避免表单右侧出现一列解释性文字。"""
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(widget)
        note = QLabel(hint)
        note.setObjectName("metricHint")
        layout.addWidget(note)
        return holder

    # -- 校验 ------------------------------------------------------------
    def _validate_pattern(self, text: str) -> None:
        if not text:
            self.pattern_note.setText("留空表示不检查提交信息格式")
            return
        try:
            re.compile(text)
        except re.error as exc:
            self.pattern_note.setText(f"✗ 正则写错了：{exc}")
            return
        self.pattern_note.setText("✓ 正则合法。演示时可现场改这条，重新分析看通过率变化")

    def pattern_is_valid(self) -> bool:
        try:
            re.compile(self.pattern.text())
            return True
        except re.error:
            return False

    # -- 对外 ------------------------------------------------------------
    def reset(self) -> None:
        self.window.setCurrentIndex(0)
        self.stale.setValue(_DEFAULTS["stale"])
        self.large.setValue(_DEFAULTS["large"])
        self.hotspot.setValue(_DEFAULTS["hotspot"])
        self.release_stale.setValue(_DEFAULTS["release_stale"])
        self.maintainer.setValue(_DEFAULTS["maintainer"])
        self.max_function.setValue(_DEFAULTS["max_function"])
        self.max_file.setValue(_DEFAULTS["max_file"])
        self.test_ratio.setValue(_DEFAULTS["test_ratio"])
        self.ownership.setValue(_DEFAULTS["ownership"])
        self.dependency_scan.setChecked(True)
        self.secret_scan.setChecked(True)
        self.pattern.setText(_DEFAULTS["pattern"])

    def to_request(self, repo_path: str) -> AnalysisRequest:
        return AnalysisRequest(
            repo_path=repo_path,
            stale_days=self.stale.value(),
            large_file_mb=self.large.value(),
            hotspot_changes=self.hotspot.value(),
            release_stale_days=self.release_stale.value(),
            single_maintainer_ratio=self.maintainer.value() / 100,
            window_days=int(self.window.currentData() or 0),
            commit_pattern=self.pattern.text(),
            max_function_lines=self.max_function.value(),
            max_file_lines=self.max_file.value(),
            min_test_ratio=self.test_ratio.value() / 100,
            ownership_ratio=self.ownership.value() / 100,
            enable_dependency_scan=self.dependency_scan.isChecked(),
            enable_secret_scan=self.secret_scan.isChecked(),
        )
