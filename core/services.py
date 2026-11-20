"""统一分析服务层：GUI 与 CLI 共用的唯一分析入口。

设计约定（对应组长文档"应用服务层"）：

* **一个入口**：``AnalysisService.analyze()`` 是所有分析请求的唯一通道。
  GUI 的 ``gui/worker.py``、命令行的 ``main.py analyze``、批量分析
  ``BatchAnalyzer`` 都调它，保证"CLI 与 GUI 使用同一分析服务"。
* **一个配置**：``AnalysisConfig`` 承载阈值、时间窗口和提交规范正则，
  可以从 JSON 配置文件加载，命令行参数在它之上覆盖。
* **失败隔离**：批量分析用 ``ThreadPoolExecutor`` 并发跑多个仓库，
  单个仓库失败只写进该仓库的结果，绝不中断其它任务。
* **可取消**：传入 ``cancel_event``（``threading.Event``）后，取消时不再
  提交新任务，已提交的任务照常收尾，未开始的任务标记为"已取消"。

数据来源的替换点只有一个：``_select_engine()``。

* TYB 的 ``metrics.py`` 落地后，这里自动切到真实统计；
* 在此之前退回 ``gui/mock_data.py`` 里的临时统计（``TEMP`` 段），
  保证 CLI 现在就可用、可演示，替换时不改调用方。
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from gui.contract import AnalysisView, RepoSummary, risk_of

ProgressCallback = Callable[[int, str], None]

DEFAULT_COMMIT_PATTERN = r"^(feat|fix|docs|refactor|test|chore)(\(.+\))?: "

# --- 配置 ------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisConfig:
    """一次分析的全部可调参数。

    字段名与 `README` 里的默认规则一致；GUI 的"分析配置"页、命令行的
    ``--stale-days`` 等参数、JSON 配置文件最终都归一到这个类。
    """

    stale_days: int = 180
    large_file_mb: int = 10
    hotspot_changes: int = 10
    release_stale_days: int = 365
    single_maintainer_ratio: float = 0.70
    window_days: int = 0            # 0 = 全部历史；30 / 90 / 365
    commit_pattern: str = DEFAULT_COMMIT_PATTERN
    max_function_lines: int = 80
    max_file_lines: int = 500
    min_test_ratio: float = 0.05
    ownership_ratio: float = 0.80
    enable_dependency_scan: bool = True
    enable_secret_scan: bool = True

    def validate(self) -> None:
        """在真正读 Git 之前把明显错误的参数挡掉，错误信息直接给人看。"""
        if self.stale_days <= 0:
            raise ValueError("stale_days 必须是正整数")
        if self.large_file_mb <= 0:
            raise ValueError("large_file_mb 必须是正整数")
        if self.hotspot_changes <= 0:
            raise ValueError("hotspot_changes 必须是正整数")
        if self.release_stale_days <= 0:
            raise ValueError("release_stale_days 必须是正整数")
        if not 0 < self.single_maintainer_ratio <= 1:
            raise ValueError("single_maintainer_ratio 必须落在 (0, 1] 区间")
        if self.window_days < 0:
            raise ValueError("window_days 不能是负数")
        if self.max_function_lines < 0 or self.max_file_lines < 0:
            raise ValueError("代码规模阈值不能是负数")
        if not 0 <= self.min_test_ratio <= 1 or not 0 <= self.ownership_ratio <= 1:
            raise ValueError("代码质量比例阈值必须在 [0, 1] 区间")
        if self.commit_pattern:
            import re

            try:
                re.compile(self.commit_pattern)
            except re.error as exc:
                raise ValueError(f"commit_pattern 不是合法正则：{exc}") from exc

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AnalysisConfig":
        """从 JSON 字典构造配置；未知字段明确报错，避免拼错的键被静默忽略。"""
        if not isinstance(data, Mapping):
            raise ValueError("配置必须是 JSON 对象")
        known = {f for f in cls.__dataclass_fields__}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"配置里有未知字段：{', '.join(unknown)}")
        config = cls(**{key: data[key] for key in known if key in data})
        config.validate()
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> "AnalysisConfig":
        raw = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"配置文件不是合法 JSON：{path}（{exc}）") from exc
        return cls.from_dict(data)

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return target


DEFAULT_CONFIG = AnalysisConfig()

# --- 异常 ------------------------------------------------------------------


class AnalysisError(RuntimeError):
    """带机器可读 ``code`` 的分析失败，CLI 据此给出可读错误而不是堆栈。"""

    def __init__(self, code: str, message: str, *, details: Optional[str] = None) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - 简单委托
        return self.message


# --- 服务 ------------------------------------------------------------------


def _noop(percent: int, message: str) -> None:  # pragma: no cover - 占位
    pass


@dataclass(frozen=True)
class RepoCheck:
    """``check`` 子命令的输出：仓库可以直接拿去分析时它才成立。"""

    path: str
    repo_name: str
    commits: int
    files: int
    branches: tuple[str, ...]
    tags: tuple[str, ...]


class AnalysisService:
    """要分析一个仓库，只需要 ``AnalysisService().analyze(path)``。

    ``allow_synthetic``：
        * GUI 用 ``True`` —— 读取失败时退回内置演示数据，界面永不白屏；
        * CLI 用 ``False``（默认）—— 读取失败就报错，绝不生成假报告。
    """

    def __init__(self, *, allow_synthetic: bool = False) -> None:
        self.allow_synthetic = allow_synthetic

    # -- 单仓库 ----------------------------------------------------------
    def check(self, repo_path: str | Path) -> RepoCheck:
        """校验仓库是否可分析，并返回基础信息（不写入任何文件）。"""
        reader = self._reader(repo_path)
        snapshot = self._snapshot(reader)
        return RepoCheck(
            path=snapshot.repo_path,
            repo_name=snapshot.repo_name,
            commits=len(snapshot.commits),
            files=len(snapshot.files),
            branches=tuple(snapshot.branches),
            tags=tuple(snapshot.tags),
        )

    def analyze(
        self,
        repo_path: str | Path,
        config: AnalysisConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AnalysisView:
        """分析一个仓库，返回满足 ``AnalysisView`` 契约的结果。"""
        config = config or DEFAULT_CONFIG
        config.validate()
        report = on_progress or _noop
        started = time.monotonic()

        if self.allow_synthetic:
            return self._analyze_with_fallback(repo_path, config, report)

        report(5, "校验仓库")
        snapshot = self._snapshot(self._reader(repo_path))
        snapshot = self._apply_window(snapshot, config)
        report(60, "统计指标")
        view = self._compute(snapshot, config, report)
        view.elapsed_seconds = time.monotonic() - started
        report(100, "完成")
        return view

    # -- 内部 ------------------------------------------------------------
    @staticmethod
    def _apply_window(snapshot, config: AnalysisConfig):
        """``window_days > 0`` 时只保留窗口内的提交（配置里的"时间范围"参数）。"""
        if config.window_days <= 0 or not snapshot.commits:
            return snapshot
        from dataclasses import replace
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=config.window_days)

        def aware(value):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

        commits = tuple(
            commit for commit in snapshot.commits if aware(commit.authored_at) >= cutoff
        )
        return replace(snapshot, commits=commits)
    @staticmethod
    def _reader(repo_path: str | Path):
        from core.git_reader import GitReader

        return GitReader(repo_path)

    @staticmethod
    def _snapshot(reader):
        from core.git_reader import GitReaderError

        try:
            return reader.read_snapshot()
        except GitReaderError as exc:
            raise AnalysisError(exc.code, exc.details or str(exc)) from exc
        except OSError as exc:
            raise AnalysisError("io_error", f"读取仓库失败：{exc}") from exc

    def _analyze_with_fallback(
        self, repo_path: str | Path, config: AnalysisConfig, report: ProgressCallback
    ) -> AnalysisView:
        """GUI 路径：失败时退回演示数据，保证界面有内容可显示。"""
        from gui import mock_data

        return mock_data.build(
            str(repo_path),
            on_progress=report,
            stale_days=config.stale_days,
            large_file_mb=config.large_file_mb,
            hotspot_changes=config.hotspot_changes,
            commit_pattern=config.commit_pattern,
        )

    def _compute(self, snapshot, config: AnalysisConfig, report: ProgressCallback) -> AnalysisView:
        """真实数据路径：优先 TYB 的 metrics.py，未就绪时用临时统计。

        替换点全部收敛在这里 —— metrics.py 落地后，把下面 ``_select_engine``
        返回的函数换掉即可，``analyze()`` 的调用方一行不动。
        """
        try:
            from reposcope.metrics import compute_metrics
            from reposcope.rules import detect_all
            from gui.contract import adapt
            metrics = compute_metrics(snapshot, _analysis_config(config))
            metrics.warnings = detect_all(metrics, _analysis_config(config)) if hasattr(metrics, "warnings") else detect_all(metrics, _analysis_config(config))
            view = adapt(metrics, snapshot)
            report(90, "静态质量、协作与安全分析")
            return view
        except (ImportError, TypeError, ValueError) as exc:
            report(70, f"高级分析不可用，使用兼容统计：{exc}")

        from gui.mock_data import _compute as legacy_compute  # TEMP 段，TYB 到位后删除

        report(80, "临时统计（等待 metrics.py）")
        return legacy_compute(
            snapshot,
            stale_days=config.stale_days,
            large_file_mb=config.large_file_mb,
            hotspot_changes=config.hotspot_changes,
            commit_pattern=config.commit_pattern,
        )


def _analysis_config(config: AnalysisConfig):
    from reposcope.models_analysis import AnalysisConfig as CoreConfig
    return CoreConfig(stale_days=config.stale_days, large_file_mb=config.large_file_mb,
                      hotspot_changes=config.hotspot_changes, release_stale_days=config.release_stale_days,
                      single_maintainer_ratio=config.single_maintainer_ratio,
                      recent_days=config.window_days or 90, observation_days=config.window_days or 90,
                      commit_message_pattern=config.commit_pattern,
                      max_function_lines=config.max_function_lines,
                      max_file_lines=config.max_file_lines,
                      min_test_ratio=config.min_test_ratio,
                      ownership_ratio=config.ownership_ratio,
                      enable_dependency_scan=config.enable_dependency_scan,
                      enable_secret_scan=config.enable_secret_scan)


def _select_engine():
    """返回 ``fn(snapshot, config) -> AnalysisResult``，没有就返回 ``None``。

    只认一个约定：``metrics.analyse(snapshot, config)``。TYB 落地后在这里接上就行。
    """
    try:
        import metrics as metrics_module  # type: ignore
    except ImportError:
        return None
    for name in ("analyse", "analyze"):
        candidate = getattr(metrics_module, name, None)
        if callable(candidate):
            return candidate
    return None


# --- 批量分析 ---------------------------------------------------------------


@dataclass
class BatchResult:
    """多仓库分析里一个仓库的结局。失败也留下来，方便在汇总表里交代。"""

    path: str
    repo_name: str = ""
    ok: bool = False
    view: AnalysisView | None = None
    error: str = ""
    cancelled: bool = False
    elapsed_seconds: float = 0.0


def summarize_view(view: AnalysisView) -> RepoSummary:
    """把一次分析压成多仓库对比表的一行。"""
    return RepoSummary(
        repo_name=view.snapshot.repo_name,
        path=view.snapshot.repo_path,
        commits=view.total_commits,
        authors=view.author_count,
        health_score=view.health_score,
        hotspot_count=len(view.hotspot_files),
        stale_count=len(view.stale_files),
        risk_level=view.risk_level or risk_of(view.health_score),
    )


class BatchAnalyzer:
    """用线程池并发分析多个仓库：单个失败不影响其它，支持进度与取消。"""

    def __init__(self, *, max_workers: int = 4, service: AnalysisService | None = None) -> None:
        if max_workers < 1:
            raise ValueError("max_workers 至少为 1")
        self.max_workers = max_workers
        self.service = service or AnalysisService(allow_synthetic=False)

    def run(
        self,
        repo_paths: Sequence[str | Path],
        config: AnalysisConfig | None = None,
        *,
        on_progress: Callable[[BatchResult, int, int], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[BatchResult]:
        """跑完整批，返回与输入顺序一致的结果列表。

        ``on_progress(result, done, total)`` 每完成一个仓库回调一次，
        CLI 用它打印进度、GUI 批量页可以拿它刷进度条。
        """
        config = config or DEFAULT_CONFIG
        config.validate()
        paths = [str(p) for p in repo_paths]
        total = len(paths)
        results: dict[int, BatchResult] = {}
        notify = on_progress or (lambda result, done, total: None)

        def is_cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        next_index = 0
        done = 0
        pending: dict = {}

        pool = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="reposcope-batch")
        try:
            while next_index < total or pending:
                while len(pending) < self.max_workers and next_index < total and not is_cancelled():
                    index = next_index
                    next_index += 1
                    pending[pool.submit(self._run_one, paths[index], config)] = index

                if not pending:
                    break

                finished, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                for future in finished:
                    index = pending.pop(future)
                    result = future.result()  # _run_one 从不抛异常
                    results[index] = result
                    done += 1
                    notify(result, done, total)

            # 取消后没来得及提交的仓库：显式标记，别让汇总表里凭空少几行
            while next_index < total:
                results[next_index] = BatchResult(
                    path=paths[next_index], cancelled=True, error="已取消"
                )
                next_index += 1
        finally:
            # 取消时不让排队中的任务继续跑；wait=True 保证线程收尾干净
            pool.shutdown(wait=True, cancel_futures=True)

        return [results[i] for i in range(total)]

    def _run_one(self, path: str, config: AnalysisConfig) -> BatchResult:
        started = time.monotonic()
        try:
            view = self.service.analyze(path, config)
        except AnalysisError as exc:
            return BatchResult(
                path=path,
                repo_name=Path(path).name,
                ok=False,
                error=f"{exc.code}: {exc.message}",
                elapsed_seconds=time.monotonic() - started,
            )
        except Exception as exc:  # 兜底：任何仓库的任何异常都不许掀翻整批
            return BatchResult(
                path=path,
                repo_name=Path(path).name,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                elapsed_seconds=time.monotonic() - started,
            )
        return BatchResult(
            path=path,
            repo_name=view.snapshot.repo_name,
            ok=True,
            view=view,
            elapsed_seconds=time.monotonic() - started,
        )

