"""Notes

Notes LTY / TYB / Wyh display
Notes ``build()`` analysis

Notes ``git_reader.GitReader`` repository
Notes

**files**，Notes ``TEMP``。
TYB Notes ``metrics.py`` Notes ``from metrics import analyse``，
Notes
"""

from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence

from core.models import Commit, FileRecord, RepositorySnapshot

from .contract import (
    AuthorStat,
    CommitHygiene,
    DashboardStats,
    HealthDimension,
    FileStat,
    ProgressCallback,
    Violation,
    Warning,
    risk_of,
)

_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".ttf"}


@dataclass
class MockView:
    """Notes ``AnalysisView`` Notes"""

    snapshot: RepositorySnapshot
    health_score: float = 0.0
    total_commits: int = 0
    author_count: int = 0
    file_count: int = 0
    commit_calendar: Mapping[str, int] = field(default_factory=dict)
    author_stats: Sequence[AuthorStat] = field(default_factory=tuple)
    hotspot_files: Sequence[FileStat] = field(default_factory=tuple)
    large_files: Sequence[FileStat] = field(default_factory=tuple)
    stale_files: Sequence[FileStat] = field(default_factory=tuple)
    warnings: Sequence[Warning] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0
    commit_hygiene: CommitHygiene = field(default_factory=CommitHygiene)
    risk_level: str = "low"
    dashboard_stats: DashboardStats = field(default_factory=DashboardStats)


def build(
    repo_path: str,
    on_progress: ProgressCallback | None = None,
    *,
    stale_days: int = 180,
    large_file_mb: int = 10,
    hotspot_changes: int = 10,
    commit_pattern: str = r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: ",
    force_synthetic: bool = False,
) -> MockView:
    """analysis

    NotesTYB Notes ``metrics.py`` Notes
    Notes ``_compute`` Notes

    ``force_synthetic=True`` repository
    160 repository 10 commits
    Notes
    """
    report = on_progress or (lambda percent, message: None)
    started = datetime.now()

    report(5, "repository")
    snapshot = None if force_synthetic else _read_real_snapshot(repo_path, report)
    if snapshot is None:
        report(20, "Preparing demo data" if force_synthetic else "Loading repository")
        snapshot = _synthetic_snapshot(repo_path)

    report(60, "Computing metrics")
    view = _compute(
        snapshot,
        stale_days=stale_days,
        large_file_mb=large_file_mb,
        hotspot_changes=hotspot_changes,
        commit_pattern=commit_pattern,
    )

    report(95, "Preparing dashboard")
    view.elapsed_seconds = (datetime.now() - started).total_seconds()
    report(100, "complete")
    return view


# --------------------------------------------------------------------------
# error None，Notes
# --------------------------------------------------------------------------
def _read_real_snapshot(repo_path: str, report: ProgressCallback) -> RepositorySnapshot | None:
    try:
        from core.git_reader import GitReader
    except ImportError:
        return None
    try:
        report(15, "commits")
        reader = GitReader(repo_path)
        reader.validate()
        report(40, "files")
        return reader.read_snapshot()
    except Exception:  # error
        return None


