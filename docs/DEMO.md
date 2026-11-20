# RepoScope demonstration guide

This guide shows the supported entry points and the screens available in the desktop interface.

## Entry points

| Scenario | Command |
|---|---|
| Analyze a real repository | `python main.py analyze PATH` |
| Open the GUI | `python main.py` |
| Open the GUI with sample data | `python main.py --demo` |
| Check repository metadata | `python main.py check PATH` |
| Export all report formats | `python main.py export PATH --format all` |

The GUI uses the same analysis service and configuration model as the CLI. The sidebar provides access to the dashboard, commit trends, author contributions, data analysis, anti-patterns, reports, and repository comparison.

## Demo data

`--demo` loads a deterministic sample workspace so the interface can be reviewed without a Git checkout. It includes commit activity, author statistics, file hotspots, health dimensions, and anti-pattern warnings.

## Screenshots

Run `python tools/screenshot.py` to capture each page under `docs/screens/`. The script uses the offscreen Qt platform and can run in CI.
