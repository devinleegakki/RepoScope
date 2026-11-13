# RepoScope

RepoScope 是一个本地优先的 Git 仓库健康分析工具。它读取本地仓库中的提交历史和文件元数据，并将结果整理为结构化数据，供后续的统计分析、可视化和报告模块使用。

当前分支实现 Git 数据读取层。该层与 GUI、CLI 和统计分析层解耦，其他模块可以直接使用统一的数据模型。

## 当前功能

- 校验仓库路径，并返回明确的错误信息。
- 读取所有本地分支的提交记录，按时间从新到旧排列。
- 读取提交作者、邮箱、时间、提交摘要、修改文件、增加行数、删除行数以及指向该提交的 tag。
- 扫描已跟踪文件和未被 `.gitignore` 排除的未跟踪文件。
- 记录文件相对路径、大小、扩展名、修改时间和跟踪状态。
- 读取本地分支名和 tag 名。
- 返回不可变的 `RepositorySnapshot`、`Commit` 和 `FileRecord` 数据对象。
- 使用结构化的 `GitReaderError` 错误码处理路径、Git 命令、超时和解析错误。

## 环境要求

- Python 3.10 或更高版本
- 已安装 Git，且 Git 命令位于系统 `PATH` 中
- 运行测试需要 `pytest`

读取器通过 `subprocess` 调用系统 Git，不依赖 GitPython，也不调用远程 GitHub 或 GitLab API。

## 快速开始

在项目根目录执行：

```powershell
python -m pip install pytest
python -m pytest -q
```

在 Python 中读取一个本地仓库：

```python
from git_reader import GitReader, GitReaderError

try:
    snapshot = GitReader(r"C:\path\to\repository").read_snapshot()
except GitReaderError as error:
    print(f"[{error.code}] {error}")
else:
    print(snapshot.repo_name)
    print(f"提交数：{len(snapshot.commits)}")
    print(f"文件数：{len(snapshot.files)}")
```

如需限制读取的提交数量，可以传入 `max_commits`：

```python
recent = GitReader(".").read_snapshot(max_commits=20)
```

## 数据模型

`RepositorySnapshot` 是统计分析层和 GUI 层使用的主要对象，包含提交记录、文件记录、本地分支、tag、仓库路径、仓库名称和 UTC 扫描时间。

所有模型都是不可变 dataclass。文件路径始终是相对于仓库根目录的路径，并统一使用 `/` 作为分隔符，因此在 Windows 上也能保持一致。

## 错误处理

应用程序边界应捕获 `GitReaderError`。其中：

- `code` 用于决定 GUI 或 CLI 的处理方式。
- `details` 保存更具体的诊断信息。
- `command` 保存发生错误的 Git 命令。

常见错误码包括：

- `path_not_found`：仓库路径不存在
- `not_a_directory`：路径不是目录
- `not_a_git_repository`：目录不是 Git 仓库
- `git_not_installed`：系统找不到 Git
- `git_timeout`：Git 命令超时
- `commit_read_failed`：读取提交失败
- `file_read_failed`：读取文件信息失败
- `ref_read_failed`：读取分支或 tag 失败
- `parse_error`：解析 Git 输出失败

## 项目结构

```text
models.py                            共享的不可变数据模型
git_reader.py                        本地 Git 读取器和错误处理
tests/test_models.py                 数据模型测试
tests/test_git_reader.py             临时 Git 仓库集成测试
tests/test_git_reader_validation.py  路径和仓库校验测试
```

## 功能范围

Git 数据层只读取本地 Git 数据。指标计算、反模式规则、PySide6/PyQtGraph 界面、报告导出以及远程代码托管平台 API 属于 RepoScope 的其他模块。
