# RepoScope

RepoScope 是一个基于 Python 的本地 Git 仓库健康分析工具。它直接读取本地仓库的提交历史和文件元数据，通过可视化指标和可解释的反模式规则，帮助开发者、课程项目团队和项目维护者了解仓库的维护状态。

RepoScope 的设计目标是把“提交记录”转换为可以理解、可以行动的健康报告：用户可以看到提交活动、贡献者分布、文件热点、长期未更新文件、大文件、提交信息规范和潜在维护风险，并将结果导出为 Markdown、HTML 或 CSV。

## 项目特点

- **Local-First**：直接读取本地 `.git` 目录，不上传仓库源码，也不依赖 GitHub/GitLab API。
- **可解释分析**：每条风险都包含指标名称、实际值、阈值、风险等级和建议动作。
- **图形化查看**：通过 PySide6（内置 QtCharts 绘制图表）展示仪表盘、时间趋势、贡献者分布和文件热点。
- **可配置规则**：支持通过 GUI 或 YAML/JSON 修改分析阈值和提交信息格式。
- **多仓库比较**：支持一次分析多个本地仓库，便于课程项目和团队维护比较。
- **多格式导出**：支持 Markdown、HTML 和 CSV，方便提交、展示和后续数据处理。

## 主要功能

### Git 数据读取

- 读取提交哈希、作者、时间、提交信息、修改文件、增加行数和删除行数。
- 读取分支、tag、文件大小、文件类型和文件修改时间。
- 扫描已跟踪文件以及未被 `.gitignore` 排除的未跟踪文件。
- 校验仓库路径、Git 目录和 Git 命令，并向界面返回明确的错误信息。

### 统计指标

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
commit_message_pattern: "^(feat|fix|docs|refactor)(\\(.+\\))?:"
```

风险等级分为高风险、中风险和低风险/提示。报告会同时显示实际值、阈值和建议动作，例如增加共同维护者、拆分热点文件、清理大文件、补充版本 tag 或统一提交模板。

## 使用流程

1. 在 GUI 中选择一个或多个本地 Git 仓库。
2. 设置时间范围、提交信息格式和各项分析阈值。
3. 在后台线程运行读取和分析任务，界面保持响应。
4. 查看仪表盘、提交趋势、贡献者、文件热点、大文件、未更新文件和风险摘要。
5. 点击风险项跳转到相关提交、文件或统计页面。
6. 导出 Markdown、HTML 或 CSV 报告。

## 技术架构

```text
PySide6 GUI（QtCharts 图表）
            |
应用服务层：任务调度、配置、结果组合
            |
数据分析层：GitReader、Metrics、Anti-pattern Rules
            |
数据模型层：RepositorySnapshot、Commit、FileRecord、AnalysisResult
            |
