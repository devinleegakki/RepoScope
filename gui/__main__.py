"""Compatibility wrapper; the canonical entry is ``python main.py``."""

from __future__ import annotations

from main import _run_gui


def main() -> int:
    return _run_gui([])


if __name__ == "__main__":
    raise SystemExit(main())