# --------------------------------------------------------------------------
# TEMP: NotesTYB Notes metrics.py remove
# --------------------------------------------------------------------------
def _naive(value: datetime | None) -> datetime | None:
    """time TypeError。"""
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _compute(
    snapshot: RepositorySnapshot,
    *,
    stale_days: int,
    large_file_mb: int,
    hotspot_changes: int,
    commit_pattern: str,
) -> MockView:
    commits = snapshot.commits
    files = snapshot.files
    now = datetime.now()

    calendar: Counter[str] = Counter()
    for commit in commits:
        calendar[_naive(commit.authored_at).strftime("%Y-%m-%d")] += 1

    # -- authors ------------------------------------------------------
    per_author: Counter[str] = Counter()
    insertions: Counter[str] = Counter()
    deletions: Counter[str] = Counter()
    recent: Counter[str] = Counter()
    cutoff = now - timedelta(days=90)
    for commit in commits:
        name = commit.author_name
        per_author[name] += 1
        insertions[name] += commit.insertions
        deletions[name] += commit.deletions
        if _naive(commit.authored_at) >= cutoff:
            recent[name] += 1
    total = sum(per_author.values()) or 1
    author_stats = [
        AuthorStat(
            name=name,
            commits=count,
            insertions=insertions[name],
            deletions=deletions[name],
            share=count / total,
            recent_90d_share=(recent[name] / count) if count else 0.0,
        )
        for name, count in per_author.most_common(12)
    ]

    # -- files ------------------------------------------------------
    changes: Counter[str] = Counter()
    for commit in commits:
        for path in commit.files_changed:
            changes[path] += 1

    # TEMP: filesgit log --numstat Notes TYB Notes
    # Notes"Notes × Notes 12 Notes"Notes
    def _changed_lines(path: str) -> int:
        return changes[path] * 12

    large_bytes = large_file_mb * 1024 * 1024
    hotspots = [
        FileStat(
            path=path,
            change_count=count,
            author_count=min(count, len(per_author)),
            changed_lines=_changed_lines(path),
            file_type=Path(path).suffix.lstrip("."),
            is_binary=Path(path).suffix.lower() in _BINARY_SUFFIXES,
        )
        for path, count in changes.most_common()
        if count >= hotspot_changes
    ][:50]
    large = [
        FileStat(
            path=f.path,
            size_bytes=f.size_bytes,
            change_count=changes.get(f.path, 0),
            changed_lines=_changed_lines(f.path),
            file_type=f.file_type,
            is_binary=f.file_type.lower() in {s.lstrip(".") for s in _BINARY_SUFFIXES},
        )
        for f in sorted(files, key=lambda item: item.size_bytes, reverse=True)
        if f.size_bytes >= large_bytes
    ][:50]
    stale = [
        FileStat(
            path=f.path,
            days_since_change=(now - _naive(f.modified_at)).days,
            change_count=changes.get(f.path, 0),
            size_bytes=f.size_bytes,
            changed_lines=_changed_lines(f.path),
            file_type=f.file_type,
        )
        for f in files
        if _naive(f.modified_at) and (now - _naive(f.modified_at)).days >= stale_days
    ][:50]

    # -- commits --------------------------------------------------
    pattern = re.compile(commit_pattern) if commit_pattern else None
    violations: list[Violation] = []
    passed = 0
    for commit in commits:
        if pattern is None or pattern.search(commit.message):
            passed += 1
        else:
            violations.append(
                Violation(
                    commit_hash=commit.hash[:8],
                    message=commit.message.splitlines()[0][:60] if commit.message else "",
                    reason="Commit messages should follow the configured pattern",
                )
            )
    hygiene = CommitHygiene(
        pass_rate=(passed / len(commits)) if commits else -1.0,
        total=len(commits),
        passed=passed,
        pattern=commit_pattern,
        violations=tuple(violations[:20]),
    )

    # -- anti-patterns --------------------------------------
    warnings: list[Warning] = []
    top_share = author_stats[0].share if author_stats else 0.0
    top_name = author_stats[0].name if author_stats else "—"

    if top_share >= 0.7:
        warnings.append(Warning(
            rule="authors",
            severity="high",
            message=f"{top_name} accounts for {top_share:.0%} of commits",
            target=top_name,
            condition="commits ≥ 70%",
            actual=f"{top_share:.0%}（{author_stats[0].commits}  times",
            threshold="70%",
            action="Spread ownership across the team and review pull requests",
        ))
    if len(stale) >= 3:
        warnings.append(Warning(
            rule="files",
            severity="medium",
            message=f"{len(stale)} files {stale_days} change",
            target=stale[0].path,
            condition=f"commits ≥ {stale_days}  days",
            actual=f"{len(stale)} files {stale[0].days_since_change}  days",
            threshold=f"{stale_days}  days",
            action="remove README",
        ))
    if large:
        warnings.append(Warning(
            rule="files",
            severity="medium",
            message=f"{len(large)} files {large_file_mb}MB，repository",
            target=large[0].path,
            condition=f"files ≥ {large_file_mb}MB",
            actual=f"{len(large)} files {large[0].size_bytes / 1048576:.1f}MB）",
            threshold=f"{large_file_mb} MB",
            action="Use Git LFS for large assets and update .gitignore rules",
        ))
    if hotspots and hotspots[0].change_count >= max(hotspot_changes * 2, 20):
        warnings.append(Warning(
            rule="files",
            severity="low",
            message=f"{hotspots[0].path} change {hotspots[0].change_count} is",
            target=hotspots[0].path,
            condition=f"files ≥ {hotspot_changes}  times",
            actual=f"{hotspots[0].change_count}  times",
            threshold=f"{hotspot_changes}  times",
            action="Review frequently changed files and split responsibilities",
        ))
    if hygiene.pass_rate >= 0 and hygiene.pass_rate < 0.6:
        warnings.append(Warning(
            rule="commits",
            severity="low",
            message=f"{hygiene.pass_rate:.0%} of commits match the pattern",
            target="git log",
            condition="Commit-pattern compliance < 60%",
            actual=f"{hygiene.pass_rate:.0%}（{hygiene.passed}/{hygiene.total}）",
            threshold="60%",
            action="Add a commit-msg hook and document the convention",
        ))

    # -- health --------------------------------------------------------
    penalty = {"high": 12, "medium": 6, "low": 3}
    health = 100.0
    for warning in warnings:
        health -= penalty.get(warning.severity, 3)
    health = round(max(0.0, min(100.0, health)), 1)

    risk_counts = {level: sum(1 for warning in warnings if warning.severity == level)
                   for level in ("high", "medium", "low")}
    recent_commits = {}
    last_date = max(calendar) if calendar else ""
    if last_date:
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        for days in (7, 30, 90):
            start = last_dt - timedelta(days=days - 1)
            recent_commits[days] = sum(value for day, value in calendar.items()
                                       if start.strftime("%Y-%m-%d") <= day <= last_date)
    warning_counts = Counter(warning.target for warning in warnings)
    dimensions = (
        HealthDimension("Git activity", min(100.0, len(calendar) / 90 * 100), "low" if len(calendar) >= 30 else "medium", 0, f"{len(calendar)} active days"),
        HealthDimension("Ownership balance", max(0.0, 100 - warning_counts.get(top_name, 0) * 20), "high" if top_share >= 0.8 else ("medium" if top_share >= 0.7 else "low"), int(top_share >= 0.7), f"Top author: {top_share:.0%}"),
        HealthDimension("Code quality", 100.0, "low", 0, "No issues"),
        HealthDimension("Dependencies", 100.0, "low", 0, "No issues"),
        HealthDimension("commits", hygiene.pass_rate * 100 if hygiene.pass_rate >= 0 else 0, "low" if hygiene.pass_rate >= .8 else "medium", hygiene.total - hygiene.passed, f"passed {hygiene.pass_rate:.0%}"),
    )
    return MockView(
        snapshot=snapshot,
        health_score=health,
        total_commits=len(commits),
        author_count=len(per_author),
        file_count=len(files),
        commit_calendar=dict(calendar),
        author_stats=author_stats,
        hotspot_files=hotspots,
        large_files=large,
        stale_files=stale,
        warnings=warnings,
        commit_hygiene=hygiene,
        risk_level=risk_of(health),
        dashboard_stats=DashboardStats(dimensions=dimensions, risk_counts=risk_counts, recent_commits=recent_commits),
    )


