"""Tests for analysis data models: config loading, coercion, (de)serialisation."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from reposcope.models_analysis import (
    AnalysisConfig,
    RepositoryMetrics,
    Warning,
    as_utc_datetime,
)


class TestAsUtcDatetime:
    def test_iso_string_with_z(self):
        dt = as_utc_datetime("2026-11-24T00:00:00Z")
        assert dt == datetime(2026, 11, 24, tzinfo=timezone.utc)

    def test_naive_datetime_assumed_utc(self):
        dt = as_utc_datetime(datetime(2026, 11, 24, 12, 0))
        assert dt.tzinfo is not None
        assert dt.hour == 12

    def test_unix_timestamp(self):
        dt = as_utc_datetime(0)
        assert dt == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_none_and_garbage(self):
        assert as_utc_datetime(None) is None
        assert as_utc_datetime("not-a-date") is None


class TestAnalysisConfig:
    def test_defaults_match_proposal(self):
        c = AnalysisConfig()
        assert c.stale_days == 180
        assert c.large_file_mb == 10.0
        assert c.single_maintainer_ratio == 0.70
        assert c.release_stale_days == 365
        assert c.hotspot_changes == 10
        assert c.commit_message_pattern == r"^(feat|fix|docs|refactor)(\(.+\))?:"

    def test_default_rules_yaml_equals_defaults(self):
        from pathlib import Path
        yaml_path = Path(__file__).resolve().parents[1] / "default_rules.yaml"
        c = AnalysisConfig.from_yaml(yaml_path)
        assert c.stale_days == AnalysisConfig().stale_days
        assert c.rule_levels["single_maintainer"] == "high"

    def test_from_dict_overrides_and_ignores_unknown(self):
        c = AnalysisConfig.from_dict({"stale_days": 30, "unknown_key": 1})
        assert c.stale_days == 30
        assert not hasattr(c, "unknown_key")

    def test_json_round_trip(self, tmp_path):
        c = AnalysisConfig.from_dict({"large_file_mb": 3.5})
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps(c.to_dict()), encoding="utf-8")
        loaded = AnalysisConfig.from_json(p)
        assert loaded.large_file_mb == 3.5

    def test_invalid_bucket_and_ratio_rejected(self):
        with pytest.raises(ValueError):
            AnalysisConfig(trend_bucket="year")
        with pytest.raises(ValueError):
            AnalysisConfig(single_maintainer_ratio=1.5)


class TestWarning:
    def test_to_dict_has_required_fields(self):
        w = Warning("r", "high", 0.9, 0.7, "do something")
        d = w.to_dict()
        for key in ("name", "level", "actual_value", "threshold", "suggestion"):
            assert key in d

    def test_bad_level_rejected(self):
        with pytest.raises(ValueError):
            Warning("r", "critical", 1, 0, "x")

    def test_metrics_to_dict_references_config_window(self):
        m = RepositoryMetrics(recent_days=45, observation_days=90)
        assert m.to_dict()["recent_days"] == 45




