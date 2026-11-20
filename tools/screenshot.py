"""text：text PNG，textreporttext。

text：
    python tools/screenshot.py            # text docs/screens/
    python tools/screenshot.py out_dir

text：
* text QSS text；
* reporttext PPT text，text；
* text ``QT_QPA_PLATFORM=offscreen``，text（CI text）。
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
    ("01-Repository", "Repository"),
    ("02-Analysis Settings", "Analysis Settings"),
    ("03-Dashboard", "Dashboard"),
    ("04-Commit Trends", "Commit Trends"),
    ("05-Author Contributions", "Author Contributions"),
    ("06-Data Analysis", "Data Analysis"),
    ("07-Anti-pattern Center", "Anti-pattern Center"),
    ("08-Reports", "Reports"),
    ("09-Repository Comparison", "Repository Comparison"),
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
