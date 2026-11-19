"""Read local Git repositories into RepoScope's neutral data models."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

from models import Commit, FileRecord, GitReaderErrorInfo, RepositorySnapshot


class GitReaderError(RuntimeError):
    """A user-facing, structured failure while inspecting a Git repository."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        command: Sequence[str] = (),
        details: Optional[str] = None,
    ) -> None:
        self.info = GitReaderErrorInfo(code, message, tuple(command), details)
        super().__init__(message)

    @property
    def code(self) -> str:
        return self.info.code

    @property
    def command(self) -> tuple[str, ...]:
        return self.info.command

    @property
    def details(self) -> Optional[str]:
        return self.info.details


class GitReader:
    """Inspect one local repository using the system ``git`` executable."""

    def __init__(self, repo_path: str | Path, *, timeout: float = 30.0) -> None:
        self.repo_path = Path(repo_path).expanduser().resolve(strict=False)
        self.timeout = timeout
        self._validated = False
        self._tag_map: Optional[dict[str, tuple[str, ...]]] = None
        self._tags_cache: Optional[list[str]] = None

    def validate(self) -> Path:
        """Validate the configured path and return its Git top-level directory."""

        if not self.repo_path.exists():
            raise GitReaderError("path_not_found", f"Repository path does not exist: {self.repo_path}")
        if not self.repo_path.is_dir():
            raise GitReaderError("not_a_directory", f"Repository path is not a directory: {self.repo_path}")
        if shutil.which("git") is None:
            raise GitReaderError("git_not_installed", "Git executable was not found on PATH")

        top_level = self._run(("rev-parse", "--show-toplevel"), error_code="not_a_git_repository").strip()
        if not top_level:
            raise GitReaderError("not_a_git_repository", f"Not a Git repository: {self.repo_path}")
        resolved_top = Path(top_level).resolve(strict=False)
        if resolved_top != self.repo_path:
            raise GitReaderError(
                "repository_path_mismatch",
                f"Path must be the repository root: {self.repo_path}",
                details=f"Git root is {resolved_top}",
            )
        self._validated = True
        return resolved_top

    def read_snapshot(self, *, max_commits: Optional[int] = None) -> RepositorySnapshot:
        """Read the repository into a single immutable snapshot."""

        self.validate()
        if max_commits is not None and max_commits < 0:
            raise ValueError("max_commits cannot be negative")
        commits = self.read_commits(max_commits=max_commits)
        return RepositorySnapshot(
            repo_path=str(self.repo_path),
            repo_name=self.repo_path.name or str(self.repo_path),
            commits=tuple(commits),
            files=tuple(self.read_files()),
            branches=tuple(self.read_branches()),
            tags=tuple(self.read_tags()),
            scanned_at=datetime.now(timezone.utc),
        )

    def _run(self, args: Sequence[str], *, error_code: str = "git_command_failed") -> str:
        if shutil.which("git") is None:
            raise GitReaderError("git_not_installed", "Git executable was not found on PATH")
        command = ("git", "-C", str(self.repo_path), *args)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitReaderError(
                "git_timeout",
                f"Git command timed out after {self.timeout:g} seconds",
                command=command,
                details=str(exc),
            ) from exc
        except OSError as exc:
            raise GitReaderError(error_code, "Could not start Git command", command=command, details=str(exc)) from exc
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise GitReaderError(error_code, details or "Git command failed", command=command, details=details)
        return completed.stdout

    def read_commits(self, *, max_commits: Optional[int] = None) -> list[Commit]:
        """Return commits from all local branches, newest first.

        Commit metadata and numstat are fetched in one ``git log`` process.
        Tags are indexed once with ``for-each-ref`` instead of running a
        ``tag --points-at`` process for every commit.
        """

        self._ensure_validated()
        if max_commits == 0:
            return []
        log_args = [
                "log",
                "--all",
                "--date=iso-strict",
                "--root",
                "-M",
                "--numstat",
                "--format=%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
        ]
        if max_commits is not None:
            # Let Git stop walking history early; parsing fewer records alone
            # would still leave the expensive history traversal untouched.
            log_args.extend(("-n", str(max_commits)))
        output = self._run(
            tuple(log_args),
            error_code="commit_read_failed",
        )
        tag_map = self._read_tag_map()
        records: list[Commit] = []
        for raw in output.split("\x1e"):
            raw = raw.strip("\r\n")
            if not raw:
                continue
            lines = raw.splitlines()
            fields = lines[0].split("\x1f")
            if len(fields) != 5:
                raise GitReaderError("parse_error", "Unexpected commit record from Git", details=lines[0])
            commit_hash, author, email, timestamp, message = fields
            try:
                authored_at = datetime.fromisoformat(timestamp)
            except ValueError as exc:
                raise GitReaderError("parse_error", "Invalid commit timestamp", details=timestamp) from exc
            insertions = deletions = 0
            files: list[str] = []
            for stat_line in lines[1:]:
                parts = stat_line.split("\t", 2)
                if len(parts) != 3:
                    continue
                added, removed, path = parts
                if added.isdigit():
                    insertions += int(added)
                if removed.isdigit():
                    deletions += int(removed)
                files.append(path.replace("\\", "/"))
            records.append(
                Commit(
                    hash=commit_hash,
                    author_name=author,
                    author_email=email,
                    authored_at=authored_at,
                    message=message,
                    files_changed=tuple(files),
                    insertions=insertions,
                    deletions=deletions,
                    tags=tag_map.get(commit_hash, ()),
                )
            )
            if max_commits is not None and len(records) >= max_commits:
                break
        return records

    def _read_commit_stats(self, commit_hash: str) -> tuple[int, int, list[str]]:
        output = self._run(
            ("diff-tree", "--root", "--no-commit-id", "--numstat", "-r", "-M", commit_hash),
            error_code="commit_read_failed",
        )
        insertions = deletions = 0
        files: list[str] = []
        for line in output.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            added, removed, path = parts
            if added.isdigit():
                insertions += int(added)
            if removed.isdigit():
                deletions += int(removed)
            files.append(path.replace("\\", "/"))
        return insertions, deletions, files

    def read_files(self) -> list[FileRecord]:
        """Return files visible to Git, including non-ignored untracked files."""

        self._ensure_validated()
        tracked = set(self._paths_from_nul(self._run(("ls-files", "-c", "-z"), error_code="file_read_failed")))
        paths = self._paths_from_nul(
            self._run(("ls-files", "-c", "-o", "--exclude-standard", "-z"), error_code="file_read_failed")
        )
        records: list[FileRecord] = []
        for relative in sorted(set(paths)):
            absolute = self.repo_path / Path(relative)
            try:
                stat = absolute.stat()
            except OSError:
                continue
            if not absolute.is_file():
                continue
            suffix = absolute.suffix.lower()
            records.append(
                FileRecord(
                    path=relative,
                    size_bytes=stat.st_size,
                    file_type=suffix or "<none>",
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    is_tracked=relative in tracked,
                )
            )
        return records

    @staticmethod
    def _paths_from_nul(output: str) -> list[str]:
        return [item.replace("\\", "/") for item in output.split("\x00") if item]

    def read_branches(self) -> list[str]:
        self._ensure_validated()
        output = self._run(("for-each-ref", "--format=%(refname:short)", "refs/heads"), error_code="ref_read_failed")
        return [line.strip() for line in output.splitlines() if line.strip()]

    def read_tags(self) -> list[str]:
        self._ensure_validated()
        if self._tags_cache is not None:
            return list(self._tags_cache)
        output = self._run(("tag", "--list"), error_code="ref_read_failed")
        self._tags_cache = [line.strip() for line in output.splitlines() if line.strip()]
        return list(self._tags_cache)

    def _read_tag_map(self) -> dict[str, tuple[str, ...]]:
        """Read all tag -> commit mappings in one Git process."""
        if self._tag_map is not None:
            return self._tag_map
        output = self._run(
            ("for-each-ref", "--format=%(objectname)%00%(*objectname)%00%(refname:short)", "refs/tags"),
            error_code="ref_read_failed",
        )
        mapping: dict[str, list[str]] = {}
        names: list[str] = []
        for line in output.splitlines():
            fields = line.split("\x00", 2)
            if len(fields) != 3:
                continue
            object_hash, peeled_hash, name = fields
            names.append(name)
            for commit_hash in (peeled_hash, object_hash):
                if commit_hash and set(commit_hash) != {"0"}:
                    mapping.setdefault(commit_hash, []).append(name)
        self._tag_map = {key: tuple(value) for key, value in mapping.items()}
        if self._tags_cache is None:
            self._tags_cache = names
        return self._tag_map

    def _tags_for_commit(self, commit_hash: str) -> list[str]:
        output = self._run(("tag", "--points-at", commit_hash), error_code="ref_read_failed")
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _ensure_validated(self) -> None:
        if not self._validated:
            self.validate()


__all__ = ["GitReader", "GitReaderError"]