本地 Git 仓库
```

- GUI 使用 PySide6；图表用 PySide6 自带的 QtCharts，不引入额外图表库。
- Git 数据读取使用 Python `subprocess` 调用系统 Git，避免上层模块直接拼接 Git 命令。
- 长时间分析使用后台线程，避免阻塞界面。
- 数据模型在各层之间统一传递，便于单元测试和后续扩展。
- CLI、GUI 和报告导出共享同一套分析结果。

## 当前代码结构

```text
models.py                            共享的数据模型
git_reader.py                        本地 Git 数据读取层
gui/                                 图形界面层（九页 + 契约 + 后台线程）
run_gui.py                           图形界面入口
tests/test_models.py                 数据模型测试
tests/test_git_reader.py             临时 Git 仓库集成测试
tests/test_git_reader_validation.py  仓库路径和 Git 校验测试
tests/test_gui_smoke.py              界面冒烟测试（离屏运行，无需显示器）
docs/GUI_INTERFACE.md                GUI 接口说明（给队友看字段和接法）
docs/DEMO.md                         演示执行卡
```

已完成：Git 数据读取层（仓库校验、提交历史、文件元数据、分支、tag、统一异常处理）和图形界面的九个页面（导航、图表、表格、导出、后台分析线程）。

进行中：`metrics.py` 的统计指标与反模式规则、CLI、报告导出模块。界面目前接的是 `gui/mock_data.py` 里的临时统计（函数头标了 `TEMP`），`metrics.py` 到位后只替换这一处，界面不动。

## 环境要求

- Python 3.10 或更高版本
- Git，并且 Git 命令位于系统 `PATH` 中
- GUI 阶段只需要 PySide6（QtCharts 随 PySide6 一起安装，不需要额外图表库）
- 测试需要 pytest

Git 数据读取层使用系统 Git 和 Python 标准库，不需要 GitPython，也不需要网络连接或远程平台账号。

## 安装与测试

在项目根目录执行：

```powershell
python -m pip install pytest pyside6   # 测试 + 图形界面
python -m pytest -q                    # 全部测试
```

只跑数据层测试的话 `pytest` 单独装就够——GUI 冒烟测试在没有 PySide6 时会自动跳过，不会让其他人红一片。

### Windows：`python` 命令没有任何输出

如果输入 `python -V` 后既没有版本号也没有报错、直接回到提示符，说明命令行里的 `python` 指向了 Windows 应用商店的占位程序（`...\WindowsApps\python.exe`），它不是真正的解释器，退出码 9009。

用 Python 官方的启动器绕过它，并在项目里建一个独立环境（`.venv/` 已在 `.gitignore` 中）：

```powershell
py -0p                                              # 列出本机所有解释器
py -3.11 -m venv .venv                              # 用 3.11 建环境
.\.venv\Scripts\python.exe -m pip install pyside6   # 装依赖
.\.venv\Scripts\python.exe run_gui.py --demo        # 启动界面
```

环境建好之后，`.venv\Scripts\` 里有真正的 `python.exe`，激活后 `python` 这个名字就恢复正常了，也不再受应用商店占位程序影响。

想彻底修好全局的 `python` 名字，两步：一是在「设置 → 应用 → 高级应用设置 → 应用执行别名」里关掉 `python.exe` 和 `python3.exe`；二是把真实的 Python 目录（例如 `%LOCALAPPDATA%\Programs\Python\Python311\` 和其下的 `Scripts\`）加入用户 `PATH`。

## 图形界面（GUI）

三种启动方式：

```powershell
python run_gui.py                     # 启动后在界面里选仓库
python run_gui.py --demo              # 内置演示数据集（160 次提交 / 4 位作者）
python run_gui.py --path <仓库目录>    # 启动即分析指定仓库
```

`run_gui.bat` 和 `run_real.bat` 是上面后两条的双击版，会自动检查环境。`--demo` 与 `--path` 互斥。

界面按八个区域分成九页：仓库选择、分析配置、总览仪表板、提交趋势、作者贡献、数据分析、反模式中心、报告区、多仓库对比。「进度反馈」是常驻顶部进度条，不单独成页。分析在 `QThread` 子线程执行，主线程只接信号，所以切换页面不阻塞、分析期间不白屏。

界面只认 `gui/contract.py` 里的 `AnalysisView` 契约，不直接依赖 `git_reader` 或 `metrics`，两者可以并行开发。字段清单、待补字段和接入方式见 [`docs/GUI_INTERFACE.md`](docs/GUI_INTERFACE.md)；两种演示模式的差异和台本见 [`docs/DEMO.md`](docs/DEMO.md)。

## 功能边界

RepoScope 只分析本地 Git 数据，不包含 GitHub/GitLab Issue、Pull Request review、远程 API 权限、Issue 关闭率或 PR 响应时间等平台专属数据。仓库内容不会自动上传，分析结果只保存在本地或由用户主动导出。

## 课程项目目标

RepoScope 面向 Applied Programming with Python 课程项目，强调模块化设计、图形界面、数据处理、配置驱动的规则、异常处理、单元测试、集成测试和文档化。每位成员的模块通过统一模型接口协作，便于独立开发、测试和代码审查。
