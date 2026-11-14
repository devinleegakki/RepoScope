"""RepoScope 图形界面入口。

三种启动方式：

    python run_gui.py                     # 正常启动，自己在界面里选仓库
    python run_gui.py --demo              # 内置演示数据集（彩排 / 截图 / 图表好看）
    python run_gui.py --path <仓库目录>    # 启动即分析指定仓库（现场演示，真数据）

``--demo`` 与 ``--path`` 互斥：演示数据用来看界面，真实仓库用来看真问题。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gui.main_window import main  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_gui.py",
        description="RepoScope 图形界面启动器",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--demo",
        action="store_true",
        help="加载内置演示数据集（160 次提交 / 4 位作者）",
    )
    source.add_argument(
        "--path",
        metavar="目录",
        default=None,
        help="启动后立即分析这个本地 Git 仓库",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    raise SystemExit(main(demo=args.demo, repo=args.path))
