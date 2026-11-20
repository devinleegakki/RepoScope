# RepoScope

RepoScope 是一个基于 Python 的本地 Git 仓库健康分析工具。它直接读取本地仓库的提交历史和文件元数据，通过可视化指标和可解释的反模式规则，帮助开发者、课程项目团队和项目维护者了解仓库的维护状态。

RepoScope 的设计目标是把“提交记录”转换为可以理解、可以行动的健康报告：用户可以看到提交活动、贡献者分布、文件热点、长期未更新文件、大文件、提交信息规范和潜在维护风险，并将结果导出为 Markdown、HTML 或 CSV。

## 项目特点

- **Local-First**：直接读取本地 `.git` 目录，不上传仓库源码，也不依赖 GitHub/GitLab API。
- **可解释分析**：每条风险都包含指标名称、实际值、阈值、风险等级和建议动作。
- **图形化查看**：通过 PySide6（内置 QtCharts 绘制图表）展示仪表盘、时间趋势、贡献者分布和文件热点。
- **可配置规则**：支持通过 GUI 或 YAML/JSON 修改分析阈值和提交信息格式。
- **多仓库比较**：支持一次分析多个本地仓库，便于课程项目和团队维护比较。
- **命令行 + 报告**：提供 `main.py` 命令行（analyze / check / batch），与 GUI 共用同一分析服务，导出 Markdown / HTML / CSV 报告。
- **多格式导出**：支持 Markdown、HTML 和 CSV，方便提交、展示和后续数据处理。

## 主要功能

### Git 数据读取

- 读取提交哈希、作者、时间、提交信息、修改文件、增加行数和删除行数。
- 读取分支、tag、文件大小、文件类型和文件修改时间。
- 扫描已跟踪文件以及未被 `.gitignore` 排除的未跟踪文件。
- 校验仓库路径、Git 目录和 Git 命令，并向界面返回明确的错误信息。

### 统计指标（与反模式规则，统一在分析服务里产出）

- 按日、周或自定义时间范围统计提交频率。
- 统计作者提交数量、贡献占比和 90 天贡献集中度。
- 识别修改次数较高的文件热点。
- 识别超过阈值的大文件。
- 识别长期未修改的文件和长期没有提交活动的仓库。
- 检查提交信息是否为空、过短或不符合配置的提交格式。
- 结合 tag 和提交时间识别版本发布后的停滞情况。

### 反模式与风险提示

默认规则包括：

```yaml
stale_days: 180
large_file_mb: 10
single_maintainer_ratio: 0.70
release_stale_days: 365
hotspot_changes: 10
commit_message_pattern: "^(feat|fix|docs|refactor|test|chore)(\(.+\))?:"
```

风险等级分为高风险、中风险和低风险/提示。报告会同时显示实际值、阈值和建议动作，例如增加共同维护者、拆分热点文件、清理大文件、补充版本 tag 或统一提交模板。

## 项目结构（当前代码结构）

```text
core/                                共享数据模型、Git 读取、分析服务和报告生成
  models.py                          共享的数据模型（LTY）
  git_reader.py                      本地 Git 数据读取层（LTY）
  services.py                        统一分析服务 + 配置 + 多仓库批量分析（WPH）
  reporters.py                       Markdown / HTML / CSV 报告生成（WPH）
cli/                                 命令行包：analyze / check / batch（WPH）
main.py                              命令行入口（课程要求的入口文件名；WPH）
main.py                              唯一入口：GUI（--demo / --path）与 CLI 子命令
gui/                                 图形界面层（九页 + 契约 + 后台线程）（HJH）
tests/                               单元测试、集成测试（WPH 负责集成部分）
docs/GUI_INTERFACE.md                GUI 接口说明（给队友看字段和接法）
docs/DEMO.md                         演示执行卡
docs/screens/                        九张界面截图
tools/screenshot.py                  重新生成截图
requirements.txt                     依赖清单（WPH）
README.md                            安装与运行说明（WPH）
```

已完成：Git 数据读取层（仓库校验、提交历史、文件元数据、分支、tag、统一异常处理）和图形界面的九个页面（导航、图表、表格、导出、后台分析线程）。

进行中：`metrics.py` 的统计指标与反模式规则（TYB）；WPH 的 CLI/报告/批量分析模块已加入，在 `metrics.py` 未落地前先用 `gui/mock_data.py` 的临时统计跑通，替换时只在 `services.py` 的一处接上。

## 小组分工（组长方案中确认）

