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

from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
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


def _load_screenshot_font() -> str | None:
    """Register a font with broad Unicode coverage for offscreen screenshots.

    Headless Qt environments may expose no system font database. Registering
    the Windows CJK fonts explicitly prevents labels and punctuation from
    becoming tofu squares in generated images. The function is harmless on
    non-Windows systems and falls back to the platform default font.
    """
    candidates = (
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path(r"/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    )
    preferred: str | None = None
    for font_path in candidates:
        if not font_path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and preferred is None:
            preferred = "Microsoft YaHei UI" if "Microsoft YaHei UI" in families else families[0]
    if preferred:
        QApplication.setFont(QFont(preferred, 10))
    return preferred


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screens"
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    _load_screenshot_font()
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



