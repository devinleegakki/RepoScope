# GUI text

text LTY（`core/git_reader.py`）、TYB（`reposcope/metrics.py` / `reposcope/rules.py`）、Wyh（CLI / report / text）。
**text GUI text，text。**

---

## text

text `gui/contract.py` text `AnalysisView` text。**text，text；text**——text `adapt()` text，text。

```python
# text（text，text）
from gui.contract import AnalysisView
```

`gui/contract.py` text `core/models.py`，**text PySide6 text import**，text。

---

## 30 text

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pyside6 pytest
.\.venv\Scripts\python.exe main.py --demo     # text，text
```

text `scripts/run_gui.bat`（text）text `scripts/run_real.bat`（analyzetextrepository）。text、text。

text VS Code text `F5` text，`.vscode/launch.json` text。

**Windows text `python` text**：text，text `py -3.11` text，textroot directory README text。

---

## text

| text | text |
|---|---|
| text | text，text |
| textanalyze | `QThread` + `moveToThread`，text |
| text | `PySide6.QtCharts`，text PySide6 text |
| text | `pytest -q` → 31 passed（text PySide6 text，text） |
| text | `docs/screens/` text，`tools/screenshot.py` text |

**text**：`git_reader` text → `gui/mock_data.py` text（`_compute`，text `TEMP`）→ text。

text：**text、text，text，text TYB text `metrics.py`。** text。

---

## text

text：

- **TEMP** —— text，text `mock_data._compute` text，text
- **text** —— text，text，text「Not provided by backend」text 0

### 1. `AnalysisView` text

| text | text | text | text | text |
|---|---|---|---|---|
| `snapshot` | `RepositorySnapshot` | text、reporttext | LTY | ✅ text |
| `health_score` | `float` 0–100 | health scoretext、text、report | TYB | TEMP |
| `total_commits` | `int` | text / text / report | TYB | TEMP |
| `author_count` | `int` | text / text | TYB | TEMP |
| `file_count` | `int` | text / Data Analysistext | TYB | TEMP |
| `commit_calendar` | `dict[str, int]` | text + text | TYB | TEMP |
| `author_stats` | `list[AuthorStat]` | authorstext + text | TYB | TEMP |
| `hotspot_files` | `list[FileStat]` | Data Analysis · text | TYB | TEMP |
| `large_files` | `list[FileStat]` | Data Analysis · Large files | TYB | TEMP |
| `stale_files` | `list[FileStat]` | Data Analysis · text | TYB | TEMP |
| `warnings` | `list[Warning]` | Anti-pattern Center + text + reporttext 6 text | TYB | TEMP |
| `commit_hygiene` | `CommitHygiene` | text「Commit conventionpass rate」text + reporttext 7 text | TYB | TEMP |
| `risk_level` | `str` | textLeveltext | TYB | TEMP |
| `elapsed_seconds` | `float` | text「elapsed x.xs」 | text | TEMP |

### 2. `commit_calendar` —— text，text commit text

```python
commit_calendar = {"2026-11-13": 12, "2026-11-14": 5, ...}   # text → textcommit count
```

text（text/text/text，text）。text `Commit` text，text，text「text」text。

### 3. `Warning` —— Anti-pattern Centertext，text

Anti-pattern Centertext「textRulestext」。text，text。

| text | text | text | text |
|---|---|---|---|
| `condition` | `str` | `"textauthorscommitstext ≥ 70%"` | Details「Condition」 |
| `actual` | `str` | `"90%（9 text）"` | Details「Actual value」 |
| `threshold` | `str` | `"70%"` | Details「Configured threshold」 |
| `action` | `str` | `"text"` | Details「Suggested action」 |

**text `str` text**：textRulestext（`70%` / `10 MB` / `180 text`），text，text。

**text**：DetailstextNotice「text rules.py text」，reporttext「text rules.py text」。**text**——text「textthresholdtext」text。

### 4. `FileStat` text

| text | text | text |
|---|---|---|
| `changed_lines` | `int` | text「text」text（`git log --numstat` text） |
| `file_type` | `str` | Large filestext「text」text |
| `is_binary` | `bool` | Large filestext（textfilestext） |

### 5. `AuthorStat.recent_90d_share`

`float` 0–1，text 90 textcommitstextcommitstext。text：text「text」。

**text `-1.0`**（defaulttext -1），text「—」text tooltip text，text 0%。

### 6. `CommitHygiene`（text）

| text | text | text |
|---|---|---|
| `pass_rate` | `float` | 0–1；`-1` text |
| `total` / `passed` | `int` | text / text |
| `pattern` | `str` | textregex，reporttext，textpass ratetext |
| `violations` | `tuple[Violation, ...]` | `commit_hash` / `message` / `reason` |

### 7. `RepoSummary`（Repository Comparisontext）

`repo_name` / `path` / `commits` / `authors` / `health_score` / `hotspot_count` / `stale_count` / `risk_level`

---

## text（text，text）

1. **TYB**：`metrics.py` text；text，text。
2. **text**：text `gui/contract.py` text `adapt()` text，text。
3. **text**：`gui/worker.py` text `mock_data.build()` text，text。

---

## text Wyh text

`requirements.txt` text：

```text
PySide6>=6.5
```

**text。** text `PySide6.QtCharts`，text `pyside6` text，text pyqtgraph、text matplotlib、text `PyQtChart`。

> text `PyQtChart` text PyQt text，text PySide6 text `PySide6.QtCharts`，`pip install PyQtChart` text。text，text。

text，`PySide6-Essentials` text QtCharts（text WebEngine text 60MB）。text QtCharts text，text。

---

## textRules（text code review text）

1. **`gui/` text import text、`models.py`、`PySide6`。** text import `git_reader` / `metrics` / `cli`——text，text。
2. **`models.py` text LTY text TYB，text。** text，text，text。
3. **text，text。** text「text」text。
   - text：text/text/text `commit_calendar` text。

---

## text（text，text）

1. **`author_stats.share`** —— 0–1 text，text？text 0–1 text。
2. **`warnings.severity`** —— text `high` / `medium` / `low` text？text。
3. **text** —— `Commit.authored_at` text naive text aware？text `TypeError`。text（`mock_data._naive()`），text。

---

## directory（text）

```text
gui/
  contract.py       ← text，text（text TODO text）
  mock_data.py      ← text git + text（TYB text _compute text）
  worker.py         ← QThread worker，analyzetext
  main_window.py    ← text、text、text、text
  select_page.py      settings_page.py    ← text 1、2 text：Repository / Analysis Settings
  dashboard.py        trends.py           ← text 3、4 text：text / Commit Trends
  charts.py           tables.py           ← text 5、6 text：Author Contributions / Data Analysis
  patterns.py         report_page.py      ← text 7、8 text：Anti-pattern Center / Reports
  batch.py                                ← text 9 text：Repository Comparison
  plotting.py       ← QtCharts text + text
  widgets.py        ← text / text / text / text
  dialogs.py        ← repositorycheck、ErrorNotice、text
  style.qss         ← text
main.py             ← text（GUI text CLI）
docs/DEMO.md        ← text：text、text、text
```

text——text「text」text，text。


