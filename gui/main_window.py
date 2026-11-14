"""主窗口：外壳、侧边栏导航、页面容器、后台线程调度。

骨架只有三样东西：
    QMainWindow（壳） + QListWidget（导航） + QStackedWidget（一叠页面）
导航的 ``currentRowChanged`` 通过 ``_row_to_page`` 映射到 ``QStackedWidget`` 的页索引，
切页不销毁页面，所以来回切是瞬间的——这一条直接对应验收标准里的"切换页面不卡顿"。

导航按组长文档的八个区域组织：
    准备    → 仓库选择、分析配置
    分析结果 → 总览仪表板、提交趋势、作者贡献、数据分析、反模式中心、报告区
    批量    → 多仓库对比
（第八个区域"进度反馈"是常驻的进度条，不是一页。）
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import dialogs
from .batch import BatchPage
from .charts import AuthorsPage
from .contract import AnalysisRequest, AnalysisView
from .dashboard import DashboardPage
from .patterns import PatternPage
from .report_page import ReportPage
from .select_page import SelectPage
from .settings_page import SettingsPage
from .tables import FilesPage
from .trends import TrendPage
from .worker import AnalysisWorker

_NAV_GROUPS = (
    ("准备", ("仓库选择", "分析配置")),
    ("分析结果", ("总览仪表板", "提交趋势", "作者贡献", "数据分析", "反模式中心", "报告区")),
    ("批量", ("多仓库对比",)),
)


class MainWindow(QMainWindow):
    """程序主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RepoScope — 本地 Git 仓库健康分析")
        self.resize(1240, 820)

        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._view: AnalysisView | None = None
        self._row_to_page: dict[int, int] = {}
        self._name_to_row: dict[str, int] = {}

        self._build_ui()
        self._apply_stylesheet()
        self.statusBar().showMessage("就绪 · 在「仓库选择」里选一个本地 Git 仓库")

    # -- 界面搭建 --------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())
        self._progress_host = self._build_progress_bar()
        self._progress_host.setVisible(False)   # 只在分析时出现，空闲时别占一条横杠
        outer.addWidget(self._progress_host)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        body_host = QWidget()
        body_host.setLayout(body)
        outer.addWidget(body_host, 1)

        self.select_page = SelectPage()
        self.settings_page = SettingsPage()
        self.dashboard_page = DashboardPage()
        self.trend_page = TrendPage()
        self.authors_page = AuthorsPage()
        self.files_page = FilesPage()
        self.patterns_page = PatternPage()
        self.report_page = ReportPage()
        self.batch_page = BatchPage()

        pages = (
            self.select_page, self.settings_page, self.dashboard_page,
            self.trend_page, self.authors_page, self.files_page,
            self.patterns_page, self.report_page, self.batch_page,
        )
        for page in pages:
            self.stack.addWidget(page)

        self.select_page.analyze_requested.connect(self._start_analysis)
        self.dashboard_page.open_patterns.connect(lambda: self.goto("反模式中心"))
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(self._name_to_row["仓库选择"])

    def _build_sidebar(self) -> QListWidget:
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(196)

        page_index = 0
        for group, names in _NAV_GROUPS:
            header = QListWidgetItem(group)
            header.setFlags(Qt.NoItemFlags)
            header.setSizeHint(QSize(0, 30))
            header.setData(Qt.UserRole, "header")
            self.sidebar.addItem(header)

            for name in names:
                item = QListWidgetItem(f"   {name}")
                item.setSizeHint(QSize(0, 40))
                item.setData(Qt.UserRole, name)
                self.sidebar.addItem(item)
                self._row_to_page[self.sidebar.count() - 1] = page_index
                self._name_to_row[name] = self.sidebar.count() - 1
                page_index += 1
        return self.sidebar

    def _on_nav_changed(self, row: int) -> None:
        page = self._row_to_page.get(row)
        if page is not None:
            self.stack.setCurrentIndex(page)

    def goto(self, name: str) -> None:
        """按导航名切页。其它页面（如总览的风险摘要）通过它跳转。"""
        row = self._name_to_row.get(name)
        if row is not None:
            self.sidebar.setCurrentRow(row)
            self.stack.setCurrentIndex(self._row_to_page[row])

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        mark = QLabel("RepoScope")
        mark.setObjectName("brand")
        layout.addWidget(mark)

        self.repo_label = QLabel("未选择仓库")
        self.repo_label.setObjectName("topbarRepo")
        layout.addWidget(self.repo_label, 1)

        self.analyze_btn = QPushButton("重新分析")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._analyze_current)
        layout.addWidget(self.analyze_btn)

        self.export_btn = QPushButton("导出报告")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(lambda: self.goto("报告区"))
        layout.addWidget(self.export_btn)
        return bar

    def _build_progress_bar(self) -> QWidget:
        host = QWidget()
        host.setObjectName("progressbar")
        layout = QHBoxLayout(host)
        layout.setContentsMargins(20, 0, 20, 8)
        layout.setSpacing(12)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_label = QLabel("待分析")
        self.progress_label.setObjectName("pageHint")
        self.progress_label.setMinimumWidth(240)
        layout.addWidget(self.progress, 1)
        layout.addWidget(self.progress_label)
        return host

    # -- 操作 ------------------------------------------------------------
    def _analyze_current(self) -> None:
        path = self.current_path()
        if not path:
            self.goto("仓库选择")
            self.statusBar().showMessage("请先在「仓库选择」里选一个本地 Git 仓库")
            return
        self._start_analysis(path)

    def current_path(self) -> str:
        return self.select_page.path_edit.text().strip()

    def _start_analysis(self, path: str) -> None:
        if self._thread is not None:
            dialogs.show_info(self, "正在分析", "当前任务还没结束，请稍候。")
            return

        if not path:
            dialogs.show_error(self, "缺少仓库路径", "请先在「仓库选择」里选择一个本地 Git 仓库目录。")
            return
        if not Path(path).is_dir():
            dialogs.show_error(self, "路径不存在", f"找不到这个目录：\n{path}")
            return
        if not (Path(path) / ".git").exists():
            dialogs.show_error(
                self, "不是 Git 仓库",
                f"目录里没有 .git 文件夹：\n{path}\n\n请选择仓库根目录，而不是它的子目录。",
            )
            return
        if not self.settings_page.pattern_is_valid():
            dialogs.show_error(
                self, "提交规范正则写错了",
                "「分析配置」里的提交信息格式不是合法正则，请先改正再分析。",
            )
            self.goto("分析配置")
            return

        request: AnalysisRequest = self.settings_page.to_request(path)
        self.select_page.remember(path)
        self.repo_label.setText(f"{Path(path).name} · {path}")
        self.analyze_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress_label.setText("准备中…")
        self._progress_host.setVisible(True)
        self.statusBar().showMessage(f"正在分析 {Path(path).name} …")

        self._thread = QThread(self)
        self._worker = AnalysisWorker(request)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()

    def _on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.progress_label.setText(f"{message} · {percent}%")

    def _on_finished(self, view: AnalysisView) -> None:
        self._view = view
        for page in (
            self.dashboard_page, self.trend_page, self.authors_page,
            self.files_page, self.patterns_page, self.report_page,
        ):
            page.set_data(view)

        self.progress.setValue(100)
        self.progress_label.setText(f"完成 · 用时 {view.elapsed_seconds:.1f}s")
        self._progress_host.setVisible(False)   # 完成后收起，用时信息交给状态栏
        self.analyze_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.statusBar().showMessage(
            f"{view.snapshot.repo_name} · {view.total_commits} 次提交 · "
            f"{view.author_count} 位作者 · 健康度 {view.health_score:.0f} · "
            f"{len(view.warnings)} 条反模式 · 用时 {view.elapsed_seconds:.1f}s"
        )
        self.goto("总览仪表板")

    def _on_failed(self, message: str) -> None:
        self.progress_label.setText("分析失败")
        self._progress_host.setVisible(False)
        self.statusBar().showMessage("分析失败")
        dialogs.show_error(self, "分析失败", message)

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    # -- 命令行直启 ------------------------------------------------------
    def open_repo(self, path: str) -> None:
        """启动后立刻分析指定仓库，供 ``--path`` 使用。

        现场演示时不用手点目录：命令一敲，进度条就开始动，比"先点这里再点那里"
        少一次出错机会。窗口已经 show() 过，所以这里补一小段延迟让进度条先画出来。
        """
        resolved = str(Path(path).resolve())
        self.select_page.path_edit.setText(resolved)
        if not Path(resolved).is_dir():
            dialogs.show_error(self, "路径不存在", f"找不到这个目录：\n{resolved}")
            return
        self._start_analysis(resolved)

    # -- 演示模式 --------------------------------------------------------
    def load_demo(self) -> None:
        """直接灌入内置演示数据集，用于彩排和截图。

        真实仓库历史太短时（新仓库只有十来个提交），趋势图和热力图会空得看不出效果。
        ``python run_gui.py --demo`` 就是走这条路，所有页面立刻有数据。
        """
        from . import mock_data

        view = mock_data.build("demo/workspace", force_synthetic=True)
        self.repo_label.setText("演示数据集 · 160 次提交 · 4 位作者")
        self._on_finished(view)
        self.analyze_btn.setEnabled(False)   # 演示数据没有真实路径可重跑
        self.statusBar().showMessage(
            "演示数据模式 · 数值来自内置数据集，接入 metrics.py 后即为真实分析结果"
        )

    # -- 样式 ------------------------------------------------------------
    def _apply_stylesheet(self) -> None:
        qss = Path(__file__).with_name("style.qss")
        if qss.exists():
            self.setStyleSheet(qss.read_text(encoding="utf-8"))


def main(demo: bool = False, repo: str | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("RepoScope")
    app.setOrganizationName("RepoScope")
    window = MainWindow()
    if demo:
        window.load_demo()
    window.show()
    if repo and not demo:
        # 等事件循环跑起来再分析：进度条先出现，观众能看见"正在读 git"的过程
        QTimer.singleShot(150, lambda: window.open_repo(repo))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
