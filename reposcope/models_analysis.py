"""Data models for RepoScope's analysis layer (metrics + anti-pattern rules).

Owner: TYB  (task 2 - statistical metrics & anti-pattern detection)
Course: INT6181 Applied Programming with Python

Design notes
------------
* This module is **GUI-independent** and **Git-independent**. It only defines
  plain data containers plus small coercion helpers.
* ``AnalysisConfig`` / ``RepositoryMetrics`` / ``Warning`` are owned by task 2.
  ``RepositorySnapshot`` / ``Commit`` / ``FileRecord`` are owned by task 1
  (LTY, in ``models.py``). To keep the two modules decoupled we describe the
  snapshot side with :class:`typing.Protocol` contracts (``*Like``). Any object
  exposing those attributes works -- including LTY's real dataclasses and the
  lightweight fixtures used in tests.
* All "days since ..." computations are anchored to an explicit ``as_of``
  timestamp so results are reproducible from a fixed fixture.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Union

try:  # PyYAML is declared in requirements.txt; JSON remains a fallback.
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML installed
    yaml = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Coercion helpers                                                            #
# --------------------------------------------------------------------------- #
def as_utc_datetime(value: Union[datetime, date, str, int, float, None]) -> Optional[datetime]:
    """Normalise a Git timestamp into an aware UTC ``datetime``.

    Accepts ``datetime`` (naive or aware), ``date``, ISO-8601 strings, numeric
    Unix seconds, or ``None``. Naive datetimes are assumed to be UTC. This
    keeps date arithmetic consistent regardless of how LTY stores timestamps.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return datetime.fromtimestamp(int(text), tz=timezone.utc)
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _first_attr(obj: Any, names: Sequence[str], default: Any = None) -> Any:
    """Return the first present, non-None attribute from ``names`` (duck typing)."""
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    if isinstance(obj, Mapping):
        for name in names:
            if name in obj and obj[name] is not None:
                return obj[name]
    return default


# --------------------------------------------------------------------------- #
# Snapshot contracts (owned by task 1 / LTY, declared here for decoupling)   #
# --------------------------------------------------------------------------- #
class FileChangeLike(Protocol):
    """A single file modification inside a commit."""

    path: str
    insertions: int
    deletions: int


class CommitLike(Protocol):
    """A commit produced by LTY's Git data layer."""

    sha: str
    author: str
    timestamp: Union[datetime, date, str, int, float]
    message: str
    files_changed: Sequence[FileChangeLike]
    insertions: int
    deletions: int


class FileRecordLike(Protocol):
    """A file in the working tree together with its last-commit metadata."""

    path: str
    size_bytes: int
    file_type: str
    last_commit_date: Union[datetime, date, str, int, float, None]


class TagLike(Protocol):
    """A release tag with its creation/commit date."""

    name: str
    date: Union[datetime, date, str, int, float, None]


class RepositorySnapshotLike(Protocol):
    """Unified snapshot consumed by metrics.py (interface contract for LTY)."""

    repo_name: str
    commits: Sequence[CommitLike]
    files: Sequence[FileRecordLike]
    tags: Sequence[TagLike]


