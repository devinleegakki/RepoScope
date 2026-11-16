"""Tests for metrics: reproducibility, each indicator, config independence."""

from __future__ import annotations

from datetime import timedelta

from metrics import compute_metrics
from models_analysis import AnalysisConfig


class TestComputeMetrics:
    def test_totals(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.total_commits == 4
        assert m.total_authors == 2  # alice, bob
        assert m.total_files == 4
        assert m.repo_name == "fixture-repo"

    def test_deterministic_from_fixed_fixture(self, base_snapshot, config, as_of):
        a = compute_metrics(base_snapshot, config, as_of=as_of)
        b = compute_metrics(base_snapshot, config, as_of=as_of)
        assert a.to_dict() == b.to_dict()

    def test_commit_trend_day_bucket(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        # 3 commits within the 90-day window (c4 at 400 days is excluded)
        assert sum(m.commit_trend.values()) == 3
        assert all(len(k) == 10 and k[4] == "-" for k in m.commit_trend)  # YYYY-MM-DD

    def test_trend_bucket_switch(self, base_snapshot, as_of):
        weekly = compute_metrics(
            base_snapshot, AnalysisConfig(trend_bucket="week"), as_of=as_of
        )
        monthly = compute_metrics(
            base_snapshot, AnalysisConfig(trend_bucket="month"), as_of=as_of
        )
        assert any("-W" in k for k in weekly.commit_trend)
        assert all(len(k) == 7 for k in monthly.commit_trend)

    def test_author_contribution_ratios(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        by_author = {a.author: a for a in m.author_contributions}
        alice = by_author["alice"]
        # window: alice 2 of 3 commits
        assert abs(alice.ratio - 2 / 3) < 1e-6
        assert alice.author == "alice"

    def test_maintainer_concentration(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        # recent 90 days: alice 2, bob 1 -> 2/3
        assert m.top_author == "alice"
        assert abs(m.maintainer_concentration - 2 / 3) < 1e-6

    def test_line_changes(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.total_insertions == 48  # 40+5+2+1
        assert m.total_deletions == 14   # 10+3+1+0

    def test_file_hotspots_sorted(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.file_hotspots
        assert m.file_hotspots[0].path == "core.py"
        assert m.file_hotspots[0].changes == 3
        changes = [f.changes for f in m.file_hotspots]
        assert changes == sorted(changes, reverse=True)

    def test_stale_files(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        paths = {f.path for f in m.stale_files}
        assert "zombie.py" in paths     # 500 days > 180
        assert "core.py" not in paths   # 15 days

    def test_large_and_binary_files(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        paths = {f.path for f in m.large_files}
        assert "blob.bin" in paths      # 25 MB + binary
        blob = next(f for f in m.large_files if f.path == "blob.bin")
        assert blob.is_binary is True

    def test_stale_threshold_change_affects_result(self, base_snapshot, as_of):
        strict = compute_metrics(
            base_snapshot, AnalysisConfig(stale_days=10), as_of=as_of
        )
        loose = compute_metrics(
            base_snapshot, AnalysisConfig(stale_days=200), as_of=as_of
        )
        assert len(strict.stale_files) > len(loose.stale_files)

    def test_commit_compliance(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.commit_compliance.checked == 4
        assert m.commit_compliance.valid == 3
        assert abs(m.commit_compliance.pass_rate - 0.75) < 1e-6
        assert any(v["sha"] == "c3" for v in m.commit_compliance.violations)

    def test_release_stale_days(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.days_since_last_tag == 500
        assert m.last_tag == "v0.1"
        assert m.recent_active is True

    def test_empty_snapshot_is_safe(self, as_of):
        from types import SimpleNamespace
        empty = SimpleNamespace(repo_name="empty", commits=[], files=[], tags=[])
        m = compute_metrics(empty, AnalysisConfig(), as_of=as_of)
        assert m.total_commits == 0
        assert m.commit_trend == {}
        assert m.maintainer_concentration == 0.0
        assert m.commit_compliance.pass_rate == 1.0
        assert m.days_since_last_tag is None
