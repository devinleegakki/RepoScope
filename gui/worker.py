"""analysis worker。

Qt Notes ``moveToThread`` Notes
error

analysis ``services.AnalysisService``（Notes
``allow_synthetic=True`` error
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.services import AnalysisConfig, AnalysisService

from .contract import AnalysisRequest


class AnalysisWorker(QObject):
    """analysis"""

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, request: AnalysisRequest) -> None:
        super().__init__()
        self._request = request

    def run(self) -> None:
        try:
            config = AnalysisConfig(
                stale_days=self._request.stale_days,
                large_file_mb=self._request.large_file_mb,
                hotspot_changes=self._request.hotspot_changes,
                release_stale_days=self._request.release_stale_days,
                single_maintainer_ratio=self._request.single_maintainer_ratio,
                window_days=self._request.window_days,
                commit_pattern=self._request.commit_pattern,
                max_function_lines=self._request.max_function_lines,
                max_file_lines=self._request.max_file_lines,
                min_test_ratio=self._request.min_test_ratio,
                ownership_ratio=self._request.ownership_ratio,
                enable_dependency_scan=self._request.enable_dependency_scan,
                enable_secret_scan=self._request.enable_secret_scan,
            )
            service = AnalysisService(allow_synthetic=True)
            view = service.analyze(
                self._request.repo_path,
                config,
                on_progress=lambda percent, message: self.progress.emit(percent, message),
            )
        except Exception as exc:  # Notes
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.finished.emit(view)




