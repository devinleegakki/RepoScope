"""Tests for anti-pattern rules: triggering, warning structure, config impact."""

from __future__ import annotations

from metrics import compute_metrics
from reposcope.models_analysis import AnalysisConfig
from rules import (
    detect_all,
    detect_commit_messages,
    detect_hotspots,
    detect_large_files,
    detect_release_stale_illusion,
    detect_single_maintainer,
    detect_stale_files,
)


REQUIRED_FIELDS = {"name", "level", "actual_value", "threshold", "suggestion"}


def assert_warning(w, expected_name: str):
    assert w is not None
    d = w.to_dict()
    assert REQUIRED_FIELDS.issubset(d.keys())
    assert d["name"] == expected_name
    assert d["level"] in {"high", "medium", "low"}
    assert d["suggestion"]
    assert w.target


class TestIndividualRules:
    def test_single_maintainer(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        w = detect_single_maintainer(m, config)
        # 66% < 70% default -> not triggered
        assert w is None
        # lower threshold -> triggered
        strict = AnalysisConfig(single_maintainer_ratio=0.5)
        w2 = detect_single_maintainer(m, strict)
        assert_warning(w2, "Single-maintainer risk")
        assert w2.level == "high"
        assert w2.actual_value > w2.threshold

    def test_release_stale_illusion(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        w = detect_release_stale_illusion(m, config)
        assert_warning(w, "Activity-without-release illusion")
        assert w.actual_value == 500
        assert w.threshold == 365

    def test_release_stale_ignored_when_inactive(self, base_snapshot, config, as_of):
        # shift all commits older than the recent window -> no recent activity
        for c in base_snapshot.commits:
            from datetime import timedelta
            c.timestamp = c.timestamp - timedelta(days=200)
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        assert m.recent_active is False
        assert detect_release_stale_illusion(m, config) is None

    def test_hotspot_threshold_change(self, base_snapshot, as_of):
        m = compute_metrics(base_snapshot, AnalysisConfig(), as_of=as_of)
        assert detect_hotspots(m, AnalysisConfig(hotspot_changes=10)) is None
        w = detect_hotspots(m, AnalysisConfig(hotspot_changes=2))
        assert_warning(w, "High-frequency change hotspot")
        assert w.actual_value == 3

    def test_large_file(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        w = detect_large_files(m, config)
        assert_warning(w, "Large / binary file risk")
        assert w.actual_value >= config.large_file_mb
        assert any(e["path"] == "blob.bin" for e in w.evidence["affected_files"])

    def test_stale_file(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        w = detect_stale_files(m, config)
        assert_warning(w, "Zombie file")
        assert w.actual_value > config.stale_days

    def test_commit_message(self, base_snapshot, config, as_of):
        m = compute_metrics(base_snapshot, config, as_of=as_of)
        w = detect_commit_messages(m, config)
        assert_warning(w, "Non-standard commit message")
        assert w.level == "low"
        assert w.actual_value == 0.75


class TestDetectAll:
    def test_returns_all_triggered(self, base_snapshot, config, as_of):
        # use a stricter ratio so the maintainer rule triggers too
        cfg = AnalysisConfig(single_maintainer_ratio=0.5)
        m = compute_metrics(base_snapshot, cfg, as_of=as_of)
        warnings = detect_all(m, cfg)
        names = {w.name for w in warnings}
        assert "Single-maintainer risk" in names
        assert "Large / binary file risk" in names
        assert "Zombie file" in names
        assert "Non-standard commit message" in names
        assert len(warnings) >= 5

    def test_severity_ordering(self, base_snapshot, as_of):
        cfg = AnalysisConfig(single_maintainer_ratio=0.5)
        m = compute_metrics(base_snapshot, cfg, as_of=as_of)
        warnings = detect_all(m, cfg)
        order = {"high": 0, "medium": 1, "low": 2}
        ranks = [order[w.level] for w in warnings]
        assert ranks == sorted(ranks)

    def test_all_warnings_well_formed(self, base_snapshot, as_of):
        cfg = AnalysisConfig(single_maintainer_ratio=0.5)
        m = compute_metrics(base_snapshot, cfg, as_of=as_of)
        for w in detect_all(m, cfg):
            assert_warning(w, w.name)

    def test_rule_level_from_config(self, base_snapshot, as_of):
        cfg = AnalysisConfig(rule_levels={"stale_file": "high"})
        m = compute_metrics(base_snapshot, cfg, as_of=as_of)
        w = detect_stale_files(m, cfg)
        assert w.level == "high"