# --------------------------------------------------------------------------
# repository GUI Notes
# --------------------------------------------------------------------------
def _synthetic_snapshot(repo_path: str = "demo/repo") -> RepositorySnapshot:
    random.seed(20261124)
    authors = [("Chen Wei", "chen@example.com"), ("Lin Tao", "lin@example.com"),
               ("Wang Yu", "wang@example.com"), ("Huang Jionghua", "hjh@example.com")]
    paths = ["models.py", "git_reader.py", "metrics.py", "rules.py", "gui/main_window.py",
             "gui/dashboard.py", "gui/trends.py", "reporters.py", "cli.py", "README.md",
             "docs/design.md", "assets/logo.png"]

    today = datetime.now()
    commits: list[Commit] = []
    # Notes"Notes"：repository
    # Notes"authors"Notes high repository
    weights = [10, 2, 1, 1]
    for index in range(160):
        name, email = random.choices(authors, weights=weights, k=1)[0]
        when = today - timedelta(days=random.randint(0, 170), hours=random.randint(0, 20))
        touched = tuple(random.sample(paths, k=random.randint(1, 4)))
        commits.append(Commit(
            hash=f"{index:040x}",
            author_name=name,
            author_email=email,
            authored_at=when,
            message=random.choice(["feat: add dashboard", "fix: handle empty repo",
                                   "docs: update readme", "wip", "refactor parser"]),
            files_changed=touched,
            insertions=random.randint(5, 220),
            deletions=random.randint(0, 90),
        ))
    commits.sort(key=lambda c: c.authored_at)

    files = tuple(
        FileRecord(
            path=path,
            size_bytes=random.randint(2_000, 18_000_000),
            file_type=path.rsplit(".", 1)[-1],
            modified_at=today - timedelta(days=random.randint(0, 260)),
        )
        for path in paths
    )
    return RepositorySnapshot(
        repo_path=repo_path,
        repo_name="demo-repo",
        commits=tuple(commits),
        files=files,
        branches=("main", "feature/gui"),
        tags=("v0.1.0",),
        scanned_at=today,
    )




