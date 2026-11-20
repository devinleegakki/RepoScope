"""Analysis Settingstext：threshold、text、Commit convention。

text：
text**textAnti-pattern Centertext**。text
"textthresholdtext 10 text 3，Re-analyze，text"——thresholdtext、text，
text"text"text。

commitsInformationtextregex，textcheck：textanalyzetext，
textNotice。
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
    """Analysis Settings。text，Start analysistext。"""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        self.header = PageHeader(
            "Analysis Settings",
            "textthresholdtextfilestext。text「Repository」textStart analysistext，text。",
        )
        outer.addWidget(self.header)

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.window = QComboBox()
        for label, days in (("text", 0), ("text", 365), ("text 90 text", 90), ("text 30 text", 30)):
            self.window.addItem(label, days)

        self.stale = QSpinBox()
        self.stale.setRange(7, 3650)
        self.stale.setValue(_DEFAULTS["stale"])
        self.stale.setSuffix(" text")

        self.large = QSpinBox()
        self.large.setRange(1, 1024)
        self.large.setValue(_DEFAULTS["large"])
        self.large.setSuffix(" MB")

        self.hotspot = QSpinBox()
        self.hotspot.setRange(2, 500)
        self.hotspot.setValue(_DEFAULTS["hotspot"])
        self.hotspot.setSuffix(" text")

        self.release_stale = QSpinBox()
        self.release_stale.setRange(7, 3650)
        self.release_stale.setValue(_DEFAULTS["release_stale"])
        self.release_stale.setSuffix(" text")

        self.maintainer = QDoubleSpinBox()
        self.maintainer.setRange(1, 100)
        self.maintainer.setDecimals(0)
        self.maintainer.setValue(_DEFAULTS["maintainer"])
        self.maintainer.setSuffix(" %")

        self.max_function = QSpinBox()
        self.max_function.setRange(1, 10000)
        self.max_function.setValue(_DEFAULTS["max_function"])
        self.max_function.setSuffix(" text")

        self.max_file = QSpinBox()
        self.max_file.setRange(1, 100000)
        self.max_file.setValue(_DEFAULTS["max_file"])
        self.max_file.setSuffix(" text")

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

        self.dependency_scan = QCheckBox("Enable dependency scan")
        self.dependency_scan.setChecked(True)
        self.secret_scan = QCheckBox("Enable suspected-secret scan")
        self.secret_scan.setChecked(True)

        self.pattern = QLineEdit(_DEFAULTS["pattern"])
        self.pattern.textChanged.connect(self._validate_pattern)
        self.pattern_note = QLabel("")
        self.pattern_note.setObjectName("pageHint")

        form.addRow("texttime range", self.window)
        form.addRow("Stale filesthreshold", self._with_hint(self.stale, "textcommitstext，textrepositorytextfiles"))
        form.addRow("Large filesthreshold", self._with_hint(self.large, "textfilestextLarge filestext"))
        form.addRow("textthreshold", self._with_hint(self.hotspot, "textHot files"))
        form.addRow("textthreshold", self._with_hint(self.release_stale, "repositorytextcommits，text tag text"))
        form.addRow("text", self._with_hint(self.maintainer, "textauthorstextNoticetextRisk"))
        form.addRow("text", self._with_hint(self.max_function, "Python textNoticetextRisk"))
        form.addRow("textLarge filestext", self._with_hint(self.max_file, "Python filestextNoticetextRisk"))
        form.addRow("textfilestext", self._with_hint(self.test_ratio, "textfilestext Python filestextNotice"))
        form.addRow("filesauthorstext", self._with_hint(self.ownership, "textauthorstextfilestextNoticetextRisk"))
        form.addRow("text", self._with_hint(self.dependency_scan, "textanalyzetextfiles"))
        form.addRow("", self._with_hint(self.secret_scan, "text API key、token、text"))
        form.addRow("commitsInformationtext", self.pattern)
        form.addRow("", self.pattern_note)

        outer.addWidget(card)

        actions = QHBoxLayout()
        restore = QPushButton("Restore defaults")
        restore.clicked.connect(self.reset)
        actions.addWidget(restore)
        actions.addStretch(1)
        outer.addLayout(actions)
        outer.addStretch(1)

        self._validate_pattern(self.pattern.text())

    @staticmethod
    def _with_hint(widget: QWidget, hint: str) -> QWidget:
        """text，text。"""
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(widget)
        note = QLabel(hint)
        note.setObjectName("metricHint")
        layout.addWidget(note)
        return holder

    # -- check ------------------------------------------------------------
    def _validate_pattern(self, text: str) -> None:
        if not text:
            self.pattern_note.setText("textcommitsInformationtext")
            return
        try:
            re.compile(text)
        except re.error as exc:
            self.pattern_note.setText(f"✗ regextext：{exc}")
            return
        self.pattern_note.setText("✓ regexvalid。text，Re-analyzetextpass ratetext")

    def pattern_is_valid(self) -> bool:
        try:
            re.compile(self.pattern.text())
            return True
        except re.error:
            return False

    # -- text ------------------------------------------------------------
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
