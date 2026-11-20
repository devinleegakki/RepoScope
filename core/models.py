"""Data models shared by RepoScope's Git reader and analysis layers.

The models in this module deliberately contain no Git or GUI behaviour.  They
are the stable boundary between repository inspection and the rest of the
application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Metadata for one file in a repository working tree."""

    path: str
    size_bytes: int
    file_type: str
    modified_at: Optional[datetime] = None
    is_tracked: bool = True

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("file path cannot be empty")
        if self.size_bytes < 0:
            raise ValueError("file size cannot be negative")

    @property
    def name(self) -> str:
        """Return the final path component without touching the filesystem."""

        return Path(self.path).name


@dataclass(frozen=True, slots=True)
class Commit:
    """A normalized Git commit and its file-level change summary."""

    hash: str
    author_name: str
    author_email: str
    authored_at: datetime
    message: str
    files_changed: Tuple[str, ...] = field(default_factory=tuple)
    insertions: int = 0
    deletions: int = 0
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.hash:
            raise ValueError("commit hash cannot be empty")
        if self.insertions < 0 or self.deletions < 0:
            raise ValueError("commit line counts cannot be negative")


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """All raw repository data needed by RepoScope analysis."""

    repo_path: str
    repo_name: str
    commits: Tuple[Commit, ...] = field(default_factory=tuple)
    files: Tuple[FileRecord, ...] = field(default_factory=tuple)
    branches: Tuple[str, ...] = field(default_factory=tuple)
    tags: Tuple[str, ...] = field(default_factory=tuple)
    scanned_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.repo_path:
            raise ValueError("repository path cannot be empty")
        if not self.repo_name:
            raise ValueError("repository name cannot be empty")


@dataclass(frozen=True, slots=True)
class GitReaderErrorInfo:
    """Machine-readable details attached to a :class:`GitReaderError`."""

    code: str
    message: str
    command: Tuple[str, ...] = field(default_factory=tuple)
    details: Optional[str] = None
