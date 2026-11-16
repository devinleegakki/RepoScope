"""RepoScope 的图形界面层。

只依赖 ``models.py``（共享数据模型）和 ``PySide6``。
其它三个模块通过 ``gui.contract.AnalysisView`` 与界面交接，见该文件说明。
"""

from .contract import AnalysisView

__all__ = ["AnalysisView"]
