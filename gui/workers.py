"""Background workers used by the RepoScope GUI."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from core.git_reader import GitReader, GitReaderError
from core.models import RepositorySnapshot


class SnapshotWorker(QObject):
    """Read one repository without blocking the Qt event loop."""

    finished = Signal(object)
    failed = Signal(object)
    progress = Signal(str)

    def __init__(self, repo_path: str, max_commits: int | None = None) -> None:
        super().__init__()
        self.repo_path = repo_path
        self.max_commits = max_commits

    @Slot()
    def run(self) -> None:
        self.progress.emit("textcheckrepository…")
        try:
            snapshot = GitReader(self.repo_path).read_snapshot(max_commits=self.max_commits)
        except GitReaderError as error:
            self.failed.emit(error)
        except Exception as error:  # GUI boundary: keep unexpected errors visible.
            self.failed.emit(error)
        else:
            self.progress.emit("Scan complete")
            self.finished.emit(snapshot)

