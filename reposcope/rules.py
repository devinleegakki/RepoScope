"""Anti-pattern detection rules for RepoScope.

Owner: TYB  (task 2 - statistical metrics & anti-pattern detection)
Course: INT6181 Applied Programming with Python

Each rule consumes :class:`RepositoryMetrics` plus :class:`AnalysisConfig` and
emits a :class:`Warning` containing name, level, actual value, threshold and a
suggested action. Rules never touch Git or the GUI, so results are fully
reproducible from a metrics fixture.
"""

from __future__ import annotations

from typing import List, Optional

try:  # works both as ``reposcope.rules`` and as a top-level ``rules``
    from .models_analysis import AnalysisConfig, RepositoryMetrics, Warning
except ImportError:  # pragma: no cover - fallback when loaded without package context
    from models_analysis import AnalysisConfig, RepositoryMetrics, Warning  # type: ignore[no-redef]


# Human-readable names (also used as report/table labels).
_RULE_NAMES = {
    "single_maintainer": "Single-maintainer risk",
    "release_stale_illusion": "Activity-without-release illusion",
    "hotspot_changes": "High-frequency change hotspot",
    "large_file": "Large / binary file risk",
    "stale_file": "Zombie file",
    "commit_message": "Non-standard commit message",
}

# Where the GUI should jump when the warning is clicked.
_RULE_TARGETS = {
    "single_maintainer": "authors",
    "release_stale_illusion": "trend",
    "hotspot_changes": "hotspots",
    "large_file": "large_files",
    "stale_file": "staleness",
    "commit_message": "compliance",
}


def _level(config: AnalysisConfig, rule_id: str) -> str:
    return config.rule_levels.get(rule_id, "low")


