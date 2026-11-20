"""Deprecated compatibility wrapper; use ``python main.py`` instead."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import _run_gui


if __name__ == "__main__":
    raise SystemExit(_run_gui(sys.argv[1:]))
