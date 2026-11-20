from datetime import datetime, timezone

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from core.models import Commit, FileRecord, RepositorySnapshot


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


def sample_snapshot() -> RepositorySnapshot:
    timestamp = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    return RepositorySnapshot(
        repo_path="C:/demo",
        repo_name="demo",
        commits=(
            Commit(
                hash="abcdef1234567890",
                author_name="Tester",
                author_email="tester@example.com",
                authored_at=timestamp,
                message="feat: demo",
                files_changed=("README.md",),
                insertions=2,
                tags=("v1.0.0",),
            ),
        ),
        files=(FileRecord("README.md", 20, ".md", timestamp),),
        branches=("main",),
        tags=("v1.0.0",),
        scanned_at=timestamp,
    )


def test_window_categories_and_snapshot_render(qapp):
    window = MainWindow()
    window._render_snapshot(sample_snapshot())

    assert window.overview_values["repo_name"].text() == "demo"
    assert window.commit_model.rowCount() == 1
    assert window.file_model.rowCount() == 1
    assert window.refs_model.rowCount() == 2

    for index in range(4):
        window.navigation.setCurrentRow(index)
        assert window.pages.currentIndex() == index

    window.close()