def detect_single_maintainer(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when one author produced more than ``single_maintainer_ratio`` of recent commits."""
    actual = metrics.maintainer_concentration
    threshold = config.single_maintainer_ratio
    if actual <= threshold or not metrics.top_author:
        return None
    return Warning(
        name=_RULE_NAMES["single_maintainer"],
        level=_level(config, "single_maintainer"),
        actual_value=round(actual, 4),
        threshold=threshold,
        suggestion="Add co-maintainers and improve handover documentation; review bus-factor risk.",
        message=(
            f"'{metrics.top_author}' authored {actual:.0%} of the last "
            f"{metrics.recent_days} days of commits (threshold {threshold:.0%})."
        ),
        target=_RULE_TARGETS["single_maintainer"],
        evidence={"top_author": metrics.top_author, "recent_days": metrics.recent_days},
    )


def detect_release_stale_illusion(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when commits are recent but the latest tag is older than the allowed window."""
    days = metrics.days_since_last_tag
    if days is None or not metrics.recent_active or days <= config.release_stale_days:
        return None
    return Warning(
        name=_RULE_NAMES["release_stale_illusion"],
        level=_level(config, "release_stale_illusion"),
        actual_value=days,
        threshold=config.release_stale_days,
        suggestion="Establish a regular release cadence; add version tags and a changelog.",
        message=(
            f"The repository is still active, but the latest tag "
            f"'{metrics.last_tag or '(none)'}' is {days} days old "
            f"(threshold {config.release_stale_days} days)."
        ),
        target=_RULE_TARGETS["release_stale_illusion"],
        evidence={"last_tag": metrics.last_tag, "last_commit_date": _iso(metrics.last_commit_date)},
    )


def detect_hotspots(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when the hottest file was modified more than ``hotspot_changes`` times."""
    if not metrics.file_hotspots:
        return None
    hottest = metrics.file_hotspots[0]
    actual = hottest.changes
    if actual <= config.hotspot_changes:
        return None
    affected = [
        {"path": f.path, "changes": f.changes, "lines_changed": f.lines_changed}
        for f in metrics.file_hotspots
        if f.changes > config.hotspot_changes
    ]
    return Warning(
        name=_RULE_NAMES["hotspot_changes"],
        level=_level(config, "hotspot_changes"),
        actual_value=actual,
        threshold=config.hotspot_changes,
        suggestion="Review module boundaries, strengthen test coverage, and consider splitting the file.",
        message=(
            f"'{hottest.path}' was changed {actual} times in the observation window "
            f"(threshold {config.hotspot_changes})."
        ),
        target=_RULE_TARGETS["hotspot_changes"],
        evidence={"affected_files": affected},
    )


def detect_large_files(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when large or binary files are present."""
    if not metrics.large_files:
        return None
    largest = metrics.large_files[0]
    affected = [
        {
            "path": f.path,
            "size_mb": round(f.size_bytes / (1024 * 1024), 3),
            "is_binary": f.is_binary,
        }
        for f in metrics.large_files
    ]
    return Warning(
        name=_RULE_NAMES["large_file"],
        level=_level(config, "large_file"),
        actual_value=round(largest.size_bytes / (1024 * 1024), 3),
        threshold=config.large_file_mb,
        suggestion="Consider Git LFS, external storage, or removing generated/binary artefacts.",
        message=(
            f"{len(metrics.large_files)} large/binary file(s) found; "
            f"largest is '{largest.path}' at {largest.size_bytes / (1024 * 1024):.2f} MB "
            f"(threshold {config.large_file_mb} MB)."
        ),
        target=_RULE_TARGETS["large_file"],
        evidence={"affected_files": affected},
    )


def detect_stale_files(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when source files have not been updated for more than ``stale_days``."""
    if not metrics.stale_files:
        return None
    oldest = metrics.stale_files[0]
    actual = oldest.stale_days or 0
    affected = [
        {"path": f.path, "stale_days": f.stale_days, "last_modified": _iso(f.last_modified)}
        for f in metrics.stale_files
    ]
    return Warning(
        name=_RULE_NAMES["stale_file"],
        level=_level(config, "stale_file"),
        actual_value=actual,
        threshold=config.stale_days,
        suggestion="Confirm whether these files are still in use; document them or remove abandoned code.",
        message=(
            f"{len(metrics.stale_files)} file(s) unchanged for more than {config.stale_days} days; "
            f"oldest is '{oldest.path}' at {actual} days."
        ),
        target=_RULE_TARGETS["stale_file"],
        evidence={"affected_files": affected},
    )


def detect_commit_messages(metrics: RepositoryMetrics, config: AnalysisConfig) -> Optional[Warning]:
    """Warn when commit messages fail the configured convention check."""
    compliance = metrics.commit_compliance
    if compliance.checked == 0 or compliance.valid == compliance.checked:
        return None
    violations = compliance.violations
    return Warning(
        name=_RULE_NAMES["commit_message"],
        level=_level(config, "commit_message"),
        actual_value=round(compliance.pass_rate, 4),
        threshold=1.0,
        suggestion="Adopt a commit-message template and agree on a conventional-commit prefix.",
        message=(
            f"{compliance.checked - compliance.valid}/{compliance.checked} commit messages "
            f"failed the convention check (pass rate {compliance.pass_rate:.0%})."
        ),
        target=_RULE_TARGETS["commit_message"],
        evidence={"examples": violations[:5], "pattern": config.commit_message_pattern},
    )


_ALL_RULES = (
    detect_single_maintainer,
    detect_release_stale_illusion,
    detect_hotspots,
    detect_large_files,
    detect_stale_files,
    detect_commit_messages,
)


def detect_all(metrics: RepositoryMetrics, config: Optional[AnalysisConfig] = None) -> List[Warning]:
    """Run every anti-pattern rule and return the triggered warnings.

    Warnings are ordered by severity (high -> medium -> low) for direct use in
    the dashboard's anti-pattern centre and report summary.
    """
    cfg = config or AnalysisConfig()
    warnings = [w for rule in _ALL_RULES if (w := rule(metrics, cfg)) is not None]
    order = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(key=lambda w: order.get(w.level, 3))
    return warnings


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt is not None else None
