"""RepoScope text。

    python main.py analyze <repositorydirectory>
    python main.py check   <repositorydirectory>
    python main.py export  <repositorydirectory>
    python main.py batch   <repositorydirectory...>

text ``cli.commands``，text。
"""

from __future__ import annotations

from .commands import build_parser, main

__all__ = ["build_parser", "main"]
