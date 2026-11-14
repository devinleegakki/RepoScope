"""后台分析线程的 worker。

Qt 铁律：控件只能在主线程里碰。所以这个对象被 ``moveToThread`` 挪到子线程后，
唯一的对外通道就是三个信号：进度、完成、失败。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from . import mock_data
from .contract import AnalysisRequest


class AnalysisWorker(QObject):
    """在子线程里跑一次分析，并只通过信号回主线程。"""

    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, request: AnalysisRequest) -> None:
        super().__init__()
        self._request = request

    def run(self) -> None:
        try:
            view = mock_data.build(
                self._request.repo_path,
                on_progress=lambda percent, message: self.progress.emit(percent, message),
                stale_days=self._request.stale_days,
                large_file_mb=self._request.large_file_mb,
                hotspot_changes=self._request.hotspot_changes,
                commit_pattern=self._request.commit_pattern,
            )
        except Exception as exc:  # 任何异常都要变成一条可读消息，不能让线程静默死掉
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.finished.emit(view)
