"""Shared, deterministic fixtures for the analysis-core tests.

The snapshot objects below are lightweight stand-ins that satisfy the
``RepositorySnapshotLike`` protocol. They deliberately mimic the shape LTY's
``models.py`` will expose so the tests stay valid after integration.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import pytest

# Allow running pytest from either the repo root or the package directory.
PACKAGE_PARENT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for import_root in (PROJECT_ROOT, PACKAGE_PARENT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


# ---- stand-in data classes (mirror LTY's models.py shape) -----------------
@dataclass
class Change:
    path: str
    insertions: int = 0
    deletions: int = 0


@dataclass
class Commit:
    sha: str
    author: str
    timestamp: datetime
    message: str
    files_changed: List[Change] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class FileRecord:
    path: str
    size_bytes: int = 0
    file_type: str = ""
    last_commit_date: Optional[datetime] = None


@dataclass
class Tag:
    name: str
    date: Optional[datetime] = None


@dataclass
class Snapshot:
    repo_name: str = "fixture-repo"
    commits: List[Commit] = field(default_factory=list)
    files: List[FileRecord] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=list)


# A fixed anchor so every "days since" value is reproducible.
AS_OF = datetime(2026, 11, 24, 0, 0, tzinfo=timezone.utc)


def _ts(days_ago: int) -> datetime:
    return AS_OF - timedelta(days=days_ago)


@pytest.fixture
def as_of() -> datetime:
    return AS_OF


@pytest.fixture
def config():
    from reposcope.models_analysis import AnalysisConfig
    return AnalysisConfig()


@pytest.fixture
def base_snapshot() -> Snapshot:
    """A deterministic repository hitting every rule's trigger condition."""
    commits = [
        # 3 commits in the last 90 days: 2 by alice, 1 by bob -> alice 66% ...
        Commit("c1", "alice", _ts(5), "feat: add parser", [Change("core.py", 40, 10)], 40, 10),
        Commit("c2", "alice", _ts(15), "fix: parser bug", [Change("core.py", 5, 3)], 5, 3),
        # a bad commit message -> triggers commit-message rule
        Commit("c3", "bob", _ts(30), "bad message", [Change("core.py", 2, 1)], 2, 1),
        # old commit, outside the recent window
        Commit("c4", "alice", _ts(400), "docs: init", [Change("old.py", 1, 0)], 1, 0),
    ]
    # core.py modified 3 times -> with a low hotspot_changes threshold it triggers.
    files = [
        FileRecord("core.py", 2 * 1024 * 1024, ".py", _ts(15)),
        FileRecord("zombie.py", 64 * 1024, ".py", _ts(500)),   # stale
        FileRecord("blob.bin", 25 * 1024 * 1024, ".bin", _ts(20)),  # large + binary
        FileRecord("old.py", 1 * 1024, ".py", _ts(400)),
    ]
    tags = [Tag("v0.1", _ts(500))]  # last tag 500 days ago -> release stale
    return Snapshot("fixture-repo", commits, files, tags)




