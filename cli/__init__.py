"""RepoScope 命令行接口。

    python main.py analyze <仓库目录>
    python main.py check   <仓库目录>
    python main.py export  <仓库目录>
    python main.py batch   <仓库目录...>

细节交给 ``cli.commands``，本模块只把解析好的参数分发过去。
"""

from __future__ import annotations

from .commands import build_parser, main

__all__ = ["build_parser", "main"]
