"""RepoScope 命令行入口（课程要求：入口文件命名为 main.py）。

    python main.py analyze <仓库目录>              # 分析并导出报告
    python main.py check   <仓库目录>              # 校验仓库是否可分析
    python main.py export  <仓库目录>              # 分析并一次导出三种格式
    python main.py batch   <仓库目录...>           # 并发分析多个仓库

GUI 版本仍从 ``run_gui.py`` 启动，两者共用 ``services.py`` 分析服务与
``reporters.py`` 报告生成，结果一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
