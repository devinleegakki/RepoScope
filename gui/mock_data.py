"""壳阶段的假数据源。

作用只有一个：在 LTY / TYB / Wyh 的代码合并进来之前，让界面有东西可显示。
接真数据时只需要把 ``build()`` 换成真实分析调用，界面代码一行不用改。

真实数据优先：如果 ``git_reader.GitReader`` 能读通，就用仓库的真提交记录，
读不通则退回内置的合成数据——保证演示永远不会白屏。

**所有临时计算都集中在这个文件里**，并且都标了 ``TEMP``。
TYB 的 ``metrics.py`` 到位后整段删掉，换成 ``from metrics import analyse``，
界面一行不动。
"""

from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence

from models import Commit, FileRecord, RepositorySnapshot

from .contract import (
    AuthorStat,
    CommitHygiene,
    FileStat,
    ProgressCallback,
    Violation,
    Warning,
    risk_of,
)

_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".ttf"}


@dataclass
class MockView:
    """一个满足 ``AnalysisView`` 的简单容器。"""

    snapshot: RepositorySnapshot
    health_score: float = 0.0
    total_commits: int = 0
    author_count: int = 0
    file_count: int = 0
    commit_calendar: Mapping[str, int] = field(default_factory=dict)
    author_stats: Sequence[AuthorStat] = field(default_factory=tuple)
    hotspot_files: Sequence[FileStat] = field(default_factory=tuple)
    large_files: Sequence[FileStat] = field(default_factory=tuple)
    stale_files: Sequence[FileStat] = field(default_factory=tuple)
    warnings: Sequence[Warning] = field(default_factory=tuple)
    elapsed_seconds: float = 0.0
    commit_hygiene: CommitHygiene = field(default_factory=CommitHygiene)
    risk_level: str = "low"


def build(
    repo_path: str,
    on_progress: ProgressCallback | None = None,
    *,
    stale_days: int = 180,
    large_file_mb: int = 10,
    hotspot_changes: int = 10,
    commit_pattern: str = r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: ",
    force_synthetic: bool = False,
) -> MockView:
    """跑一次分析，返回界面需要的数据。

    现在内部是临时实现，用来验证界面；TYB 的 ``metrics.py`` 到位后，
    把 ``_compute`` 换成他们的函数即可。

    ``force_synthetic=True`` 用于演示彩排：无视仓库真实内容，直接用内置的
    160 次提交数据集。真实仓库历史太短时（比如新仓库只有 10 个提交），
    趋势图和热力图会空得看不出效果，演示时用这个开关更稳妥。
    """
    report = on_progress or (lambda percent, message: None)
    started = datetime.now()

    report(5, "校验仓库路径")
    snapshot = None if force_synthetic else _read_real_snapshot(repo_path, report)
    if snapshot is None:
        report(20, "使用内置演示数据集" if force_synthetic else "读取失败，使用演示数据")
        snapshot = _synthetic_snapshot(repo_path)

    report(60, "统计指标")
    view = _compute(
        snapshot,
        stale_days=stale_days,
        large_file_mb=large_file_mb,
        hotspot_changes=hotspot_changes,
        commit_pattern=commit_pattern,
    )

    report(95, "整理结果")
    view.elapsed_seconds = (datetime.now() - started).total_seconds()
    report(100, "完成")
    return view


# --------------------------------------------------------------------------
# 真实数据读取（失败则返回 None，交给合成数据兜底）
# --------------------------------------------------------------------------
def _read_real_snapshot(repo_path: str, report: ProgressCallback) -> RepositorySnapshot | None:
    try:
        from git_reader import GitReader
    except ImportError:
        return None
    try:
        report(15, "读取提交历史")
        reader = GitReader(repo_path)
        reader.validate()
        report(40, "读取文件元数据")
        return reader.read_snapshot()
    except Exception:  # 壳阶段：任何失败都退回演示数据，绝不白屏
        return None


