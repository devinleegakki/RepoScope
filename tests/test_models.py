from datetime import datetime, timezone

import pytest

from models import Commit, FileRecord, RepositorySnapshot


def test_models_are_immutable_and_keep_nested_values() -> None:
    timestamp = datetime.now(timezone.utc)
    commit = Commit(
        hash="abc123",
        author_name="LTY",
        author_email="lty@example.com",
        authored_at=timestamp,
        message="feat: add reader",
        files_changed=("models.py",),
        insertions=3,
        deletions=1,
        tags=("v1.0.0",),
    )
    record = FileRecord("models.py", 100, ".py", timestamp)
    snapshot = RepositorySnapshot(
        repo_path="/tmp/repo",
        repo_name="repo",
        commits=(commit,),
        files=(record,),
        branches=("main",),
        tags=("v1.0.0",),
        scanned_at=timestamp,
    )

    assert snapshot.commits[0].files_changed == ("models.py",)
    assert record.name == "models.py"
    with pytest.raises((AttributeError, TypeError)):
        snapshot.repo_name = "changed"


@pytest.mark.parametrize(
    ("factory", "kwargs"),
    [
        (FileRecord, {"path": "", "size_bytes": 0, "file_type": ""}),
        (FileRecord, {"path": "a", "size_bytes": -1, "file_type": ""}),
        (
            Commit,
            {
                "hash": "",
                "author_name": "a",
                "author_email": "e",
                "authored_at": datetime.now(timezone.utc),
                "message": "m",
            },
        ),
        (
            RepositorySnapshot,
            {"repo_path": "", "repo_name": "repo"},
        ),
    ],
)
def test_models_reject_invalid_values(factory, kwargs) -> None:
    with pytest.raises(ValueError):
        factory(**kwargs)