# --------------------------------------------------------------------------- #
# Configuration                                                               #
# --------------------------------------------------------------------------- #
@dataclass
class AnalysisConfig:
    """Thresholds and options that drive metrics and anti-pattern rules.

    Defaults match the course proposal (section 2.4 / 3.2). Values can be
    overridden from YAML or JSON so that "changing the config changes the
    result" is directly testable.
    """

    # Observation windows (days)
    observation_days: int = 90
    recent_days: int = 90
    trend_bucket: str = "day"  # one of: day | week | month

    # Thresholds from the proposal
    stale_days: int = 180
    large_file_mb: float = 10.0
    single_maintainer_ratio: float = 0.70
    release_stale_days: int = 365
    hotspot_changes: int = 10
    commit_message_pattern: str = r"^(feat|fix|docs|refactor)(\(.+\))?:"
    min_message_length: int = 5

    # Classification helpers
    binary_extensions: List[str] = field(
        default_factory=lambda: [
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip",
            ".tar", ".gz", ".7z", ".exe", ".dll", ".so", ".bin", ".pyc",
            ".class", ".jar", ".mp3", ".mp4", ".woff", ".woff2", ".ttf",
        ]
    )

    # Risk level assigned to each anti-pattern rule (high | medium | low)
    rule_levels: Dict[str, str] = field(
        default_factory=lambda: {
            "single_maintainer": "high",
            "release_stale_illusion": "medium",
            "hotspot_changes": "medium",
            "large_file": "medium",
            "stale_file": "low",
            "commit_message": "low",
        }
    )

    _compiled_pattern: Optional[re.Pattern[str]] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.trend_bucket not in {"day", "week", "month"}:
            raise ValueError("trend_bucket must be one of: day, week, month")
        if not 0.0 <= self.single_maintainer_ratio <= 1.0:
            raise ValueError("single_maintainer_ratio must be within [0, 1]")
        for key in ("observation_days", "recent_days", "stale_days",
                    "release_stale_days", "hotspot_changes", "min_message_length"):
            if getattr(self, key) < 0:
                raise ValueError(f"{key} must be non-negative")
        if self.large_file_mb < 0:
            raise ValueError("large_file_mb must be non-negative")
        # Compile once; an invalid user pattern fails fast with a clear error.
        self._compiled_pattern = re.compile(self.commit_message_pattern)

    # ---- constructors -----------------------------------------------------
    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> "AnalysisConfig":
        """Build a config from a mapping, ignoring unknown keys gracefully."""
        if not data:
            return cls()
        known = {
            "observation_days", "recent_days", "trend_bucket", "stale_days",
            "large_file_mb", "single_maintainer_ratio", "release_stale_days",
            "hotspot_changes", "commit_message_pattern", "min_message_length",
            "binary_extensions", "rule_levels",
        }
        kwargs = {k: v for k, v in data.items() if k in known}
        # Nested mappings may be loaded as dicts already; copy to avoid aliasing.
        if "binary_extensions" in kwargs:
            kwargs["binary_extensions"] = list(kwargs["binary_extensions"])
        if "rule_levels" in kwargs:
            merged = cls().rule_levels
            merged.update(dict(kwargs["rule_levels"]))
            kwargs["rule_levels"] = merged
        return cls(**kwargs)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "AnalysisConfig":
        """Load thresholds from a YAML file (or JSON, which is valid YAML)."""
        text = Path(path).read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(text) or {}
        else:  # pragma: no cover
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:  # pragma: no cover
                raise RuntimeError("PyYAML is required to load YAML configs") from exc
        if not isinstance(data, Mapping):
            raise ValueError("config root must be a mapping")
        return cls.from_dict(data)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "AnalysisConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("config root must be a JSON object")
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_days": self.observation_days,
            "recent_days": self.recent_days,
            "trend_bucket": self.trend_bucket,
            "stale_days": self.stale_days,
            "large_file_mb": self.large_file_mb,
            "single_maintainer_ratio": self.single_maintainer_ratio,
            "release_stale_days": self.release_stale_days,
            "hotspot_changes": self.hotspot_changes,
            "commit_message_pattern": self.commit_message_pattern,
            "min_message_length": self.min_message_length,
            "binary_extensions": list(self.binary_extensions),
            "rule_levels": dict(self.rule_levels),
        }

    @property
    def commit_pattern(self) -> re.Pattern[str]:
        assert self._compiled_pattern is not None
        return self._compiled_pattern


# --------------------------------------------------------------------------- #
# Metric result containers                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class AuthorContribution:
    author: str
    commits: int
    ratio: float                 # share of all commits in the observation window
    recent_commits: int = 0      # commits within ``recent_days``
    recent_ratio: float = 0.0    # share of commits within ``recent_days``

    def to_dict(self) -> Dict[str, Any]:
        return {
            "author": self.author,
            "commits": self.commits,
            "ratio": round(self.ratio, 4),
            "recent_commits": self.recent_commits,
            "recent_ratio": round(self.recent_ratio, 4),
        }


