# API Reference

## Core interfaces

- `GitReader.validate()` validates a path and raises `GitReaderError` with a machine-readable code.
- `GitReader.read_snapshot()` returns a `RepositorySnapshot`.
- `AnalysisService.check(path)` returns repository metadata without analysis.
- `AnalysisService.analyze(path, config, on_progress=...)` returns an `AnalysisView`.
- `BatchAnalyzer.run(paths, config, ...)` returns isolated `BatchResult` values.
- `reporters.render_markdown`, `render_html`, and `render_csv` render an `AnalysisView`.
- `reporters.write_report(view, formats, output_dir)` writes report files and returns `Path` values.

## Stable view fields

`AnalysisView` exposes snapshot, health score, commit calendar, author statistics, hotspot/large/stale files, warnings, commit hygiene, risk level, and dashboard statistics. `Warning` exposes `rule`, `severity`, `message`, `target`, `condition`, `actual`, `threshold`, and `action`.

These fields are shared by GUI pages, CLI summaries, and report renderers and must remain compatible when extending the analysis engine.
