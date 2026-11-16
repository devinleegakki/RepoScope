# GUI 接口说明

面向 LTY（`git_reader`）、TYB（`metrics` / `rules`）、Wyh（CLI / 报告 / 依赖清单）。
**你不需要读 GUI 代码，只需要看这一页。**

---

## 一句话

界面只认 `gui/contract.py` 里的 `AnalysisView` 这一个契约。**谁产出这个结构，界面就能显示；不符合同样能显示**——在 `adapt()` 里做一次字段映射就行，界面代码一行不用改。

```python
# 你只需要保证能产出这个（字段名可以不同，告诉我实际名字）
from gui.contract import AnalysisView
```

`gui/contract.py` 只依赖标准库和 `models.py`，**不装 PySide6 也能 import**，可以拿它当对齐字段的清单。

---

## 30 秒上手

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pyside6 pytest
.\.venv\Scripts\python.exe run_gui.py --demo     # 内置数据集，界面立刻有内容
```

不想敲命令就双击仓库根目录的 `run_gui.bat`（演示数据）或 `run_real.bat`（分析本仓库）。两个脚本会自己检查环境、缺什么装什么。

在 VS Code 里按 `F5` 也行，`.vscode/launch.json` 里已经配好五条。

**Windows 上 `python` 没反应**：那是应用商店的占位程序，用 `py -3.11` 代替，详见根目录 README 的排障一节。

---

## 现在能跑到什么程度

| 项 | 状态 |
|---|---|
| 九个页面 | 全部可交互，导航切换不销毁页面 |
| 后台分析 | `QThread` + `moveToThread`，主线程不阻塞 |
| 图表 | `PySide6.QtCharts`，随 PySide6 一起装 |
| 测试 | `pytest -q` → 31 passed（没装 PySide6 时界面那组自动跳过，数据层照常跑） |
| 截图 | `docs/screens/` 九张，`tools/screenshot.py` 可重新生成 |

**当前数据链路**：`git_reader` 真实读取 → `gui/mock_data.py` 里一段临时统计（`_compute`，函数头标了 `TEMP`）→ 界面。

也就是说：**数字能跑通、能演示，但算法是我的临时实现，不是 TYB 的 `metrics.py`。** 这部分要替换。

---

## 你要给我什么

状态列说明：

- **TEMP** —— 界面已经有值，但来自 `mock_data._compute` 的临时算法，需换成真实现
- **缺** —— 字段还没定义，界面位置已画好，缺值时显示「待后端提供」而不是 0

### 1. `AnalysisView` 顶层字段

| 字段 | 类型 | 界面上用在哪 | 谁 | 状态 |
|---|---|---|---|---|
| `snapshot` | `RepositorySnapshot` | 总览副标题、报告头 | LTY | ✅ 真数据 |
| `health_score` | `float` 0–100 | 健康度大卡、对比表、报告 | TYB | TEMP |
| `total_commits` | `int` | 总览卡 / 对比表 / 报告 | TYB | TEMP |
| `author_count` | `int` | 总览卡 / 对比表 | TYB | TEMP |
| `file_count` | `int` | 总览卡 / 数据分析副标题 | TYB | TEMP |
| `commit_calendar` | `dict[str, int]` | 热力图 + 趋势折线 | TYB | TEMP |
| `author_stats` | `list[AuthorStat]` | 作者页条形 + 明细表 | TYB | TEMP |
| `hotspot_files` | `list[FileStat]` | 数据分析 · 热点 | TYB | TEMP |
| `large_files` | `list[FileStat]` | 数据分析 · 大文件 | TYB | TEMP |
| `stale_files` | `list[FileStat]` | 数据分析 · 陈旧 | TYB | TEMP |
| `warnings` | `list[Warning]` | 反模式中心 + 总览摘要 + 报告第 6 节 | TYB | TEMP |
| `commit_hygiene` | `CommitHygiene` | 总览「提交规范通过率」卡 + 报告第 7 节 | TYB | TEMP |
| `risk_level` | `str` | 总览右上角等级徽标 | TYB | TEMP |
| `elapsed_seconds` | `float` | 状态栏「用时 x.xs」 | 服务层 | TEMP |

### 2. `commit_calendar` —— 请直接给日期字典，别给 commit 列表

```python
commit_calendar = {"2026-11-13": 12, "2026-11-14": 5, ...}   # 日期 → 当天提交数
```

热力图和趋势图都吃这一份数据（日/周/月三种视图是同一份数据的切片，不是三份新数据）。如果后端给一串 `Commit` 让我在前端按周聚合，那个逻辑会散在界面层，违反「界面不自己算」的约定。

### 3. `Warning` —— 反模式中心最需要，优先级最高

反模式中心这一页的全部卖点就是「每条规则都能解释」。只给一句话，这页就废了。

| 字段 | 类型 | 例子 | 用在哪 |
|---|---|---|---|
| `condition` | `str` | `"单一作者提交占比 ≥ 70%"` | 详情「触发条件」 |
| `actual` | `str` | `"90%（9 次）"` | 详情「实际值」 |
| `threshold` | `str` | `"70%"` | 详情「配置阈值」 |
| `action` | `str` | `"让第二位成员参与核心模块"` | 详情「建议动作」 |

**为什么是 `str` 不是数字**：不同规则单位不一样（`70%` / `10 MB` / `180 天`），后端拼成一句人话最省事，前端也不用维护单位映射表。

**后端没给全时界面怎么表现**：详情页底部出现橙色提示「以下字段待 rules.py 补齐」，报告对应单元格写「待 rules.py 补齐」。**界面不编造**——演示时被问「这个阈值哪来的」必须答得上。

### 4. `FileStat` 追加三个字段

| 字段 | 类型 | 用在哪 |
|---|---|---|
| `changed_lines` | `int` | 热点表「累计改动」列（`git log --numstat` 求和） |
| `file_type` | `str` | 大文件表「类型」列 |
| `is_binary` | `bool` | 大文件榜区分二进制（这类文件不能按行数看） |

### 5. `AuthorStat.recent_90d_share`

`float` 0–1，最近 90 天提交占该人总提交的比例。用途：识别「历史贡献高但人已经不在了」。

**未提供时请留 `-1.0`**（默认就是 -1），界面显示「—」并给 tooltip 说明，不会显示成 0%。

### 6. `CommitHygiene`（新增类型）

| 字段 | 类型 | 说明 |
|---|---|---|
| `pass_rate` | `float` | 0–1；`-1` 表示未检查 |
| `total` / `passed` | `int` | 分母 / 分子 |
| `pattern` | `str` | 实际用的正则，报告里要写出来，否则通过率无从复核 |
| `violations` | `tuple[Violation, ...]` | `commit_hash` / `message` / `reason` |

### 7. `RepoSummary`（多仓库对比表一行）

`repo_name` / `path` / `commits` / `authors` / `health_score` / `hotspot_count` / `stale_count` / `risk_level`

---

## 怎么接（三步，大部分是我的活）

1. **TYB**：`metrics.py` 产出尽量对齐上表；名字不一样也行，把实际名字发我。
2. **我**：在 `gui/contract.py` 的 `adapt()` 里写映射，通常五行。
3. **我**：`gui/worker.py` 里把 `mock_data.build()` 换成真实服务调用，界面其余部分不动。

---

## 给 Wyh 的依赖清单

`requirements.txt` 请写：

```text
PySide6>=6.5
```

**只这一行。** 图表用 `PySide6.QtCharts`，它随 `pyside6` 一起装，不需要 pyqtgraph、不需要 matplotlib、不需要 `PyQtChart`。

> 组长文档里写的 `PyQtChart` 是 PyQt 系列的包名，在 PySide6 里对应 `PySide6.QtCharts`，`pip install PyQtChart` 在这套环境下装不上。评审机器上少装一个包就是图表白屏，这条必须对齐。

如果只想装精简版，`PySide6-Essentials` 也含 QtCharts（省掉 WebEngine 那 60MB）。界面在 QtCharts 缺失时会自动降级成表格，不会崩。

---

## 三条边界规则（也是 code review 检查项）

1. **`gui/` 只 import 标准库、`models.py`、`PySide6`。** 不 import `git_reader` / `metrics` / `cli`——那些还在改，直连就是每天修界面。
2. **`models.py` 归 LTY 和 TYB，我只读不改。** 要加字段在群里说，别各自改，不然合并必冲突。
3. **界面上任何数字都来自传入的对象，页面不自己算。** 这样「图表数据与后端一致」这条验收标准才有保证。
   - 唯一例外写在注释里：趋势图的日/周/月是同一份 `commit_calendar` 的三种切片。

---

## 我这边还没确认的三件事（会影响对接，麻烦回一下）

1. **`author_stats.share`** —— 0–1 的小数，还是百分比整数？我按 0–1 写的。
2. **`warnings.severity`** —— 取值是不是就 `high` / `medium` / `low` 三档？界面按三档配色。
3. **时间字段带不带时区** —— `Commit.authored_at` 是 naive 还是 aware？两个相减会直接抛 `TypeError`。我这边做了兼容（`mock_data._naive()`），但最好统一成一种。

---

## 目录（只看前三个就够）

```text
gui/
  contract.py       ← 接口定义，先看这个（所有 TODO 都在这）
  mock_data.py      ← 真读 git + 临时统计（TYB 到位后删 _compute 整段）
  worker.py         ← QThread worker，分析只在子线程跑
  main_window.py    ← 外壳、导航映射、线程调度、演示模式
  select_page.py      settings_page.py    ← 第 1、2 页：仓库选择 / 分析配置
  dashboard.py        trends.py           ← 第 3、4 页：总览 / 提交趋势
  charts.py           tables.py           ← 第 5、6 页：作者贡献 / 数据分析
  patterns.py         report_page.py      ← 第 7、8 页：反模式中心 / 报告区
  batch.py                                ← 第 9 页：多仓库对比
  plotting.py       ← QtCharts 封装 + 无图表库时降级
  widgets.py        ← 指标卡 / 徽标 / 页头 / 空状态
  dialogs.py        ← 仓库校验、错误提示、导出对话框
  style.qss         ← 配色和间距
run_gui.py          ← 入口（--demo / --path / 无参数）
docs/DEMO.md        ← 演示执行卡：两种模式、哪几页会空、台本
```

九页对应组长文档的八个区域——文档里的第八个区域「进度反馈」是常驻顶部进度条，不单独成页。