# --------------------------------------------------------------------------
# TEMP: 临时统计。TYB 的 metrics.py 到位后删除本段。
# --------------------------------------------------------------------------
def _naive(value: datetime | None) -> datetime | None:
    """把带时区的时间统一成朴素时间，否则相减会抛 TypeError。"""
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _compute(
    snapshot: RepositorySnapshot,
    *,
    stale_days: int,
    large_file_mb: int,
    hotspot_changes: int,
    commit_pattern: str,
) -> MockView:
    commits = snapshot.commits
    files = snapshot.files
    now = datetime.now()

    calendar: Counter[str] = Counter()
    for commit in commits:
        calendar[_naive(commit.authored_at).strftime("%Y-%m-%d")] += 1

    # -- 作者贡献 ------------------------------------------------------
    per_author: Counter[str] = Counter()
    insertions: Counter[str] = Counter()
    deletions: Counter[str] = Counter()
    recent: Counter[str] = Counter()
    cutoff = now - timedelta(days=90)
    for commit in commits:
        name = commit.author_name
        per_author[name] += 1
        insertions[name] += commit.insertions
        deletions[name] += commit.deletions
        if _naive(commit.authored_at) >= cutoff:
            recent[name] += 1
    total = sum(per_author.values()) or 1
    author_stats = [
        AuthorStat(
            name=name,
            commits=count,
            insertions=insertions[name],
            deletions=deletions[name],
            share=count / total,
            recent_90d_share=(recent[name] / count) if count else 0.0,
        )
        for name, count in per_author.most_common(12)
    ]

    # -- 文件榜单 ------------------------------------------------------
    changes: Counter[str] = Counter()
    for commit in commits:
        for path in commit.files_changed:
            changes[path] += 1

    # TEMP: 每个文件的改动行数拿不到（git log --numstat 在 TYB 那块），
    # 这里按"改动次数 × 平均每次 12 行"估算，只用于演示列宽。
    def _changed_lines(path: str) -> int:
        return changes[path] * 12

    large_bytes = large_file_mb * 1024 * 1024
    hotspots = [
        FileStat(
            path=path,
            change_count=count,
            author_count=min(count, len(per_author)),
            changed_lines=_changed_lines(path),
            file_type=Path(path).suffix.lstrip("."),
            is_binary=Path(path).suffix.lower() in _BINARY_SUFFIXES,
        )
        for path, count in changes.most_common()
        if count >= hotspot_changes
    ][:50]
    large = [
        FileStat(
            path=f.path,
            size_bytes=f.size_bytes,
            change_count=changes.get(f.path, 0),
            changed_lines=_changed_lines(f.path),
            file_type=f.file_type,
            is_binary=f.file_type.lower() in {s.lstrip(".") for s in _BINARY_SUFFIXES},
        )
        for f in sorted(files, key=lambda item: item.size_bytes, reverse=True)
        if f.size_bytes >= large_bytes
    ][:50]
    stale = [
        FileStat(
            path=f.path,
            days_since_change=(now - _naive(f.modified_at)).days,
            change_count=changes.get(f.path, 0),
            size_bytes=f.size_bytes,
            changed_lines=_changed_lines(f.path),
            file_type=f.file_type,
        )
        for f in files
        if _naive(f.modified_at) and (now - _naive(f.modified_at)).days >= stale_days
    ][:50]

    # -- 提交信息规范 --------------------------------------------------
    pattern = re.compile(commit_pattern) if commit_pattern else None
    violations: list[Violation] = []
    passed = 0
    for commit in commits:
        if pattern is None or pattern.search(commit.message):
            passed += 1
        else:
            violations.append(
                Violation(
                    commit_hash=commit.hash[:8],
                    message=commit.message.splitlines()[0][:60] if commit.message else "",
                    reason="不符合约定格式（缺少 feat/fix/docs 前缀）",
                )
            )
    hygiene = CommitHygiene(
        pass_rate=(passed / len(commits)) if commits else -1.0,
        total=len(commits),
        passed=passed,
        pattern=commit_pattern,
        violations=tuple(violations[:20]),
    )

    # -- 反模式警告（四要素齐全） --------------------------------------
    warnings: list[Warning] = []
    top_share = author_stats[0].share if author_stats else 0.0
    top_name = author_stats[0].name if author_stats else "—"

    if top_share >= 0.7:
        warnings.append(Warning(
            rule="单一作者依赖",
            severity="high",
            message=f"{top_name} 承担了 {top_share:.0%} 的提交，关键知识集中在一人身上",
            target=top_name,
            condition="单一作者提交占比 ≥ 70%",
            actual=f"{top_share:.0%}（{author_stats[0].commits} 次）",
            threshold="70%",
            action="让第二位成员参与核心模块，并在 PR 里补 code review 记录",
        ))
    if len(stale) >= 3:
        warnings.append(Warning(
            rule="陈旧文件堆积",
            severity="medium",
            message=f"{len(stale)} 个文件超过 {stale_days} 天未被修改，可能已经废弃",
            target=stale[0].path,
            condition=f"单文件距最后一次提交 ≥ {stale_days} 天",
            actual=f"{len(stale)} 个文件（最久 {stale[0].days_since_change} 天）",
            threshold=f"{stale_days} 天",
            action="确认是否废弃：废弃则删除，仍在使用则补测试并写进 README",
        ))
    if large:
        warnings.append(Warning(
            rule="大文件入库",
            severity="medium",
            message=f"{len(large)} 个文件超过 {large_file_mb}MB，仓库体积会持续膨胀",
            target=large[0].path,
            condition=f"单文件大小 ≥ {large_file_mb}MB",
            actual=f"{len(large)} 个文件（最大 {large[0].size_bytes / 1048576:.1f}MB）",
            threshold=f"{large_file_mb} MB",
            action="移出仓库或改用 Git LFS，并在 .gitignore 里加规则",
        ))
    if hotspots and hotspots[0].change_count >= max(hotspot_changes * 2, 20):
        warnings.append(Warning(
            rule="热点文件过度修改",
            severity="low",
            message=f"{hotspots[0].path} 被修改 {hotspots[0].change_count} 次，是重构候选",
            target=hotspots[0].path,
            condition=f"单文件修改次数 ≥ {hotspot_changes} 次",
            actual=f"{hotspots[0].change_count} 次",
            threshold=f"{hotspot_changes} 次",
            action="拆分职责或补测试后再改，避免每次改动都波及全局",
        ))
    if hygiene.pass_rate >= 0 and hygiene.pass_rate < 0.6:
        warnings.append(Warning(
            rule="提交信息不规范",
            severity="low",
            message=f"只有 {hygiene.pass_rate:.0%} 的提交符合约定格式",
            target="git log",
            condition="符合 pattern 的提交占比 < 60%",
            actual=f"{hygiene.pass_rate:.0%}（{hygiene.passed}/{hygiene.total}）",
            threshold="60%",
            action="用 commit-msg hook 或模板约束，历史提交不必追改",
        ))

    # -- 健康度 --------------------------------------------------------
    penalty = {"high": 12, "medium": 6, "low": 3}
    health = 100.0
    for warning in warnings:
        health -= penalty.get(warning.severity, 3)
    health = round(max(0.0, min(100.0, health)), 1)

    return MockView(
        snapshot=snapshot,
        health_score=health,
        total_commits=len(commits),
        author_count=len(per_author),
        file_count=len(files),
        commit_calendar=dict(calendar),
        author_stats=author_stats,
        hotspot_files=hotspots,
        large_files=large,
        stale_files=stale,
        warnings=warnings,
        commit_hygiene=hygiene,
        risk_level=risk_of(health),
    )


