"""离屏截图：把九个页面各存一张 PNG，用于自查布局和写报告配图。

用法：
    python tools/screenshot.py            # 输出到 docs/screens/
    python tools/screenshot.py out_dir

为什么值得单独写一个脚本：
* 改完 QSS 不用手点九次页面就能看到全部效果；
* 报告和 PPT 需要配图，这个脚本一次出齐；
* 用 ``QT_QPA_PLATFORM=offscreen``，没有显示器也能跑（CI 里同样可用）。
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
    ("01-仓库选择", "仓库选择"),
    ("02-分析配置", "分析配置"),
    ("03-总览仪表板", "总览仪表板"),
    ("04-提交趋势", "提交趋势"),
    ("05-作者贡献", "作者贡献"),
    ("06-数据分析", "数据分析"),
    ("07-反模式中心", "反模式中心"),
    ("08-报告区", "报告区"),
    ("09-多仓库对比", "多仓库对比"),
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
