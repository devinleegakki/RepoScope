"""RepoScope Notes

    python main.py analyze <repository>
    python main.py check   <repository>
    python main.py export  <repository>
    python main.py batch   <repository...>

Notes ``cli.commands``，settings
"""

from __future__ import annotations

from .commands import build_parser, main

__all__ = ["build_parser", "main"]