@dataclass
class FileStat:
    path: str
    changes: int = 0
    lines_changed: int = 0
    size_bytes: int = 0
    file_type: str = ""
    last_modified: Optional[datetime] = None
    stale_days: Optional[int] = None
    is_binary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "changes": self.changes,
            "lines_changed": self.lines_changed,
            "size_bytes": self.size_bytes,
            "file_type": self.file_type,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "stale_days": self.stale_days,
            "is_binary": self.is_binary,
        }


@dataclass
class CommitCompliance:
    checked: int = 0
    valid: int = 0
    pass_rate: float = 1.0
    violations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checked": self.checked,
            "valid": self.valid,
            "pass_rate": round(self.pass_rate, 4),
            "violations": list(self.violations),
        }


@dataclass
class RepositoryMetrics:
    """All metrics for one repository, derived solely from a snapshot + config."""

    repo_name: str = ""
    as_of: Optional[datetime] = None
    observation_days: int = 90
    recent_days: int = 90
    total_commits: int = 0
    total_authors: int = 0
    total_files: int = 0
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None

    commit_trend: Dict[str, int] = field(default_factory=dict)
    trend_bucket: str = "day"
    author_contributions: List[AuthorContribution] = field(default_factory=list)
    maintainer_concentration: float = 0.0     # top author's share within recent_days
    top_author: str = ""
    file_hotspots: List[FileStat] = field(default_factory=list)
    stale_files: List[FileStat] = field(default_factory=list)
    large_files: List[FileStat] = field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    commit_compliance: CommitCompliance = field(default_factory=CommitCompliance)
    days_since_last_tag: Optional[int] = None
    last_tag: str = ""

    # ---- convenience ------------------------------------------------------
    @property
    def recent_active(self) -> bool:
        """True when at least one commit occurred inside the recent window."""
        if self.last_commit_date is None or self.as_of is None:
            return False
        return (self.as_of - self.last_commit_date).days <= self.recent_days

    def to_dict(self) -> Dict[str, Any]:
        """Serialisable view shared by GUI tables and report writers."""
        return {
            "repo_name": self.repo_name,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "observation_days": self.observation_days,
            "recent_days": self.recent_days,
            "total_commits": self.total_commits,
            "total_authors": self.total_authors,
            "total_files": self.total_files,
            "first_commit_date": self.first_commit_date.isoformat() if self.first_commit_date else None,
            "last_commit_date": self.last_commit_date.isoformat() if self.last_commit_date else None,
            "commit_trend": dict(self.commit_trend),
            "trend_bucket": self.trend_bucket,
            "author_contributions": [a.to_dict() for a in self.author_contributions],
            "maintainer_concentration": round(self.maintainer_concentration, 4),
            "top_author": self.top_author,
            "file_hotspots": [f.to_dict() for f in self.file_hotspots],
            "stale_files": [f.to_dict() for f in self.stale_files],
            "large_files": [f.to_dict() for f in self.large_files],
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
            "commit_compliance": self.commit_compliance.to_dict(),
            "days_since_last_tag": self.days_since_last_tag,
            "last_tag": self.last_tag,
        }


# --------------------------------------------------------------------------- #
# Warning                                                                     #
# --------------------------------------------------------------------------- #
@dataclass
class Warning:
    """An explainable anti-pattern finding.

    Every warning carries the five fields required by the acceptance criteria:
    name, level, actual value, threshold and suggested action. ``target`` lets
    the GUI jump to the related chart/table; ``evidence`` holds affected files
    or authors.
    """

    name: str
    level: str                       # high | medium | low
    actual_value: Any
    threshold: Any
    suggestion: str
    message: str = ""
    target: str = ""                 # e.g. authors | hotspots | tags | staleness | large_files | compliance
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.level not in {"high", "medium", "low"}:
            raise ValueError("warning level must be high, medium or low")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "suggestion": self.suggestion,
            "message": self.message,
            "target": self.target,
            "evidence": dict(self.evidence),
        }
