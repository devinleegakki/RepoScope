# RepoScope

RepoScope is an offline desktop application for assessing the health of local Git repositories. It reads repository history and file metadata, computes engineering metrics, detects maintainability risks, and produces interactive GUI views plus Markdown, HTML, and CSV reports.

## What it provides

- **Local-first analysis**: reads a repository from disk and does not upload source code.
- **Git history inspection**: commits, authors, branches, tags, changed files, insertions, and deletions.
- **Health metrics**: activity, author concentration, file hotspots, large files, stale files, commit-message hygiene, code quality, dependencies, and security findings.
- **Explainable warnings**: each anti-pattern can include its condition, observed value, threshold, and suggested action.
- **Two interfaces**: a PySide6 desktop GUI and a command-line interface backed by the same analysis service.
- **Report export**: Markdown, HTML, and CSV output from both the CLI and the GUI report page.

## Quick start

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

Launch the GUI and select a repository from the first page:

```powershell
python main.py
```

Launch the built-in demo dataset:

```powershell
python main.py --demo
```

Open the GUI and analyze a repository immediately:

```powershell
python main.py --path <repository-path>
```

The GUI contains these pages: Repository, Analysis Settings, Dashboard, Commit Trends, Author Contributions, Data Analysis, Anti-pattern Center, Reports, and Repository Comparison.

## Command-line interface

The same `main.py` entry point supports non-interactive workflows:

```powershell
# Validate a repository without writing files
python main.py check <repository-path>
python main.py check <repository-path> --json

# Analyze and write one or more report formats
python main.py analyze <repository-path> --format markdown --output reports
python main.py analyze <repository-path> --format all --output reports

# Export all supported formats
python main.py export <repository-path> --output reports

# Analyze multiple repositories concurrently
python main.py batch <repository-path> <another-repository> --format all --output reports
```

Supported report formats are `markdown`, `html`, `csv`, and `all`. The `analyze` and `export` commands write files named like `<repository>_report.md`, `<repository>_report.html`, and `<repository>_report.csv`. Batch analysis also writes `batch_summary.md` and `batch_summary.csv`.

Configuration can be supplied with `--config <file.json>` and overridden with command-line options:

- `--stale-days`
- `--large-file-mb`
- `--hotspot-changes`
- `--release-stale-days`
- `--single-maintainer-ratio`
- `--window-days`
- `--commit-pattern`
- `--max-function-lines`
- `--max-file-lines`
- `--min-test-ratio`
- `--ownership-concentration`
- `--dependency-scan`
- `--secret-scan`

## Project structure

```text
main.py                    Unified GUI and CLI entry point
requirements.txt           Runtime dependencies
core/                      Shared models, Git reader, services, and reporters
cli/                       CLI parser and command handlers
gui/                       PySide6 window, pages, widgets, charts, and theme
reposcope/                 Metrics, rules, static analysis, and analysis models
tests/                     Application and integration tests
docs/                      Interface notes, demo runbook, and screenshots
tools/                     Development utilities, including screenshot generation
config/                    Development and CI dependency files
scripts/                   Optional Windows launchers
```

The repository root intentionally keeps `main.py`, `README.md`, and `requirements.txt` as the primary user-facing files. The application code is organized under the directories above.

## Development setup

Install development dependencies:

```powershell
python -m pip install -r config/requirements-dev.txt
```

Run the complete test suite:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q --cov=core --cov=cli --cov=gui --cov=reposcope --cov=main.py --cov-report=term-missing --cov-fail-under=60
```

Run the code quality check:

```powershell
python -m ruff check .
```

Generate screenshots for all GUI pages:

```powershell
python tools/screenshot.py
```

The screenshot utility uses Qt offscreen mode and explicitly loads a CJK-capable system font when available.

## Documentation

- [Walkthrough](docs/WALKTHROUGH.md)
- [Architecture](docs/ARCHITECTURE.md)
- [CLI guide](docs/CLI_GUIDE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Rules reference](docs/RULES_REFERENCE.md)
- [API reference](docs/API_REFERENCE.md)
- [Testing](docs/TESTING.md)
- [CI/CD](docs/CI_CD.md)
- [AI code review](docs/AI_CODE_REVIEW.md)
- [Release checklist](docs/RELEASE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Contributing](CONTRIBUTING.md)

## Continuous integration

GitHub Actions runs on Windows with Python 3.11 and 3.12. The workflow:

1. installs `config/requirements-dev.txt`;
2. checks the project with Ruff;
3. compiles the project with `python -m compileall -q .`;
4. runs pytest with `QT_QPA_PLATFORM=offscreen` and requires at least 60% coverage;
5. uploads the coverage XML report as a workflow artifact.

Pushing a tag such as `v0.1.0` runs the release workflow. After the same checks pass, it publishes a `RepoScope-v0.1.0.zip` source archive to a GitHub Release.

Pull requests also receive an advisory DeepSeek AI review when the `DEEPSEEK_API_KEY` Actions secret is configured. The workflow uses the OpenAI-compatible endpoint `https://api.deepseek.com` with model `deepseek-flash` (DeepSeek-V4.1-Flash-1017), reviews only the PR diff, and updates one non-blocking PR comment. See [AI code review](docs/AI_CODE_REVIEW.md).

## Requirements

- Python 3.11 or newer
- Git available on `PATH`
- PySide6 6.5 or newer for the GUI
- PyYAML 6.0 or newer for YAML rule configuration

## License and data handling

RepoScope performs analysis locally. It does not upload repository contents. Review the repository license and third-party dependency licenses before redistribution.



