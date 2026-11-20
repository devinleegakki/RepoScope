"""Stable data contract between the analysis engine and GUI pages.

The adapter keeps PySide6 widgets independent from concrete metric models.

files**GUI type**
Notes ``AnalysisView`` Notes
Notes ``adapt()`` Notes

rules code review Notes

* ``gui/`` Notes import Notes``models.py`` Notes ``PySide6``。
* Notes ``from core.git_reader import ...``、``from metrics import ...``。
  Notes
* Notes ``AnalysisView``，Notes

    The stable view contract is documented in ``docs/API_REFERENCE.md``::

    snapshot / health_score / total_commits ...   LTY(git_reader) + TYB(metrics)
    commit_hygiene                                TYB(metrics + rules)
    warnings[...].condition/actual/threshold/action   TYB(rules)   ← pending
    RepoSummary                                   Wyh(batch)   ← pending

Notes ``# TODO(TYB)`` Notes
display"pending"），Notes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, Sequence, Tuple, runtime_checkable

from core.models import RepositorySnapshot

# display"—"Notes 0，
# Notes"Notes 0 analysis"Notes
PENDING = "pending"


@dataclass(frozen=True)
class FileStat:
    """files / files / files"""

    path: str
    change_count: int = 0
    author_count: int = 0
    size_bytes: int = 0
    days_since_change: int = 0

    # --- TODO(TYB): metrics.py analysis ---
    changed_lines: int = 0          # files
    file_type: str = ""             # type
    is_binary: bool = False         # files


@dataclass(frozen=True)
class AuthorStat:
    """repository"""

    name: str
    commits: int
    insertions: int = 0
    deletions: int = 0
    share: float = 0.0

    # --- TODO(TYB): current 90 commits"high"Notes ---
    # Notes -1.0 display "—"。
    recent_90d_share: float = -1.0


@dataclass(frozen=True)
class Violation:
    """commits"""

    commit_hash: str
    message: str
    reason: str = ""


@dataclass(frozen=True)
class CommitHygiene:
    """commits 4.6）。"""

    pass_rate: float = -1.0         # 0~1，-1 Notes
    total: int = 0
    passed: int = 0
    pattern: str = ""
    violations: Tuple[Violation, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HealthDimension:
    """One explainable score shown in the dashboard health overview."""

    name: str
    score: float
    level: str = "low"
    issue_count: int = 0
    hint: str = ""


@dataclass(frozen=True)
class DashboardStats:
    """Precomputed dashboard-only aggregates; widgets do not recalculate them."""

    dimensions: Tuple[HealthDimension, ...] = field(default_factory=tuple)
    risk_counts: Mapping[str, int] = field(default_factory=dict)
    recent_commits: Mapping[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Warning:
    """rules

    display"Notes"，
    Notes 4.2 anti-patterns
    """

    rule: str
    severity: str                   # high / medium / low
    message: str
    target: str = ""

    # --- TODO(TYB): rules.py anti-patterns ---
    condition: str = ""             # Notes"commits ≥ 70%"
    actual: str = ""                # Notes"82%"
    threshold: str = ""             # configuration"70%"
    action: str = ""                # Notes"Notes code review Notes"

    @property
    def has_evidence(self) -> bool:
        """information"pending"。"""
        return all((self.condition, self.actual, self.threshold, self.action))


@dataclass(frozen=True)
class RepoSummary:
    """repository 4.8）。"""

    repo_name: str
    path: str = ""
    commits: int = 0
    authors: int = 0
    health_score: float = 0.0
    hotspot_count: int = 0
    stale_count: int = 0
    risk_level: str = "low"         # low / medium / high


@runtime_checkable
class AnalysisView(Protocol):
    """NotesTYB Notes ``AnalysisResult`` Notes

    Notes
    See ``docs/API_REFERENCE.md`` for the public field mapping.
    """

    snapshot: RepositorySnapshot
    health_score: float
    total_commits: int
    author_count: int
    file_count: int
    commit_calendar: Mapping[str, int]
    author_stats: Sequence[AuthorStat]
    hotspot_files: Sequence[FileStat]
    large_files: Sequence[FileStat]
    stale_files: Sequence[FileStat]
    warnings: Sequence[Warning]
    elapsed_seconds: float

    # --- TODO(TYB) / TODO(Wyh) ---
    commit_hygiene: CommitHygiene   # Notes"commits"
    risk_level: str                 # Notes
    dashboard_stats: DashboardStats


ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class AnalysisRequest:
    """analysis GUI settings

    Notes TYB Notes ``AnalysisConfig`` Notes
    Notes
    """

    repo_path: str
    stale_days: int = 180
    large_file_mb: int = 10
    hotspot_changes: int = 10
    release_stale_days: int = 365
    single_maintainer_ratio: float = 0.70
    window_days: int = 0            # 0 = Notes30 / 90 / 365
    commit_pattern: str = r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: "
    max_function_lines: int = 80
    max_file_lines: int = 500
    min_test_ratio: float = 0.05
    ownership_ratio: float = 0.80
    enable_dependency_scan: bool = True
    enable_secret_scan: bool = True


def risk_of(score: float) -> str:
    """rules"""
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def adapt(result: object, snapshot: RepositorySnapshot | None = None) -> AnalysisView:
    """Notes TYB Notes ``AnalysisResult`` Notes ``AnalysisView``。

    TODO(Notes): Notes ``metrics.py`` Notes
    Notes::

        result.metrics.health_score      -> health_score
        result.metrics.total_commits     -> total_commits
        result.metrics.commit_calendar   -> commit_calendar
        result.metrics.author_stats      -> author_stats   (Notes)
        result.metrics.hotspot_files     -> hotspot_files
        result.metrics.large_files       -> large_files
        result.metrics.stale_files       -> stale_files
        result.metrics.warnings          -> warnings
        result.metrics.commit_hygiene    -> commit_hygiene

    display 0 analysis
    """
    from dataclasses import dataclass
    from types import SimpleNamespace
    metrics = getattr(result, "metrics", result)
    snap = snapshot or getattr(result, "snapshot", None)
    if snap is None:
        raise TypeError("adapt Notes snapshot")
    authors = []
    for a in getattr(metrics, "author_contributions", []):
        authors.append(AuthorStat(a.author, a.commits, 0, 0, a.ratio, a.recent_ratio))
    def files(items):
        return [FileStat(f.path, f.changes, 0, f.size_bytes, f.stale_days or 0,
                          f.lines_changed, f.file_type, f.is_binary) for f in items]
    compliance = getattr(metrics, "commit_compliance", None)
    hygiene = CommitHygiene(compliance.pass_rate, compliance.checked, compliance.valid,
                            getattr(result, "commit_message_pattern", ""),
                            tuple(Violation(v.get("sha", ""), v.get("message", ""), "; ".join(v.get("reasons", []))) for v in compliance.violations)) if compliance else CommitHygiene()
    warnings = []
    for w in getattr(result, "warnings", []):
        warnings.append(Warning(w.name, w.level, w.message, w.target, str(w.threshold), str(w.actual_value), str(w.threshold), w.suggestion))
    q = getattr(metrics, "code_quality", None)
    extra = {
        "code_quality": q, "ownership": getattr(metrics, "ownership", None),
        "dependencies": getattr(metrics, "dependencies", None), "security_findings": getattr(metrics, "security_findings", []),
    }
    risk_counts = {level: sum(1 for w in warnings if w.severity == level) for level in ("high", "medium", "low")}
    q = getattr(metrics, "code_quality", None)
    own = getattr(metrics, "ownership", None)
    dep = getattr(metrics, "dependencies", None)
    findings = getattr(metrics, "security_findings", [])
    quality_issues = (len(getattr(q, "long_functions", [])) + len(getattr(q, "long_files", [])) +
                      getattr(q, "bare_except_count", 0)) if q else 0
    security_issues = len(findings) + (len(getattr(dep, "unpinned", [])) + len(getattr(dep, "duplicates", [])) if dep else 0)
    dimensions = (
        HealthDimension("Git activity", min(100.0, len(metrics.commit_trend) / 30 * 100), "low" if len(metrics.commit_trend) >= 30 else "medium", 0, f"{len(metrics.commit_trend)} active days"),
        HealthDimension("Ownership balance", max(0.0, 100 - len(getattr(own, "high_risk_files", [])) * 10), "high" if getattr(own, "high_risk_files", []) else "low", len(getattr(own, "high_risk_files", [])), f"{len(getattr(own, 'high_risk_files', []))} files"),
        HealthDimension("Code quality", max(0.0, 100 - quality_issues * 8), "high" if quality_issues >= 5 else ("medium" if quality_issues else "low"), quality_issues, f"{quality_issues} issues"),
        HealthDimension("Dependencies and security", max(0.0, 100 - security_issues * 15), "high" if findings else ("medium" if security_issues else "low"), security_issues, f"{security_issues} issues"),
        HealthDimension("commits", hygiene.pass_rate * 100 if hygiene and hygiene.pass_rate >= 0 else 0, "low" if hygiene and hygiene.pass_rate >= .8 else "medium", (hygiene.total - hygiene.passed) if hygiene else 0, f"passed {hygiene.pass_rate:.0%}" if hygiene else "pending"),
    )
    recent = {}
    calendar = dict(metrics.commit_trend)
    for days in (7, 30, 90):
        recent[days] = sum(calendar.values()) if days == 90 else sum(list(calendar.values())[-days:])
    stats = DashboardStats(dimensions=dimensions, risk_counts=risk_counts, recent_commits=recent)
    return SimpleNamespace(snapshot=snap, health_score=max(0.0, 100.0 - 10.0 * len(warnings)),
        total_commits=metrics.total_commits, author_count=metrics.total_authors,
        file_count=metrics.total_files, commit_calendar=metrics.commit_trend,
        author_stats=tuple(authors), hotspot_files=tuple(files(metrics.file_hotspots)),
        large_files=tuple(files(metrics.large_files)), stale_files=tuple(files(metrics.stale_files)),
        warnings=tuple(warnings), elapsed_seconds=0.0, commit_hygiene=hygiene,
        risk_level=risk_of(max(0.0, 100.0 - 10.0 * len(warnings))), dashboard_stats=stats, **extra)




