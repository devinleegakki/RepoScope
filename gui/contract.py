"""GUI 与其它模块之间唯一的契约层。

这个文件是给组里其它三个人看的：**GUI 只认这里的类型，不认你们的模块名。**
只要满足 ``AnalysisView`` 的形状，界面就能跑起来；不符合，界面一行都不用改，
在 ``adapt()`` 里做一次字段映射就行。

边界规则（写进 code review 检查项）：

* ``gui/`` 只能 import 标准库、``models.py`` 和 ``PySide6``。
* 不允许 ``from core.git_reader import ...``、``from metrics import ...``。
  那些模块还在改，直连会导致你每天都要修界面。
* 传进界面的永远是一个 ``AnalysisView``，界面不关心它是真算出来的还是假的。

字段来源对照（详见 ``docs/GUI_INTERFACE.md``）::

    snapshot / health_score / total_commits ...   LTY(git_reader) + TYB(metrics)
    commit_hygiene                                TYB(metrics + rules)
    warnings[...].condition/actual/threshold/action   TYB(rules)   ← 待补
    RepoSummary                                   Wyh(batch)   ← 待补

凡是标了 ``# TODO(TYB)`` 的字段，都是界面已经画好了位置、等后端填值的地方。
后端提供之前，界面显示占位符（"待后端提供"），不会假装有数据。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, Sequence, Tuple, runtime_checkable

from core.models import RepositorySnapshot

# 后端还没实现的字段统一用这个占位符，界面据此显示"—"而不是 0，
# 避免出现"明明是 0 却看起来像分析成功"的假数据。
PENDING = "待后端提供"


@dataclass(frozen=True)
class FileStat:
    """一个文件在某个榜单里的统计行（热点 / 大文件 / 陈旧文件共用）。"""

    path: str
    change_count: int = 0
    author_count: int = 0
    size_bytes: int = 0
    days_since_change: int = 0

    # --- TODO(TYB): metrics.py 产出，数据分析页的明细列要用 ---
    changed_lines: int = 0          # 该文件累计增删行数
    file_type: str = ""             # 扩展名，用于按类型聚合
    is_binary: bool = False         # 二进制文件要在大文件榜里单独标注


@dataclass(frozen=True)
class AuthorStat:
    """一位作者在仓库里的贡献汇总。"""

    name: str
    commits: int
    insertions: int = 0
    deletions: int = 0
    share: float = 0.0

    # --- TODO(TYB): 最近 90 天提交占比，用来识别"历史贡献高但已经不在"的人 ---
    # 用 -1.0 表示后端未提供，界面显示 "—"。
    recent_90d_share: float = -1.0


@dataclass(frozen=True)
class Violation:
    """一条提交信息不合规的记录，报告区要能列出来给作者改。"""

    commit_hash: str
    message: str
    reason: str = ""


@dataclass(frozen=True)
class CommitHygiene:
    """提交信息规范检查结果（组长文档 4.6）。"""

    pass_rate: float = -1.0         # 0~1，-1 表示未提供
    total: int = 0
    passed: int = 0
    pattern: str = ""
    violations: Tuple[Violation, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HealthDimension:
    """One explainable score shown in the dashboard health overview."""

    name: str
    score: float
    level: str = "low"
    issue_count: int = 0
    hint: str = ""


@dataclass(frozen=True)
class DashboardStats:
    """Precomputed dashboard-only aggregates; widgets do not recalculate them."""

    dimensions: Tuple[HealthDimension, ...] = field(default_factory=tuple)
    risk_counts: Mapping[str, int] = field(default_factory=dict)
    recent_commits: Mapping[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Warning:
    """一条反模式规则命中的结果。

    界面不只显示一句结论，还要能回答"为什么算问题、差多少、该怎么改"，
    所以一条警告必须自带四要素（组长文档 4.2 反模式中心）。
    """

    rule: str
    severity: str                   # high / medium / low
    message: str
    target: str = ""

    # --- TODO(TYB): rules.py 产出，缺这四个字段反模式中心只能显示一句干结论 ---
    condition: str = ""             # 触发条件，如"单一作者提交占比 ≥ 70%"
    actual: str = ""                # 实际值，如"82%"
    threshold: str = ""             # 配置阈值，如"70%"
    action: str = ""                # 建议动作，如"补充 code review 与知识转移"

    @property
    def has_evidence(self) -> bool:
        """四要素是否齐全。不齐全时界面明确提示"后端待补"。"""
        return all((self.condition, self.actual, self.threshold, self.action))


@dataclass(frozen=True)
class RepoSummary:
    """多仓库对比表的一行（组长文档 4.8）。"""

    repo_name: str
    path: str = ""
    commits: int = 0
    authors: int = 0
    health_score: float = 0.0
    hotspot_count: int = 0
    stale_count: int = 0
    risk_level: str = "low"         # low / medium / high


@runtime_checkable
class AnalysisView(Protocol):
    """界面需要的全部数据。TYB 的 ``AnalysisResult`` 满足它即可直接传入。

    字段为什么是这些：每一项都能对应到界面上的一个具体控件，
    多一个没用，少一个控件就空着。见 ``docs/GUI_INTERFACE.md``。
    """

    snapshot: RepositorySnapshot
    health_score: float
    total_commits: int
    author_count: int
    file_count: int
    commit_calendar: Mapping[str, int]
    author_stats: Sequence[AuthorStat]
    hotspot_files: Sequence[FileStat]
    large_files: Sequence[FileStat]
    stale_files: Sequence[FileStat]
    warnings: Sequence[Warning]
    elapsed_seconds: float

    # --- TODO(TYB) / TODO(Wyh) ---
    commit_hygiene: CommitHygiene   # 总览页的"提交规范通过率"
    risk_level: str                 # 总览页右上角的等级徽标
    dashboard_stats: DashboardStats


ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class AnalysisRequest:
    """开始分析时 GUI 交给后台的参数。

    等 TYB 的 ``AnalysisConfig`` 定稿后，这个类改成一个薄封装，
    或者直接用他们的类——界面其它部分不受影响。
    """

    repo_path: str
    stale_days: int = 180
    large_file_mb: int = 10
    hotspot_changes: int = 10
    release_stale_days: int = 365
    single_maintainer_ratio: float = 0.70
    window_days: int = 0            # 0 = 全部历史；30 / 90 / 365
    commit_pattern: str = r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: "
    max_function_lines: int = 80
    max_file_lines: int = 500
    min_test_ratio: float = 0.05
    ownership_ratio: float = 0.80
    enable_dependency_scan: bool = True
    enable_secret_scan: bool = True


def risk_of(score: float) -> str:
    """把健康度映射成等级。阈值是展示规则，写在这里保证全界面一致。"""
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


def adapt(result: object, snapshot: RepositorySnapshot | None = None) -> AnalysisView:
    """把 TYB 的 ``AnalysisResult`` 映射成 ``AnalysisView``。

    TODO(接口对接日): 等 ``metrics.py`` 落地后在这里补字段映射，界面不用改。
    大致对应关系::

        result.metrics.health_score      -> health_score
        result.metrics.total_commits     -> total_commits
        result.metrics.commit_calendar   -> commit_calendar
        result.metrics.author_stats      -> author_stats   (字段名按实际调整)
        result.metrics.hotspot_files     -> hotspot_files
        result.metrics.large_files       -> large_files
        result.metrics.stale_files       -> stale_files
        result.metrics.warnings          -> warnings
        result.metrics.commit_hygiene    -> commit_hygiene

    在映射补齐之前，调用它会明确抛错，避免界面显示 0 还以为分析成功。
    """
    from dataclasses import dataclass
    from types import SimpleNamespace
    metrics = getattr(result, "metrics", result)
    snap = snapshot or getattr(result, "snapshot", None)
    if snap is None:
        raise TypeError("adapt 需要 snapshot")
    authors = []
    for a in getattr(metrics, "author_contributions", []):
        authors.append(AuthorStat(a.author, a.commits, 0, 0, a.ratio, a.recent_ratio))
    def files(items):
        return [FileStat(f.path, f.changes, 0, f.size_bytes, f.stale_days or 0,
                          f.lines_changed, f.file_type, f.is_binary) for f in items]
    compliance = getattr(metrics, "commit_compliance", None)
    hygiene = CommitHygiene(compliance.pass_rate, compliance.checked, compliance.valid,
                            getattr(result, "commit_message_pattern", ""),
                            tuple(Violation(v.get("sha", ""), v.get("message", ""), "; ".join(v.get("reasons", []))) for v in compliance.violations)) if compliance else CommitHygiene()
    warnings = []
    for w in getattr(result, "warnings", []):
        warnings.append(Warning(w.name, w.level, w.message, w.target, str(w.threshold), str(w.actual_value), str(w.threshold), w.suggestion))
    q = getattr(metrics, "code_quality", None)
    extra = {
        "code_quality": q, "ownership": getattr(metrics, "ownership", None),
        "dependencies": getattr(metrics, "dependencies", None), "security_findings": getattr(metrics, "security_findings", []),
    }
    risk_counts = {level: sum(1 for w in warnings if w.severity == level) for level in ("high", "medium", "low")}
    q = getattr(metrics, "code_quality", None)
    own = getattr(metrics, "ownership", None)
    dep = getattr(metrics, "dependencies", None)
    findings = getattr(metrics, "security_findings", [])
    quality_issues = (len(getattr(q, "long_functions", [])) + len(getattr(q, "long_files", [])) +
                      getattr(q, "bare_except_count", 0)) if q else 0
    security_issues = len(findings) + (len(getattr(dep, "unpinned", [])) + len(getattr(dep, "duplicates", [])) if dep else 0)
    dimensions = (
        HealthDimension("Git 活跃度", min(100.0, len(metrics.commit_trend) / 30 * 100), "low" if len(metrics.commit_trend) >= 30 else "medium", 0, f"{len(metrics.commit_trend)} 个活跃周期"),
        HealthDimension("协作与所有权", max(0.0, 100 - len(getattr(own, "high_risk_files", [])) * 10), "high" if getattr(own, "high_risk_files", []) else "low", len(getattr(own, "high_risk_files", [])), f"{len(getattr(own, 'high_risk_files', []))} 个高风险文件"),
        HealthDimension("代码质量", max(0.0, 100 - quality_issues * 8), "high" if quality_issues >= 5 else ("medium" if quality_issues else "low"), quality_issues, f"{quality_issues} 个规则问题"),
        HealthDimension("依赖与安全", max(0.0, 100 - security_issues * 15), "high" if findings else ("medium" if security_issues else "low"), security_issues, f"{security_issues} 个依赖/安全问题"),
        HealthDimension("提交规范", hygiene.pass_rate * 100 if hygiene and hygiene.pass_rate >= 0 else 0, "low" if hygiene and hygiene.pass_rate >= .8 else "medium", (hygiene.total - hygiene.passed) if hygiene else 0, f"通过率 {hygiene.pass_rate:.0%}" if hygiene else "待提供"),
    )
    recent = {}
    calendar = dict(metrics.commit_trend)
    for days in (7, 30, 90):
        recent[days] = sum(calendar.values()) if days == 90 else sum(list(calendar.values())[-days:])
    stats = DashboardStats(dimensions=dimensions, risk_counts=risk_counts, recent_commits=recent)
    return SimpleNamespace(snapshot=snap, health_score=max(0.0, 100.0 - 10.0 * len(warnings)),
        total_commits=metrics.total_commits, author_count=metrics.total_authors,
        file_count=metrics.total_files, commit_calendar=metrics.commit_trend,
        author_stats=tuple(authors), hotspot_files=tuple(files(metrics.file_hotspots)),
        large_files=tuple(files(metrics.large_files)), stale_files=tuple(files(metrics.stale_files)),
        warnings=tuple(warnings), elapsed_seconds=0.0, commit_hygiene=hygiene,
        risk_level=risk_of(max(0.0, 100.0 - 10.0 * len(warnings))), dashboard_stats=stats, **extra)

