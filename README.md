# RepoScope

RepoScope 是一个基于 Python 的本地 Git 仓库健康分析工具。它直接读取本地仓库的提交历史和文件元数据，通过可视化指标和可解释的反模式规则，帮助开发者、课程项目团队和项目维护者了解仓库的维护状态。

RepoScope 的设计目标是把“提交记录”转换为可以理解、可以行动的健康报告：用户可以看到提交活动、贡献者分布、文件热点、长期未更新文件、大文件、提交信息规范和潜在维护风险，并将结果导出为 Markdown、HTML 或 CSV。

## 项目特点

- **Local-First**：直接读取本地 `.git` 目录，不上传仓库源码，也不依赖 GitHub/GitLab API。
- **可解释分析**：每条风险都包含指标名称、实际值、阈值、风险等级和建议动作。
- **图形化查看**：通过 PySide6 和 PyQtGraph 展示仪表盘、时间趋势、贡献者分布和文件热点。
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
PySide6 + PyQtGraph GUI
            |
应用服务层：任务调度、配置、结果组合
            |
数据分析层：GitReader、Metrics、Anti-pattern Rules
            |
数据模型层：RepositorySnapshot、Commit、FileRecord、AnalysisResult
            |
本地 Git 仓库
```

- GUI 使用 PySide6 和 PyQtGraph。
- Git 数据读取使用 Python `subprocess` 调用系统 Git，避免上层模块直接拼接 Git 命令。
- 长时间分析使用后台线程，避免阻塞界面。
- 数据模型在各层之间统一传递，便于单元测试和后续扩展。
- CLI、GUI 和报告导出共享同一套分析结果。

## 当前代码结构

```text
models.py                            共享的数据模型
git_reader.py                        本地 Git 数据读取层
tests/test_models.py                 数据模型测试
tests/test_git_reader.py             临时 Git 仓库集成测试
tests/test_git_reader_validation.py  仓库路径和 Git 校验测试
```

当前仓库已完成 Git 数据读取层，包括仓库校验、提交历史、文件元数据、分支、tag 和统一异常处理。统计分析、GUI、CLI 和报告导出将在后续模块中接入相同的数据模型。

## 环境要求

- Python 3.10 或更高版本
- Git，并且 Git 命令位于系统 `PATH` 中
- GUI 阶段需要 PySide6 和 PyQtGraph
- 测试需要 pytest

Git 数据读取层使用系统 Git 和 Python 标准库，不需要 GitPython，也不需要网络连接或远程平台账号。

## 安装与测试

在项目根目录执行：

```powershell
python -m pip install pytest
python -m pytest -q
```

GUI 模块完成后，再按项目依赖安装 PySide6 和 PyQtGraph。当前 Git 数据层测试只需要 `pytest`：

```powershell
python -m pip install pytest
python -m pytest -q
```

## 功能边界

RepoScope 只分析本地 Git 数据，不包含 GitHub/GitLab Issue、Pull Request review、远程 API 权限、Issue 关闭率或 PR 响应时间等平台专属数据。仓库内容不会自动上传，分析结果只保存在本地或由用户主动导出。

## 课程项目目标

RepoScope 面向 Applied Programming with Python 课程项目，强调模块化设计、图形界面、数据处理、配置驱动的规则、异常处理、单元测试、集成测试和文档化。每位成员的模块通过统一模型接口协作，便于独立开发、测试和代码审查。
