"""Capture screenshots of the main RepoScope pages.

Usage::

    python tools/screenshot.py
    python tools/screenshot.py output_directory

The script uses the application stylesheet and the offscreen Qt platform so it
can also run in CI environments.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.main_window import MainWindow  # noqa: E402

_PAGES = (
    ("01-repository", "repository"),
    ("02-configuration", "configuration"),
    ("03-dashboard", "dashboard"),
    ("04-commits", "commits"),
    ("05-authors", "authors"),
    ("06-analysis", "analysis"),
    ("07-anti-patterns", "anti-patterns"),
    ("08-report", "report"),
    ("09-repository", "repository"),
)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screens"
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("RepoScope")
    window = MainWindow()
    window.resize(1240, 820)
    window.load_demo()
    window.show()
    app.processEvents()

    for filename, nav in _PAGES:
        window.goto(nav)
        for _ in range(3):
            app.processEvents()
        path = out / f"{filename}.png"
        window.grab().save(str(path))
        print(f"saved {path}")

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



