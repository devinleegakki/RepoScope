# RepoScope

RepoScope is a local-first Git repository health analyzer. It reads a local
repository and turns its commit history and file metadata into structured data
for later metrics, visualizations, and reports.

This branch contains the Git data layer. It is independent from the GUI, CLI,
and analysis layers so those components can consume one stable set of models.

## Current features

- Validate a repository path and report actionable errors.
- Read commits from all local branches, newest first.
- Capture commit author, email, timestamp, subject, changed files, insertions,
  deletions, and tags pointing at each commit.
- Scan tracked files and non-ignored untracked files.
- Capture relative POSIX paths, file sizes, file extensions, modification times,
  and tracking status.
- Read local branch and tag names.
- Return immutable `RepositorySnapshot`, `Commit`, and `FileRecord` objects.
- Use structured `GitReaderError` codes for path, Git, command, timeout, and
  parsing failures.

## Requirements

- Python 3.10 or newer
- Git installed and available on `PATH`
- `pytest` for running the test suite

The reader uses `subprocess` and the system Git executable. No GitPython or
remote GitHub/GitLab API is required.

## Quick start

From the repository root:

```powershell
python -m pip install pytest
python -m pytest -q
```

Read a repository from Python:

```python
from git_reader import GitReader, GitReaderError

try:
    snapshot = GitReader(r"C:\path\to\repository").read_snapshot()
except GitReaderError as error:
    print(f"[{error.code}] {error}")
else:
    print(snapshot.repo_name)
    print(f"commits: {len(snapshot.commits)}")
    print(f"files: {len(snapshot.files)}")
```

To limit history reads, pass `max_commits`:

```python
recent = GitReader(".").read_snapshot(max_commits=20)
```

## Data model

`RepositorySnapshot` is the main hand-off object for analysis and UI code. It
contains commits, files, local branches, tags, the repository path and name,
and a UTC scan timestamp. All model objects are frozen dataclasses. Paths are
relative to the repository root and use `/` separators, including on Windows.

## Error handling

Catch `GitReaderError` at application boundaries. Its `code` property can be
used for UI or CLI behavior, while `details` and `command` provide diagnostics.
Common codes include `path_not_found`, `not_a_directory`,
`not_a_git_repository`, `git_not_installed`, `git_timeout`,
`commit_read_failed`, `file_read_failed`, `ref_read_failed`, and `parse_error`.

## Project layout

```text
models.py                         Shared immutable data models
git_reader.py                     Local Git reader and error handling
tests/test_models.py              Model validation tests
tests/test_git_reader.py          Temporary-repository integration tests
tests/test_git_reader_validation.py  Path and repository validation tests
```

## Scope

The Git data layer only reads local Git data. Metrics, anti-pattern rules,
PySide6/PyQtGraph screens, report exporters, and remote hosting APIs belong to
the other RepoScope layers.
