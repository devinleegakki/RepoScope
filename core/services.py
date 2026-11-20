"""Coordinate repository validation, analysis, progress, and batch execution.

This service is shared by the GUI and CLI. Presentation layers should use it
instead of invoking Git or metric functions directly.

Notes"Notes"）：

* **Notes**：``AnalysisService.analyze()`` analysis
  GUI Notes ``gui/worker.py``、Notes ``main.py analyze``、analysis
  ``BatchAnalyzer`` Notes"CLI Notes GUI analysis"。
* **configuration**：``AnalysisConfig`` commits
  Notes JSON files
* **error**：analysis ``ThreadPoolExecutor`` repository
  repository
* **cancel**：Notes ``cancel_event``（``threading.Event``）cancel
  commits"cancel"。

Notes``_select_engine()``。

* TYB Notes ``metrics.py`` Notes
* Notes ``gui/mock_data.py`` Notes``TEMP`` Notes
  Notes CLI Notes
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

# --- configuration ------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisConfig:
    """analysis

    Notes `README` rulesGUI Notes"configuration"Notes
    ``--stale-days`` settingsJSON files
    """

    stale_days: int = 180
    large_file_mb: int = 10
    hotspot_changes: int = 10
    release_stale_days: int = 365
    single_maintainer_ratio: float = 0.70
    window_days: int = 0            # 0 = Notes30 / 90 / 365
    commit_pattern: str = DEFAULT_COMMIT_PATTERN
    max_function_lines: int = 80
    max_file_lines: int = 500
    min_test_ratio: float = 0.05
    ownership_ratio: float = 0.80
    enable_dependency_scan: bool = True
    enable_secret_scan: bool = True

    def validate(self) -> None:
        """Notes Git error"""
        if self.stale_days <= 0:
            raise ValueError("stale_days must be greater than zero")
        if self.large_file_mb <= 0:
            raise ValueError("large_file_mb must be greater than zero")
        if self.hotspot_changes <= 0:
            raise ValueError("hotspot_changes must be greater than zero")
        if self.release_stale_days <= 0:
            raise ValueError("release_stale_days must be greater than zero")
        if not 0 < self.single_maintainer_ratio <= 1:
            raise ValueError("single_maintainer_ratio must be in the range (0, 1]")
        if self.window_days < 0:
            raise ValueError("window_days must be zero or greater")
        if self.max_function_lines < 0 or self.max_file_lines < 0:
            raise ValueError("size")
        if not 0 <= self.min_test_ratio <= 1 or not 0 <= self.ownership_ratio <= 1:
            raise ValueError("test_ratio must be between 0 and 1")
        if self.commit_pattern:
            import re

            try:
                re.compile(self.commit_pattern)
            except re.error as exc:
                raise ValueError(f"commit_pattern valid{exc}") from exc

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "AnalysisConfig":
        """Notes JSON configuration"""
        if not isinstance(data, Mapping):
            raise ValueError("configuration JSON Notes")
        known = {f for f in cls.__dataclass_fields__}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"configuration{', '.join(unknown)}")
        config = cls(**{key: data[key] for key in known if key in data})
        config.validate()
        return config

    @classmethod
    def from_json(cls, path: str | Path) -> "AnalysisConfig":
        raw = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"files JSON：{path}（{exc}）") from exc
        return cls.from_dict(data)

    def save_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return target


DEFAULT_CONFIG = AnalysisConfig()

# --- Notes ------------------------------------------------------------------


class AnalysisError(RuntimeError):
    """Notes ``code`` analysisCLI error"""

    def __init__(self, code: str, message: str, *, details: Optional[str] = None) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - Notes
        return self.message


# --- Notes ------------------------------------------------------------------


def _noop(percent: int, message: str) -> None:  # pragma: no cover - Notes
    pass


@dataclass(frozen=True)
class RepoCheck:
    """``check`` repository"""

    path: str
    repo_name: str
    commits: int
    files: int
    branches: tuple[str, ...]
    tags: tuple[str, ...]


class AnalysisService:
    """repository ``AnalysisService().analyze(path)``。

    ``allow_synthetic``：
        * GUI Notes ``True`` —— error
        * CLI Notes ``False``（default report
    """

    def __init__(self, *, allow_synthetic: bool = False) -> None:
        self.allow_synthetic = allow_synthetic

    # -- repository ----------------------------------------------------------
    def check(self, repo_path: str | Path) -> RepoCheck:
        """repository"""
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
        """repository ``AnalysisView`` Notes"""
        config = config or DEFAULT_CONFIG
        config.validate()
        report = on_progress or _noop
        started = time.monotonic()

        if self.allow_synthetic:
            return self._analyze_with_fallback(repo_path, config, report)

        report(5, "Loading repository")
        snapshot = self._snapshot(self._reader(repo_path))
        snapshot = self._apply_window(snapshot, config)
        report(60, "Collecting repository metrics")
        view = self._compute(snapshot, config, report)
        view.elapsed_seconds = time.monotonic() - started
        report(100, "complete")
        return view

    # -- Notes ------------------------------------------------------------
    @staticmethod
    def _apply_window(snapshot, config: AnalysisConfig):
        """``window_days > 0`` commits"time"settings"""
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
            raise AnalysisError("io_error", f"repository{exc}") from exc

    def _analyze_with_fallback(
        self, repo_path: str | Path, config: AnalysisConfig, report: ProgressCallback
    ) -> AnalysisView:
        """GUI path"""
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
        """path TYB Notes metrics.py，Notes

        Notes —— metrics.py Notes ``_select_engine``
        Notes``analyze()`` Notes
        """
        try:
            from reposcope.metrics import compute_metrics
            from reposcope.rules import detect_all
            from gui.contract import adapt
            metrics = compute_metrics(snapshot, _analysis_config(config))
            metrics.warnings = detect_all(metrics, _analysis_config(config)) if hasattr(metrics, "warnings") else detect_all(metrics, _analysis_config(config))
            view = adapt(metrics, snapshot)
            report(90, "analysis")
            return view
        except (ImportError, TypeError, ValueError) as exc:
            report(70, f"Analysis fallback: {exc}")

        from gui.mock_data import _compute as legacy_compute  # TEMP NotesTYB remove

        report(80, "Computing repository metrics")
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
    """Notes ``fn(snapshot, config) -> AnalysisResult``，none ``None``。

    Notes``metrics.analyse(snapshot, config)``。TYB Notes
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


# --- analysis ---------------------------------------------------------------


@dataclass
class BatchResult:
    """repository"""

    path: str
    repo_name: str = ""
    ok: bool = False
    view: AnalysisView | None = None
    error: str = ""
    cancelled: bool = False
    elapsed_seconds: float = 0.0


def summarize_view(view: AnalysisView) -> RepoSummary:
    """repository"""
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
    """repository"""

    def __init__(self, *, max_workers: int = 4, service: AnalysisService | None = None) -> None:
        if max_workers < 1:
            raise ValueError("max_workers Notes 1")
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
        """Notes

        ``on_progress(result, done, total)`` repository
        CLI NotesGUI Notes
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
                    result = future.result()  # _run_one Notes
                    results[index] = result
                    done += 1
                    notify(result, done, total)

            # repository
            while next_index < total:
                results[next_index] = BatchResult(
                    path=paths[next_index], cancelled=True, error="cancel"
                )
                next_index += 1
        finally:
            # cancelwait=True Notes
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
        except Exception as exc:  # repository
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