| 成员 | 负责模块 / 角色 | 主要任务 | 主要交付物 | 状态 |
| --- | --- | --- | --- | --- |
| LTY | Git 数据层与仓库读取 | 仓库验证、读取提交历史/文件元数据/分支/tag、单元测试 | `core/git_reader.py`、`core/models.py` | 已完成 |
| TYB | 统计指标与反模式检测 | 提交趋势、作者贡献、文件热点、大文件、提交规范、反模式规则 | `metrics.py`、`rules.py` | 待启动 |
| HJH | PySide6 GUI 与可视化交互 | 九个页面、图表、表格、导出、后台线程不阻塞界面 | `gui/*.py` | 已完成 |
| wph | CLI、报告、批量分析与质量集成 | `main.py` analyze/check/export 三个命令；Markdown/HTML/CSV 报告；多仓库 ThreadPoolExecutor 批量分析 + 单仓库失败隔离；统一服务层；`requirements.txt`、`README.md`、集成测试 | `main.py`、`cli/`、`core/`、`requirements.txt` | 已实现 |

## 使用流程

### 图形界面（推荐演示用）

```powershell
python -m pip install PySide6>=6.5
python main.py                          # 启动后在界面里选仓库
python main.py --demo                   # 内置演示数据集（160 次提交 / 4 位作者）
python main.py --path <仓库目录>        # 启动即分析指定仓库
```

界面按区域分成九页：仓库选择、分析配置、总览仪表板、提交趋势、作者贡献、数据分析、反模式中心、报告区、多仓库对比。分析在后台线程运行，界面不冻结。

### 命令行（WPH 负责部分）

入口文件 `main.py`，四个子命令：

```powershell
# 1. 分析一个仓库，导出报告（md / html / csv / all）
python main.py analyze <仓库目录> [--format markdown] [--output reports]

# 2. 校验仓库是否可分析（不写文件，可用于脚本）
python main.py check <仓库目录> [--json]

# 3. 分析并一次导出三种格式（analyze 的便捷版）
python main.py export <仓库目录> [--output reports]

# 4. 并发分析多个仓库，单个失败不影响其他任务
python main.py batch <仓库目录...> [-j 4] [--format all] [--output reports]
```

配置优先级：命令行参数 > `--config <文件.json>` > 默认值。可覆盖的配置项：
`--stale-days`、`--large-file-mb`、`--hotspot-changes`、`--release-stale-days`、
`--single-maintainer-ratio`、`--window-days`（只统计最近 N 天提交）、
`--commit-pattern`（提交信息规范正则）。

`analyze` 把 `reports/<仓库名>_report.{md,html,csv}` 写入输出目录；
`batch` 还会额外生成 `batch_summary.md` 和 `batch_summary.csv` 做跨仓库对比。

### 运行演示

```powershell
python main.py --demo             # GUI 演示，无需真实 Git 仓库
python main.py check .          # 检查本仓库本身是否可被分析
```

## 安装与测试

在项目根目录执行：

```powershell
python -m pip install PySide6>=6.5   # GUI 需要；CLI 只需要 Python 标准库
python -m pip install pytest          # 跑测试需要
python -m pytest -q                   # 全部测试（没有 PySide6 时界面那组自动跳过）
```

全部测试目前：31 个已有测试 + WPH 新增的服务/报告/命令行集成测试，全部通过。

### CI/CD（GitHub Actions）

仓库包含一条 CI 工作流：

- `.github/workflows/ci.yml`：对 `main` 的 push 和所有 Pull Request 自动运行，使用 Windows、Python 3.11/3.12 两个环境安装 `config/requirements-dev.txt`，执行源码编译检查和完整测试。
当前工作流只负责 Windows 环境下的自动测试；如需发布安装包，可以在此基础上另行增加 Windows 打包步骤。

### Windows：`python` 命令没有任何输出

同原 README 说明：如果 `python -V` 无输出，那是应用商店占位程序，用 `py -3.11`（或本机真实解释器）替代，并把真实 Python 加入 `PATH`。

课程要求：源码打包时把入口文件命名为 `main.py`，运行说明写在 `README.md`，把源码、数据文件和 `readme` 压成 `groupN_project.zip`。

## 课程项目目标

RepoScope 面向 Applied Programming with Python 课程项目，强调模块化设计、图形界面、数据处理、配置驱动的规则、异常处理、单元测试、集成测试和文档化。每位成员的模块通过统一模型接口协作，便于独立开发、测试和代码审查。

RepoScope 只分析本地 Git 数据，不包含 GitHub/GitLab Issue、Pull Request review、远程 API 权限、Issue 关闭率或 PR 响应时间等平台专属数据。仓库内容不会自动上传，分析结果只保存在本地或由用户主动导出。

