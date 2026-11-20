# CLI Guide

All commands use `python main.py`.

| Command | Purpose |
|---|---|
| `check PATH` | Validate a repository and print metadata. |
| `analyze PATH` | Analyze and write the selected report format. |
| `export PATH` | Analyze and export all formats by default. |
| `batch PATH...` | Analyze multiple repositories concurrently. |

Common options include `--config FILE`, `--format markdown|md|html|csv|all`, and `--output DIR`.
Configuration overrides include `--stale-days`, `--large-file-mb`, `--hotspot-changes`, `--release-stale-days`, `--single-maintainer-ratio`, `--window-days`, and `--commit-pattern`.

Exit codes are `0` for success, `1` for validation or analysis failure, and `130` for interruption. Batch mode isolates failures and writes `batch_summary.md` and `batch_summary.csv`.
