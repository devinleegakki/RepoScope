"""RepoScope text。

text ``--demo`` / ``--path`` text GUI；text ``analyze``、
``check``、``export``、``batch`` text CLI。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main as cli_main  # noqa: E402


def _gui_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="RepoScope GUI launcher",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="explicitly start the GUI (default)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RepoScope 1.0",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="load the built-in demo dataset")
    source.add_argument("--path", metavar="directory", help="analyze a local Git repository after startup")
    return parser


def _run_gui(argv: list[str] | None = None) -> int:
    """text GUI；CLI-only text PySide6。"""
    from gui.main_window import main as gui_main

    args = _gui_parser().parse_args(argv)
    return gui_main(demo=args.demo, repo=args.path)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"analyze", "check", "export", "batch"}:
        return cli_main(args)
    return _run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
