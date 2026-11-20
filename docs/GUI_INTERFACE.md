# RepoScope GUI interface

The GUI is built with PySide6 and uses the same analysis service as the CLI. `main.py` is the only application entry point.

## Navigation

The sidebar is grouped into Setup, Results, and Batch sections. Each item has an icon and a text label. The menu button collapses the sidebar to an icon rail and expands it again.

- **Repository** selects a local Git repository.
- **Analysis settings** controls thresholds and optional scans.
- **Dashboard** shows health, activity, and risk summaries.
- **Commit trends**, **Author contributions**, **Data analysis**, and **Anti-pattern center** provide detailed views.
- **Reports** previews and exports Markdown, HTML, and CSV files.
- **Repository comparison** analyzes several repositories in one run.

## Shared analysis models

`gui.contract` contains the view models consumed by pages. The models keep stable field names so CLI, reports, and GUI output remain compatible.

### `Warning`

Warnings describe a detected anti-pattern and include evidence fields:

| Field | Type | Meaning |
|---|---|---|
| `condition` | `str` | Rule condition, for example `commits >= 70%`. |
| `actual` | `str` | Observed value. |
| `threshold` | `str` | Configured threshold. |
| `action` | `str` | Suggested remediation. |
| `target` | `str` | File, commit, or repository target. |

Missing evidence is displayed as `Pending`; it is never represented by a placeholder field named `text`.

### `FileStat`

File statistics include `path`, `change_count`, `changed_lines`, `size_bytes`, `days_since_change`, `file_type`, and `is_binary`.

### `AuthorStat`

Author statistics include commit count, insertions, deletions, overall share, and the recent 90-day share when enough history is available.

## Running the application

```text
python main.py
python main.py --demo
python main.py analyze PATH --format all --output reports
```

Use `QT_QPA_PLATFORM=offscreen` for smoke tests and screenshot generation.
