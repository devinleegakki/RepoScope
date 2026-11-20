"""RepoScope 的唯一应用入口。

无参数或使用 ``--demo`` / ``--path`` 时启动 GUI；使用 ``analyze``、
``check``、``export``、``batch`` 子命令时继续运行原有 CLI。
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
        description="RepoScope 图形界面启动器",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="显式启动图形界面（默认行为）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RepoScope 1.0",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="加载内置演示数据集")
    source.add_argument("--path", metavar="目录", help="启动后立即分析本地 Git 仓库")
    return parser


def _run_gui(argv: list[str] | None = None) -> int:
    """启动 GUI；CLI-only 调用不会加载 PySide6。"""
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
