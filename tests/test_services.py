"""集成测试：统一分析服务（services.py）。

覆盖验收要求里"CLI 与 GUI 使用同一分析服务"和"单个仓库失败不影响其他任务"：

* 真仓库能读出真数据；
* 无效路径、非 Git 目录、非法配置都有可读错误码；
* 时间范围（window_days）真的会过滤提交；
* 批量分析并发执行、失败隔离、可取消。
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gui.contract import AnalysisView
from services import (
    AnalysisConfig,
    AnalysisError,
    AnalysisService,
    BatchAnalyzer,
    summarize_view,
)


def run_git(repo: Path, *args: str, env: dict | None = None) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=merged,
    )
    return result.stdout


def make_repo(root: Path, name: str = "health repo") -> Path:
    repo = root / name
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Alice")
    run_git(repo, "config", "user.email", "alice@example.com")
    (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "feat: initial app")
    run_git(repo, "tag", "v0.1.0")

    # 第二个作者提交一次，验证作者统计不是"全部同一人"
    run_git(repo, "config", "user.name", "Bob")
    run_git(repo, "config", "user.email", "bob@example.com")
    (repo / "app.py").write_text("print('hello world')\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "fix: greet properly")

    # 一条历史很早的提交，用于验证 window_days 过滤
    old_date = (datetime.now() - timedelta(days=400)).isoformat()
    (repo / "legacy.py").write_text("old\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(
        repo, "commit", "-m", "chore: old file",
        env={"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date},
    )
    return repo


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path)


def test_analyze_reads_real_repository(repo: Path) -> None:
    view = AnalysisService().analyze(repo)

    assert isinstance(view, AnalysisView)
    assert view.snapshot.repo_name == repo.name
    assert view.total_commits == 3          # 老提交也在全部历史里
    assert view.author_count == 2
    assert view.commit_calendar
    assert 0 <= view.health_score <= 100
    assert view.elapsed_seconds >= 0
    assert view.snapshot.tags == ("v0.1.0",)


def test_check_returns_repository_info(repo: Path) -> None:
    info = AnalysisService().check(repo)
    assert info.repo_name == repo.name
    assert info.commits == 3
    assert "main" in info.branches
    assert info.tags == ("v0.1.0",)


def test_analyze_missing_path_raises_readable_error(tmp_path: Path) -> None:
    with pytest.raises(AnalysisError) as excinfo:
        AnalysisService().analyze(tmp_path / "nope")
    assert excinfo.value.code == "path_not_found"
    assert "does not exist" in excinfo.value.message


def test_analyze_non_git_directory_raises(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(AnalysisError) as excinfo:
        AnalysisService().analyze(plain)
    assert excinfo.value.code == "not_a_git_repository"


def test_analyze_rejects_invalid_commit_pattern(repo: Path) -> None:
    config = AnalysisConfig(commit_pattern="^(feat")
    with pytest.raises(ValueError):
        AnalysisService().analyze(repo, config)


def test_gui_mode_falls_back_to_synthetic_data(tmp_path: Path) -> None:
    """GUI 用的 allow_synthetic=True：坏路径也不许抛错、不许白屏。"""
    view = AnalysisService(allow_synthetic=True).analyze(tmp_path / "nope")
    assert isinstance(view, AnalysisView)
    assert view.total_commits > 0


def test_window_days_filters_old_commits(repo: Path) -> None:
    view = AnalysisService().analyze(repo, AnalysisConfig(window_days=30))
    assert view.total_commits == 2           # 400 天前那条被过滤


def test_config_json_roundtrip(tmp_path: Path) -> None:
    config = AnalysisConfig(stale_days=30, window_days=90, commit_pattern=r"^(feat|fix): ")
    path = config.save_json(tmp_path / "config.json")
    loaded = AnalysisConfig.from_json(path)
    assert loaded == config

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["stale_days"] == 30


def test_config_rejects_unknown_field(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"stale_dayz": 30}', encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        AnalysisConfig.from_json(path)
    assert "stale_dayz" in str(excinfo.value)


def test_config_rejects_bad_values() -> None:
    with pytest.raises(ValueError):
        AnalysisConfig(stale_days=0).validate()
    with pytest.raises(ValueError):
        AnalysisConfig(single_maintainer_ratio=1.5).validate()
    with pytest.raises(ValueError):
        AnalysisConfig(window_days=-1).validate()


def test_batch_isolates_single_repository_failure(repo: Path, tmp_path: Path) -> None:
    analyzer = BatchAnalyzer(max_workers=2)
    results = analyzer.run([repo, tmp_path / "missing"])

    assert len(results) == 2
    assert results[0].ok and results[0].view is not None
    assert results[1].ok is False
    assert "path_not_found" in results[1].error
    # 成功仓库不受失败仓库影响
    assert results[0].view.total_commits == 3


def test_batch_progress_callback_counts(repo: Path) -> None:
    seen: list[tuple[str, int, int]] = []
    analyzer = BatchAnalyzer(max_workers=2)
    analyzer.run(
        [repo, repo],
        on_progress=lambda result, done, total: seen.append((result.repo_name, done, total)),
    )
    assert seen[-1][1:] == (2, 2)
    assert all(total == 2 for _, _, total in seen)


def test_batch_cancel_marks_unstarted_as_cancelled(repo: Path) -> None:
    import threading

    cancel = threading.Event()
    cancel.set()
    results = BatchAnalyzer(max_workers=2).run([repo, repo], cancel_event=cancel)
    assert all(result.cancelled for result in results)
    assert all(not result.ok for result in results)


def test_summarize_view_maps_contract_fields(repo: Path) -> None:
    view = AnalysisService().analyze(repo)
    summary = summarize_view(view)
    assert summary.repo_name == view.snapshot.repo_name
    assert summary.commits == view.total_commits
    assert summary.authors == view.author_count
    assert summary.health_score == view.health_score
    assert summary.risk_level in {"low", "medium", "high"}
