"""集成测试：报告生成（reporters.py）。

验收点："Markdown、HTML、CSV 报告"齐全，且"三种报告数据一致"
—— 三种格式从同一个 AnalysisView 渲染，关键数字必须对得上。
"""

from pathlib import Path

import pytest

from gui import mock_data
from gui.contract import RepoSummary
from services import BatchResult

import reporters


@pytest.fixture(scope="module")
def view():
    # 合成数据集不依赖真实 Git 仓库，测试结果稳定（随机种子固定）
    return mock_data.build("demo/workspace", force_synthetic=True)


def test_human_size_units() -> None:
    assert reporters.human_size(512) == "512 B"
    assert reporters.human_size(2048) == "2.00 KB"
    assert reporters.human_size(10 * 1024 * 1024) == "10.00 MB"


def test_markdown_covers_all_sections(view) -> None:
    markdown = reporters.render_markdown(view)
    for keyword in (
        "总体评价", "关键指标", "作者贡献", "提交活跃度", "文件热点",
        "大文件", "陈旧文件", "反模式清单", "提交规范", "复现方式",
    ):
        assert keyword in markdown
    assert view.snapshot.repo_name in markdown
    assert f"健康度 **{view.health_score:.0f} / 100**" in markdown


def test_html_is_standalone_document(view) -> None:
    page = reporters.render_html(view)
    assert page.startswith("<!DOCTYPE html>")
    assert "<table>" in page
    assert view.snapshot.repo_name in page
    assert f"{view.health_score:.0f}" in page


def test_csv_contains_all_sections(view) -> None:
    content = reporters.render_csv(view)
    header = content.splitlines()[0]
    assert header.startswith("类别,对象,提交数,占比")
    assert "作者" in content
    assert "反模式警告" in content
    assert "汇总" in content


def test_three_formats_share_the_same_numbers(view) -> None:
    """三种报告数据一致：同一个健康度和同一条反模式规则名必须同时出现。"""
    markdown = reporters.render_markdown(view)
    page = reporters.render_html(view)
    sheet = reporters.render_csv(view)

    health = f"{view.health_score:.0f}"
    assert health in markdown and health in page and health in sheet

    if view.warnings:
        rule = view.warnings[0].rule
        assert rule in markdown and rule in page and rule in sheet

    assert str(view.total_commits) in markdown and str(view.total_commits) in page


def test_write_report_creates_three_files(view, tmp_path: Path) -> None:
    written = reporters.write_report(view, ["markdown", "html", "csv"], tmp_path)
    assert len(written) == 3
    suffixes = {path.suffix for path in written}
    assert suffixes == {".md", ".html", ".csv"}
    for path in written:
        assert path.exists() and path.stat().st_size > 0


def test_write_report_csv_has_utf8_bom_for_excel(view, tmp_path: Path) -> None:
    (path,) = reporters.write_report(view, ["csv"], tmp_path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_write_report_rejects_unknown_format(view, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        reporters.write_report(view, ["pdf"], tmp_path)


def test_summary_reports_include_rows_and_failures() -> None:
    rows = [
        RepoSummary(repo_name="alpha", path="/tmp/alpha", commits=10, authors=2,
                    health_score=88.0, hotspot_count=1, stale_count=0, risk_level="low"),
        RepoSummary(repo_name="beta", path="/tmp/beta", commits=3, authors=1,
                    health_score=55.0, hotspot_count=2, stale_count=4, risk_level="medium"),
    ]
    failures = [BatchResult(path="/tmp/broken", repo_name="broken",
                            ok=False, error="not_a_git_repository: nope")]

    markdown = reporters.render_summary_markdown(rows, failures)
    assert "alpha" in markdown and "beta" in markdown and "broken" in markdown
    assert "not_a_git_repository" in markdown

    sheet = reporters.render_summary_csv(rows)
    lines = sheet.strip().splitlines()
    assert len(lines) == 3
    assert "alpha" in lines[1] and "beta" in lines[2]
