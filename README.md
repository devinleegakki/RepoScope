# RepoScope

RepoScope text Python textlocal Git repository health analysistext。textlocalrepositorytextcommitstextfilestext，textanti-patternsRules，text、textrepositorytext。

RepoScope text“commitstext”text、textreport：textcommitstext、text、File hotspots、textfiles、Large files、commitsInformationconventiontextRisk，text Markdown、HTML text CSV。

## text

- **Local-First**：textlocal `.git` directory，textrepositorySource，text GitHub/GitLab API。
- **textanalyze**：textRisktext、Actual value、threshold、RiskLeveltextSuggested action。
- **text**：text PySide6（text QtCharts text）text、text、textFile hotspots。
- **textconfigurationRules**：text GUI text YAML/JSON textanalyzethresholdtextcommitsInformationtext。
- **textrepositorytext**：textanalyzetextlocalrepository，text。
- **text + report**：text `main.py` text（analyze / check / batch），text GUI textanalyzetext，text Markdown / HTML / CSV report。
- **text**：text Markdown、HTML text CSV，textcommits、text。

## text

### Git text

- textcommitstext、authors、text、commitsInformation、textfiles、text。
- textbranches、tag、filestext、filestextfilestext。
- textfilestext `.gitignore` textfiles。
- checkrepositoryPath、Git directorytext Git text，textErrorInformation。

### Compute metrics（textanti-patternsRules，textanalyzetext）

- text、texttime rangetextcommitstext。
- textauthorscommit counttext、text 90 text。
- textFile hotspots。
- textthresholdtextLarge files。
- textfilestextcommitstextrepository。
- textcommitsInformationtext、textconfigurationtextcommit format。
- text tag textcommitstext。

### anti-patternstextRiskNotice

defaultRulestext：

```yaml
stale_days: 180
large_file_mb: 10
single_maintainer_ratio: 0.70
release_stale_days: 365
hotspot_changes: 10
commit_message_pattern: "^(feat|fix|docs|refactor|test|chore)(\(.+\))?:"
```

RiskLeveltextHigh risk、Medium risktextLow risk/Notice。reporttextActual value、thresholdtextSuggested action，text、textHot files、textLarge files、text tag textcommitstext。

## text（text）

```text
core/                                text、Git text、analyzetextreporttext
  models.py                          text（LTY）
  git_reader.py                      local Git text（LTY）
  services.py                        textanalyzetext + configuration + textrepositoryBatchanalyze（WPH）
  reporters.py                       Markdown / HTML / CSV reporttext（WPH）
cli/                                 text：analyze / check / batch（WPH）
main.py                              text（textfilestext；WPH）
main.py                              text：GUI（--demo / --path）text CLI text
gui/                                 text（text + text + text）（HJH）
tests/                               text、text（WPH text）
docs/GUI_INTERFACE.md                GUI text（text）
docs/DEMO.md                         text
docs/screens/                        text
tools/screenshot.py                  text
requirements.txt                     text（WPH）
README.md                            text（WPH）
```

textComplete：Git text（repositorycheck、commitstext、filestext、branches、tag、text）text（text、text、text、text、textanalyzetext）。

text：`metrics.py` textCompute metricstextanti-patternsRules（TYB）；WPH text CLI/report/Batchanalyzetext，text `metrics.py` text `gui/mock_data.py` text，text `services.py` text。

## text（text）

| text | text / text | text | text | text |
| --- | --- | --- | --- | --- |
| LTY | Git textrepositorytext | repositorytext、textcommitstext/filestext/branches/tag、text | `core/git_reader.py`、`core/models.py` | textComplete |
| TYB | Compute metricstextanti-patternstext | Commit Trends、Author Contributions、File hotspots、Large files、Commit convention、anti-patternsRules | `metrics.py`、`rules.py` | text |
| HJH | PySide6 GUI text | text、text、text、text、text | `gui/*.py` | textComplete |
| wph | CLI、report、Batchanalyzetext | `main.py` analyze/check/export text；Markdown/HTML/CSV report；textrepository ThreadPoolExecutor Batchanalyze + textrepositoryfailedtext；text；`requirements.txt`、`README.md`、text | `main.py`、`cli/`、`core/`、`requirements.txt` | text |

## text

### text（text）

```powershell
python -m pip install PySide6>=6.5
python main.py                          # textrepository
python main.py --demo                   # text（160 textcommits / 4 textauthors）
python main.py --path <repositorydirectory>        # textanalyzetextrepository
```

text：Repository、Analysis Settings、Dashboard、Commit Trends、Author Contributions、Data Analysis、Anti-pattern Center、Reports、Repository Comparison。analyzetext，text。

### text（WPH text）

textfiles `main.py`，text：

```powershell
# 1. analyzetextrepository，Export report（md / html / csv / all）
python main.py analyze <repositorydirectory> [--format markdown] [--output reports]

# 2. checkrepositorytextanalyze（textfiles，text）
python main.py check <repositorydirectory> [--json]

# 3. analyzetext（analyze text）
python main.py export <repositorydirectory> [--output reports]

# 4. textanalyzetextrepository，textfailedtext
python main.py batch <repositorydirectory...> [-j 4] [--format all] [--output reports]
```

configurationtext：text > `--config <files.json>` > defaulttext。textconfigurationtext：
`--stale-days`、`--large-file-mb`、`--hotspot-changes`、`--release-stale-days`、
`--single-maintainer-ratio`、`--window-days`（text N textcommits）、
`--commit-pattern`（commitsInformationconventionregex）。

`analyze` text `reports/<repositorytext>_report.{md,html,csv}` textoutput directory；
`batch` text `batch_summary.md` text `batch_summary.csv` textrepositorytext。

### text

```powershell
python main.py --demo             # GUI text，text Git repository
python main.py check .          # textrepositorytextanalyze
```

## text

textroot directorytext：

```powershell
python -m pip install PySide6>=6.5   # GUI text；CLI text Python text
python -m pip install pytest          # text
python -m pytest -q                   # text（text PySide6 text）
```

text：31 text + WPH text/report/text，text。

### CI/CD（GitHub Actions）

repositorytext CI text：

- `.github/workflows/ci.yml`：text `main` text push text Pull Request text，text Windows、Python 3.11/3.12 text `config/requirements-dev.txt`，textSourcetext。
text Windows text；text，text Windows text。

### Windows：`python` text

text README text：text `python -V` text，text，text `py -3.11`（text）text，text Python text `PATH`。

text：Sourcetextfilestext `main.py`，text `README.md`，textSource、textfilestext `readme` text `groupN_project.zip`。

## text

RepoScope text Applied Programming with Python text，text、text、text、configurationtextRules、text、text、text。text，text、text。

RepoScope textanalyzelocal Git text，text GitHub/GitLab Issue、Pull Request review、text API text、Issue text PR text。repositorytext，Resultstextlocaltext。