# --------------------------------------------------------------------------
# 合成数据（仓库读不通时的兜底，也用于 GUI 单元测试）
# --------------------------------------------------------------------------
def _synthetic_snapshot(repo_path: str = "demo/repo") -> RepositorySnapshot:
    random.seed(20261124)
    authors = [("Chen Wei", "chen@example.com"), ("Lin Tao", "lin@example.com"),
               ("Wang Yu", "wang@example.com"), ("Huang Jionghua", "hjh@example.com")]
    paths = ["models.py", "git_reader.py", "metrics.py", "rules.py", "gui/main_window.py",
             "gui/dashboard.py", "gui/trends.py", "reporters.py", "cli.py", "README.md",
             "docs/design.md", "assets/logo.png"]

    today = datetime.now()
    commits: list[Commit] = []
    # 权重刻意做成"一人挑大头"：这是学生小组仓库最常见的形态，
    # 也是"单一作者依赖"这条 high 规则要被触发的原因。四人平均分配的仓库反而少见。
    weights = [10, 2, 1, 1]
    for index in range(160):
        name, email = random.choices(authors, weights=weights, k=1)[0]
        when = today - timedelta(days=random.randint(0, 170), hours=random.randint(0, 20))
        touched = tuple(random.sample(paths, k=random.randint(1, 4)))
        commits.append(Commit(
            hash=f"{index:040x}",
            author_name=name,
            author_email=email,
            authored_at=when,
            message=random.choice(["feat: add dashboard", "fix: handle empty repo",
                                   "docs: update readme", "wip", "refactor parser"]),
            files_changed=touched,
            insertions=random.randint(5, 220),
            deletions=random.randint(0, 90),
        ))
    commits.sort(key=lambda c: c.authored_at)

    files = tuple(
        FileRecord(
            path=path,
            size_bytes=random.randint(2_000, 18_000_000),
            file_type=path.rsplit(".", 1)[-1],
            modified_at=today - timedelta(days=random.randint(0, 260)),
        )
        for path in paths
    )
    return RepositorySnapshot(
        repo_path=repo_path,
        repo_name="demo-repo",
        commits=tuple(commits),
        files=files,
        branches=("main", "feature/gui"),
        tags=("v0.1.0",),
        scanned_at=today,
    )
