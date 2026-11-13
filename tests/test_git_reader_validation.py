from pathlib import Path

import pytest

from git_reader import GitReader, GitReaderError


def test_missing_path_has_machine_readable_error(tmp_path: Path) -> None:
    error_path = tmp_path / "missing"
    with pytest.raises(GitReaderError) as exc_info:
        GitReader(error_path).validate()

    assert exc_info.value.code == "path_not_found"
    assert str(error_path) in str(exc_info.value)


def test_file_path_is_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(GitReaderError) as exc_info:
        GitReader(file_path).validate()

    assert exc_info.value.code == "not_a_directory"


def test_non_git_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(GitReaderError) as exc_info:
        GitReader(tmp_path).validate()

    assert exc_info.value.code == "not_a_git_repository"
