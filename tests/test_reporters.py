"""reportreporters.py）。

Notes"Markdown、HTML、CSV report"Notes"report"
—— Notes AnalysisView Notes
"""

from pathlib import Path

import pytest

from gui import mock_data
from gui.contract import RepoSummary
from core.services import BatchResult

from core import reporters


@pytest.fixture(scope="module")
def view():
    # Notes Git repository
    return mock_data.build("demo/workspace", force_synthetic=True)


def test_human_size_units() -> None:
    assert reporters.human_size(512) == "512 B"
    assert reporters.human_size(2048) == "2.00 KB"
    assert reporters.human_size(10 * 1024 * 1024) == "10.00 MB"


def test_markdown_covers_all_sections(view) -> None:
    markdown = reporters.render_markdown(view)
    for keyword in (
        "Overview", "Repository summary", "Author", "commits", "Hotspot files",
        "Large files", "Stale files", "anti-patterns", "Commit message quality",
        "Reproduce this report",
    ):
        assert keyword in markdown
    assert view.snapshot.repo_name in markdown
    assert f"Health score: **{view.health_score:.0f} / 100**" in markdown


def test_html_is_standalone_document(view) -> None:
    page = reporters.render_html(view)
    assert page.startswith("<!DOCTYPE html>")
    assert "<table>" in page
    assert view.snapshot.repo_name in page
    assert f"{view.health_score:.0f}" in page


def test_csv_contains_all_sections(view) -> None:
    content = reporters.render_csv(view)
    header = content.splitlines()[0]
    assert header.startswith("Category,Name,commits,ratio")
    assert "authors" in content
    assert "anti-patterns" in content
    assert "anti-patterns" in content


def test_three_formats_share_the_same_numbers(view) -> None:
    """report"""
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




