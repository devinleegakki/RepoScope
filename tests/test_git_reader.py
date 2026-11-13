import subprocess
from pathlib import Path

import pytest

from git_reader import GitReader


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(repo), *args),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "demo repo"
    repo.mkdir()
    run_git(repo, "init", "-b", "main")
    run_git(repo, "config", "user.name", "Test Author")
    run_git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("first\n", encoding="utf-8")
    (repo / "中文 文件.txt").write_text("one\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "feat: initial files")
    run_git(repo, "tag", "v1.0.0")
    (repo / "README.md").write_text("first\nsecond\n", encoding="utf-8")
    (repo / "new file.py").write_text("print('ok')\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", "fix: update files")
    (repo / "untracked.data").write_text("ignored by no rule\n", encoding="utf-8")
    return repo


def test_read_commits_parses_history_and_stats(git_repo: Path) -> None:
    commits = GitReader(git_repo).read_commits()

    assert len(commits) == 2
    assert commits[0].message == "fix: update files"
    assert commits[0].author_name == "Test Author"
    assert commits[0].insertions >= 1
    assert "README.md" in commits[0].files_changed
    assert commits[1].tags == ("v1.0.0",)
    assert GitReader(git_repo).read_commits(max_commits=1)[0].message == "fix: update files"
    assert GitReader(git_repo).read_commits(max_commits=0) == []


def test_read_files_includes_tracked_and_non_ignored_untracked(git_repo: Path) -> None:
    files = GitReader(git_repo).read_files()
    by_path = {record.path: record for record in files}

    assert "README.md" in by_path
    assert "中文 文件.txt" in by_path
    assert "new file.py" in by_path
    assert by_path["README.md"].is_tracked is True
    assert by_path["untracked.data"].is_tracked is False
    assert by_path["new file.py"].file_type == ".py"
    assert by_path["untracked.data"].size_bytes > 0


def test_read_snapshot_combines_refs_and_data(git_repo: Path) -> None:
    snapshot = GitReader(git_repo).read_snapshot()

    assert snapshot.repo_name == "demo repo"
    assert snapshot.repo_path == str(git_repo.resolve())
    assert snapshot.branches == ("main",)
    assert snapshot.tags == ("v1.0.0",)
    assert len(snapshot.commits) == 2
    assert snapshot.scanned_at is not None
