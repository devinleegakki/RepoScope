"""GUI 冒烟测试：窗口能建、页面能切、数据能灌、报告能生成。

用 offscreen 平台跑，所以不需要真实显示器，CI 里也能过：

    QT_QPA_PLATFORM=offscreen python -m unittest tests.test_gui_smoke
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from PySide6.QtWidgets import QApplication  # noqa: E402
except ImportError as exc:  # pragma: no cover - 没装 GUI 依赖时整组跳过
    raise unittest.SkipTest(
        f"GUI 冒烟测试需要 PySide6（pip install pyside6）：{exc}"
    ) from exc

from gui import mock_data  # noqa: E402
from gui.contract import AnalysisView, RepoSummary  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from gui.report_page import build_markdown, export  # noqa: E402

_APP = None
_VIEW = None


def setUpModule() -> None:
    global _APP, _VIEW
    _APP = QApplication.instance() or QApplication([])
    _VIEW = mock_data.build("/definitely/not/a/repo")


class TestMockData(unittest.TestCase):
    def test_view_satisfies_contract(self):
        self.assertIsInstance(_VIEW, AnalysisView)

    def test_falls_back_to_synthetic_data(self):
        self.assertGreater(len(_VIEW.snapshot.commits), 0)
        self.assertGreater(_VIEW.total_commits, 0)
        self.assertTrue(_VIEW.commit_calendar)
        self.assertTrue(0 <= _VIEW.health_score <= 100)
        self.assertIn(_VIEW.risk_level, {"low", "medium", "high"})

    def test_progress_callback_is_called(self):
        seen = []
        mock_data.build("/definitely/not/a/repo", on_progress=lambda p, m: seen.append(p))
        self.assertTrue(seen)
        self.assertEqual(seen[-1], 100)

    def test_warnings_carry_four_elements(self):
        """反模式中心的要求：每条警告都要能解释"为什么、差多少、怎么改"。"""
        self.assertTrue(_VIEW.warnings)
        for warning in _VIEW.warnings:
            self.assertTrue(warning.has_evidence, f"{warning.rule} 缺少四要素")
            self.assertIn(warning.severity, {"high", "medium", "low"})

    def test_commit_hygiene_is_computed(self):
        hygiene = _VIEW.commit_hygiene
        self.assertEqual(hygiene.total, _VIEW.total_commits)
        self.assertTrue(0 <= hygiene.pass_rate <= 1)
        # violations 只保留前 20 条用于展示，所以这里是"不超出"而不是"相等"
        self.assertLessEqual(hygiene.passed + len(hygiene.violations), hygiene.total)


class TestMainWindow(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_nine_pages_are_registered(self):
        self.assertEqual(self.window.stack.count(), 9)

    def test_sidebar_has_group_headers_and_pages(self):
        # 9 个页面 + 3 个分组标题
        self.assertEqual(self.window.sidebar.count(), 12)
        self.assertEqual(len(self.window._row_to_page), 9)

    def test_sidebar_switches_page(self):
        for row, page_index in self.window._row_to_page.items():
            self.window.sidebar.setCurrentRow(row)
            self.assertEqual(self.window.stack.currentIndex(), page_index)

    def test_group_header_does_not_switch_page(self):
        self.window.goto("分析配置")
        before = self.window.stack.currentIndex()
        header_row = 0
        self.assertEqual(self.window.sidebar.item(header_row).data(0x0100), "header")
        self.window.sidebar.setCurrentRow(header_row)
        # 分组标题不可选，切换不会把页面切到空白
        self.assertEqual(self.window.stack.currentIndex(), before)

    def test_every_data_page_accepts_view(self):
        for page in (self.window.dashboard_page, self.window.trend_page,
                     self.window.authors_page, self.window.files_page,
                     self.window.patterns_page, self.window.report_page):
            page.set_data(_VIEW)

        self.assertEqual(self.window.dashboard_page.health._value.text(),
                         f"{_VIEW.health_score:.0f}")
        self.assertEqual(self.window.files_page.hot.model.rowCount(),
                         len(_VIEW.hotspot_files))
        self.assertEqual(self.window.patterns_page.list.count(), len(_VIEW.warnings))
        self.assertTrue(self.window.report_page.preview.toPlainText())

    def test_trend_mode_switch_keeps_chart_alive(self):
        self.window.trend_page.set_data(_VIEW)
        for index in range(self.window.trend_page.mode.count()):
            self.window.trend_page.mode.setCurrentIndex(index)
        self.assertTrue(self.window.trend_page.chart_hint.text())

    def test_settings_produce_request(self):
        request = self.window.settings_page.to_request("/tmp/repo")
        self.assertEqual(request.repo_path, "/tmp/repo")
        self.assertGreater(request.stale_days, 0)
        self.assertEqual(request.window_days, 0)
        self.assertTrue(self.window.settings_page.pattern_is_valid())

    def test_invalid_pattern_is_detected(self):
        self.window.settings_page.pattern.setText("^(feat")
        self.assertFalse(self.window.settings_page.pattern_is_valid())
        self.window.settings_page.reset()
        self.assertTrue(self.window.settings_page.pattern_is_valid())

    def test_path_validation_updates_state(self):
        self.window.select_page.path_edit.setText("")
        self.assertFalse(self.window.select_page.analyze_btn.isEnabled())
        self.window.select_page.path_edit.setText("/definitely/not/here")
        self.assertFalse(self.window.select_page.analyze_btn.isEnabled())
        self.assertIn("不存在", self.window.select_page.status.text())

    def test_empty_path_is_rejected_without_crashing(self):
        self.window.select_page.path_edit.setText("")
        self.assertIsNone(self.window._thread)


class TestReport(unittest.TestCase):
    def test_markdown_covers_all_sections(self):
        markdown = build_markdown(_VIEW)
        for keyword in ("总体评价", "关键指标", "作者贡献", "提交活跃度",
                        "热点文件", "反模式清单", "提交规范", "复现方式"):
            self.assertIn(keyword, markdown)

    def test_export_writes_three_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            written = export(_VIEW, ["markdown", "html", "csv"], folder)
            self.assertEqual(len(written), 3)
            for path in written:
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)

    def test_repo_summary_defaults(self):
        summary = RepoSummary(repo_name="x")
        self.assertEqual(summary.risk_level, "low")


if __name__ == "__main__":
    unittest.main()
