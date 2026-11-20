# RepoScope Walkthrough

## GUI workflow

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Launch `python main.py`, or use `python main.py --demo` for deterministic sample data.
3. On **Repository**, browse to a local Git checkout. The path must contain `.git`.
4. On **Analysis settings**, choose the observation window, thresholds, and optional dependency/secret scans.
5. Click **Analyze**. Work runs in a worker thread while progress is reported in the status bar.
6. Review **Dashboard**, **Commit trends**, **Author contributions**, **Data analysis**, and **Anti-pattern center**.
7. Open **Reports**, choose Markdown, HTML, or CSV, choose an output folder, and confirm the generated files.
8. Use **Repository comparison** to queue several repositories and compare health scores.

## CLI workflow

```text
python main.py check PATH --json
python main.py analyze PATH --format all --output reports
python main.py export PATH --output reports
python main.py batch PATH_A PATH_B --format all --output reports
```

The GUI and CLI use the same `AnalysisService`, so findings and report values are consistent.

## Demo and screenshots

`--demo` uses synthetic data and does not require a Git checkout. Run `python tools/screenshot.py` with Qt offscreen mode to refresh screenshots under `docs/screens/`.
