"""End-to-end test of the snapshot -> metrics -> warnings pipeline."""

from __future__ import annotations

from pathlib import Path

from metrics import compute_metrics
from reposcope.models_analysis import AnalysisConfig
from rules import detect_all


def test_full_pipeline_from_default_yaml(base_snapshot, as_of):
    yaml_path = Path(__file__).resolve().parents[1] / "default_rules.yaml"
    config = AnalysisConfig.from_yaml(yaml_path)
    config = AnalysisConfig.from_dict({**config.to_dict(), "single_maintainer_ratio": 0.5})

    metrics = compute_metrics(base_snapshot, config, as_of=as_of)
    warnings = detect_all(metrics, config)

    assert metrics.total_commits == 4
    assert warnings
    # Both downstream consumers (GUI tables / reports) can serialise cleanly.
    assert isinstance(metrics.to_dict()["commit_trend"], dict)
    for w in warnings:
        assert isinstance(w.to_dict(), dict)
        assert "suggestion" in w.to_dict()


def test_config_change_produces_different_warnings(base_snapshot, as_of):
    lenient = AnalysisConfig(single_maintainer_ratio=0.5, hotspot_changes=2)
    strict = AnalysisConfig(single_maintainer_ratio=0.95, hotspot_changes=99)

    m_lenient = compute_metrics(base_snapshot, lenient, as_of=as_of)
    m_strict = compute_metrics(base_snapshot, strict, as_of=as_of)

    w_lenient = {w.name for w in detect_all(m_lenient, lenient)}
    w_strict = {w.name for w in detect_all(m_strict, strict)}

    assert "Single-maintainer risk" in w_lenient
    assert "Single-maintainer risk" not in w_strict
    assert "High-frequency change hotspot" in w_lenient
    assert "High-frequency change hotspot" not in w_strict




