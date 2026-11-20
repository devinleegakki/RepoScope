"""RepoScope application entry point.

Launch the desktop GUI by default, or dispatch one of the CLI commands.
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
        description="RepoScope repository analysis",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the desktop interface (the default)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RepoScope 1.0",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="Open the interface with demo data")
    source.add_argument("--path", metavar="REPOSITORY", help="Analyze a Git repository")
    return parser


def _run_gui(argv: list[str] | None = None) -> int:
    """Run the GUI; CLI commands do not require PySide6."""
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



