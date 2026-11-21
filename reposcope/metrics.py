"""Statistical metrics computed from a unified :class:`RepositorySnapshot`.

Owner: TYB  (task 2 - statistical metrics & anti-pattern detection)
Course: INT6181 Applied Programming with Python

This module is deliberately free of GUI and Git concerns: it consumes the
snapshot produced by task 1 (LTY) and returns a :class:`RepositoryMetrics`.
Every time-dependent value is anchored to ``as_of`` so a fixed fixture yields
identical results across runs.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

try:  # works both as ``reposcope.metrics`` and as a top-level ``metrics``
    from .models_analysis import (
        AnalysisConfig,
        AuthorContribution,
        CommitCompliance,
        FileStat,
        RepositoryMetrics,
        RepositorySnapshotLike,
        _first_attr,
        as_utc_datetime,
    )
except ImportError:  # pragma: no cover - fallback when loaded without package context
    from reposcope.models_analysis import (  # type: ignore[no-redef]
        AnalysisConfig,
        AuthorContribution,
        CommitCompliance,
        FileStat,
        RepositoryMetrics,
        RepositorySnapshotLike,
        _first_attr,
        as_utc_datetime,
    )


# --------------------------------------------------------------------------- #
# Small extraction helpers (tolerant to LTY's exact field names)              #
# --------------------------------------------------------------------------- #
def _author_name(commit: Any) -> str:
    """Return a display name for a commit author.

    Supports LTY's real ``Commit`` (``author_name`` / ``author_email``), a
    nested author object (``.name``), and plain-string fixtures.
    """
    # Real models.py stores author_name as a flat string.
    flat = _first_attr(commit, ("author_name",), None)
    if flat:
        return str(flat)
    author = _first_attr(commit, ("author", "committer"), "")
    if author is None:
        return ""
    name = _first_attr(author, ("name", "display_name"), None)
    if name:
        return str(name)
    email = _first_attr(author, ("email", "author_email"), None)
    if email:
        return str(email)
    return str(author)


def _commit_time(commit: Any) -> Optional[datetime]:
    # Real models.py uses ``authored_at``.
    return as_utc_datetime(
        _first_attr(
            commit,
            ("authored_at", "timestamp", "committed_date", "date", "datetime", "time"),
            None,
        )
    )


def _commit_message(commit: Any) -> str:
    return str(_first_attr(commit, ("message", "msg", "subject"), "") or "")


def _file_change_entries(commit: Any) -> List[Tuple[str, int, int]]:
    """Yield (path, insertions, deletions) for each file touched by a commit.

    Two shapes are supported:
    * LTY's real ``Commit.files_changed``: a tuple of path **strings**, whose
      line counts live on the commit as a whole (so per-file ins/del are 0).
    * Rich fixtures: objects carrying ``path`` / ``insertions`` / ``deletions``.
    """
    changes = _first_attr(commit, ("files_changed", "file_changes", "changed_files", "files"), []) or []
    out: List[Tuple[str, int, int]] = []
    for change in changes:
        if isinstance(change, str):
            path = change
            ins = dele = 0
        else:
            path = str(_first_attr(change, ("path", "filename", "name", "file"), "") or "")
            ins = int(_first_attr(change, ("insertions", "added", "lines_added"), 0) or 0)
            dele = int(_first_attr(change, ("deletions", "removed", "lines_removed"), 0) or 0)
        if not path:
            continue
        out.append((path, ins, dele))
    return out


def _commit_line_totals(commit: Any) -> Tuple[int, int]:
    ins = int(_first_attr(commit, ("insertions", "additions", "lines_added"), 0) or 0)
    dele = int(_first_attr(commit, ("deletions", "removals", "lines_removed"), 0) or 0)
    if ins == 0 and dele == 0:
        # Fall back to summing per-file changes when the commit has no totals.
        for _, f_ins, f_dele in _file_change_entries(commit):
            ins += f_ins
            dele += f_dele
    return ins, dele


def _bucket_key(dt: datetime, bucket: str) -> str:
    if bucket == "day":
        return dt.strftime("%Y-%m-%d")
    if bucket == "month":
        return dt.strftime("%Y-%m")
    # ISO week, e.g. 2026-W47
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _is_binary(path: str, file_type: str, config: AnalysisConfig) -> bool:
    lowered = path.lower()
    ftype = (file_type or "").lower().lstrip(".")
    if ftype in {ext.lstrip(".").lower() for ext in config.binary_extensions}:
        return True
    for ext in config.binary_extensions:
        if lowered.endswith(ext.lower()):
            return True
    return False


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #
def compute_metrics(
    snapshot: RepositorySnapshotLike,
    config: Optional[AnalysisConfig] = None,
    as_of: Optional[datetime] = None,
) -> RepositoryMetrics:
    """Derive all metrics for one repository.

    Parameters
    ----------
    snapshot:
        Unified repository snapshot (task 1's ``RepositorySnapshot``).
    config:
        Thresholds / options; defaults are used when omitted.
    as_of:
        Reference "now". Defaults to current UTC time. Pass an explicit value
        in tests to make every ``*_days`` metric reproducible.
    """
    cfg = config or AnalysisConfig()
    anchor = as_utc_datetime(as_of) or datetime.now(timezone.utc)

    commits = list(_first_attr(snapshot, ("commits",), []) or [])
    files = list(_first_attr(snapshot, ("files",), []) or [])
    tags = list(_first_attr(snapshot, ("tags",), []) or [])
    repo_name = str(_first_attr(snapshot, ("repo_name", "name", "path"), "") or "")

    metrics = RepositoryMetrics(
        repo_name=repo_name,
        as_of=anchor,
        observation_days=cfg.observation_days,
        recent_days=cfg.recent_days,
        trend_bucket=cfg.trend_bucket,
        total_commits=len(commits),
        total_files=len(files),
    )

    observation_start = anchor - timedelta(days=cfg.observation_days)
    recent_start = anchor - timedelta(days=cfg.recent_days)

    # ---- collections keyed by commit -------------------------------------
    authors_all: Dict[str, int] = defaultdict(int)
    authors_window: Dict[str, int] = defaultdict(int)
    authors_recent: Dict[str, int] = defaultdict(int)
    author_commits_recent: Dict[str, int] = defaultdict(int)

    trend: Dict[str, int] = defaultdict(int)
    file_changes: Dict[str, int] = defaultdict(int)
    file_lines: Dict[str, int] = defaultdict(int)

    total_ins = 0
    total_del = 0
    compliance_checked = 0
    compliance_valid = 0
    violations: List[Dict[str, Any]] = []

    dated: List[datetime] = []
    # LTY's real Commit carries ``tags`` (tuple of names) but no tag date.
    # We infer each tag's date from the commit it points at.
    tagged_commits: List[Tuple[datetime, str]] = []

    for commit in commits:
        author = _author_name(commit) or "(unknown)"
        ctime = _commit_time(commit)
        authors_all[author] += 1

        commit_tags = _first_attr(commit, ("tags",), ()) or ()
        if ctime is not None:
            for ctag in commit_tags:
                ctag_name = ctag if isinstance(ctag, str) else str(
                    _first_attr(ctag, ("name", "tag"), "") or ""
                )
                if ctag_name:
                    tagged_commits.append((ctime, ctag_name))

        ins, dele = _commit_line_totals(commit)
        total_ins += ins
        total_del += dele

        # Commit-message compliance applies to the whole history.
        message = _commit_message(commit)
        stripped = message.strip()
        compliance_checked += 1
        reasons: List[str] = []
        if not stripped:
            reasons.append("empty message")
        elif len(stripped) < cfg.min_message_length:
            reasons.append(f"shorter than {cfg.min_message_length} chars")
        if stripped and not cfg.commit_pattern.match(stripped):
            reasons.append("does not match configured pattern")
        if reasons:
            violations.append({
                "sha": str(_first_attr(commit, ("sha", "hash", "hexsha"), "") or ""),
                "author": author,
                "message": message,
                "reasons": reasons,
            })
        else:
            compliance_valid += 1

        for path, f_ins, f_dele in _file_change_entries(commit):
            file_changes[path] += 1
            file_lines[path] += f_ins + f_dele

        if ctime is None:
            continue
        dated.append(ctime)
        metrics.first_commit_date = (
            ctime if metrics.first_commit_date is None else min(metrics.first_commit_date, ctime)
        )
        metrics.last_commit_date = (
            ctime if metrics.last_commit_date is None else max(metrics.last_commit_date, ctime)
        )

        if observation_start <= ctime <= anchor:
            authors_window[author] += 1
            trend[_bucket_key(ctime, cfg.trend_bucket)] += 1
        if recent_start <= ctime <= anchor:
            authors_recent[author] += 1
            author_commits_recent[author] += 1

    # ---- commit trend (chronological, observation window only) ------------
    metrics.commit_trend = {k: trend[k] for k in sorted(trend)}
    metrics.total_insertions = total_ins
    metrics.total_deletions = total_del
    metrics.total_authors = len(authors_all)

    # ---- author contributions & concentration ----------------------------
    window_total = sum(authors_window.values())
    recent_total = sum(authors_recent.values())
    for author, count in sorted(authors_window.items(), key=lambda kv: (-kv[1], kv[0])):
        rc = authors_recent.get(author, 0)
        metrics.author_contributions.append(AuthorContribution(
            author=author,
            commits=count,
            ratio=count / window_total if window_total else 0.0,
            recent_commits=rc,
            recent_ratio=rc / recent_total if recent_total else 0.0,
        ))
    if recent_total:
        top_author, top_count = max(authors_recent.items(), key=lambda kv: (kv[1], kv[0]))
        metrics.top_author = top_author
        metrics.maintainer_concentration = top_count / recent_total

    # ---- file hotspots / stale / large ----------------------------------
    for record in files:
        path = str(_first_attr(record, ("path", "filename", "name", "file"), "") or "")
        if not path:
            continue
        size_bytes = int(_first_attr(record, ("size_bytes", "size"), 0) or 0)
        file_type = str(_first_attr(record, ("file_type", "extension", "ext"), "") or "")
        last_dt = as_utc_datetime(
            _first_attr(
                record,
                ("modified_at", "last_commit_date", "last_modified", "mtime", "modified"),
                None,
            )
        )
        stale_days = (anchor - last_dt).days if last_dt else None
        stat = FileStat(
            path=path,
            changes=file_changes.get(path, 0),
            lines_changed=file_lines.get(path, 0),
            size_bytes=size_bytes,
            file_type=file_type,
            last_modified=last_dt,
            stale_days=stale_days,
            is_binary=_is_binary(path, file_type, cfg),
        )
        if stat.changes:
            metrics.file_hotspots.append(stat)
        if stale_days is not None and stale_days > cfg.stale_days:
            metrics.stale_files.append(stat)
        if (size_bytes > cfg.large_file_mb * 1024 * 1024) or stat.is_binary:
            metrics.large_files.append(stat)

    metrics.file_hotspots.sort(key=lambda f: (-f.changes, f.path))
    metrics.stale_files.sort(key=lambda f: (-(f.stale_days or 0), f.path))
    metrics.large_files.sort(key=lambda f: (-f.size_bytes, f.path))

    # ---- latest tag ------------------------------------------------------
    # Preference order:
    #   1. tag objects carrying an explicit date (rich fixtures / future LTY);
    #   2. tag names on commits, dated by the commit they point at (real models.py).
    tag_dates: List[Tuple[datetime, str]] = []
    for tag in tags:
        if isinstance(tag, str):
            continue  # a bare name without a date; handled via tagged_commits
        tname = str(_first_attr(tag, ("name", "tag"), "") or "")
        tdate = as_utc_datetime(_first_attr(tag, ("date", "timestamp", "commit_date"), None))
        if tdate is not None:
            tag_dates.append((tdate, tname))
    if not tag_dates:
        tag_dates = tagged_commits
    if tag_dates:
        tdate, tname = max(tag_dates, key=lambda item: item[0])
        metrics.last_tag = tname
        metrics.days_since_last_tag = max(0, (anchor - tdate).days)

    # ---- compliance summary ---------------------------------------------
    metrics.commit_compliance = CommitCompliance(
        checked=compliance_checked,
        valid=compliance_valid,
        pass_rate=compliance_valid / compliance_checked if compliance_checked else 1.0,
        violations=violations,
    )
    try:
        from .static_analysis import run_static_analysis
    except ImportError:  # top-level import used by legacy test harness
        from static_analysis import run_static_analysis  # type: ignore
    (metrics.code_quality, metrics.ownership,
     metrics.dependencies, metrics.security_findings) = run_static_analysis(snapshot, cfg)
    return metrics




