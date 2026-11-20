"""text：text、text、text、text。

text：
    QMainWindow（text） + QListWidget（text） + QStackedWidget（text）
text ``currentRowChanged`` text ``_row_to_page`` text ``QStackedWidget`` text，
text，text——text"text"。

text：
    Setup    → Repository、Analysis Settings
    Results → Dashboard、Commit Trends、Author Contributions、Data Analysis、Anti-pattern Center、Reports
    Batch    → Repository Comparison
（text"text"text，text。）
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QThread, QTimer
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel

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
    ("Setup", ("Repository", "Analysis Settings")),
    ("Results", ("Dashboard", "Commit Trends", "Author Contributions", "Data Analysis", "Anti-pattern Center", "Reports")),
    ("Batch", ("Repository Comparison",)),
)

_NAV_ICONS = {
    "Repository": "cil-folder-open.png",
    "Analysis Settings": "cil-settings.png",
    "Dashboard": "cil-speedometer.png",
    "Commit Trends": "cil-chart-line.png",
    "Author Contributions": "cil-people.png",
    "Data Analysis": "cil-file.png",
    "Anti-pattern Center": "cil-task.png",
    "Reports": "cil-description.png",
    "Repository Comparison": "cil-layers.png",
}


class _LegacyNavigation:
    """Small adapter for the pre-grouped four-page navigation API."""

    def __init__(self, stack: QStackedWidget) -> None:
        self._stack = stack

    def setCurrentRow(self, row: int) -> None:
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)


class MainWindow(QMainWindow):
    """text。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RepoScope — local Git repository health analysis")
        self.resize(1240, 820)

        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._view: AnalysisView | None = None
        self._row_to_page: dict[int, int] = {}
        self._name_to_row: dict[str, int] = {}
        self._nav_titles: dict[int, str] = {}
        self._sidebar_expanded = True
        # Compatibility aliases kept for older integrations that used the
        # original four-page prototype API.
        self.navigation = self.sidebar if hasattr(self, "sidebar") else None
        self.pages = self.stack if hasattr(self, "stack") else None

        self._build_ui()
        self._apply_stylesheet()
        self.statusBar().showMessage("Ready · text「Repository」textlocal Git repository")

    # -- text --------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())
        self._progress_host = self._build_progress_bar()
        self._progress_host.setVisible(False)   # textanalyzetext，text
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
        self.dashboard_page.open_patterns.connect(lambda: self.goto("Anti-pattern Center"))
        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(self._name_to_row["Repository"])
        self.navigation = _LegacyNavigation(self.stack)
        self.pages = self.stack
        self.overview_values = {"repo_name": QLabel("—")}
        self.commit_model = QStandardItemModel(self)
        self.file_model = QStandardItemModel(self)
        self.refs_model = QStandardItemModel(self)

    def _render_snapshot(self, snapshot) -> None:
        """Render the raw snapshot for callers of the original GUI API."""
        self.overview_values["repo_name"].setText(snapshot.repo_name)
        self.commit_model.clear()
        self.file_model.clear()
        self.refs_model.clear()
        for commit in snapshot.commits:
            self.commit_model.appendRow([QStandardItem(commit.hash), QStandardItem(commit.message)])
        for file_record in snapshot.files:
            self.file_model.appendRow([QStandardItem(file_record.path), QStandardItem(str(file_record.size_bytes))])
        for ref in (*snapshot.branches, *snapshot.tags):
            self.refs_model.appendRow([QStandardItem(ref)])

    def _build_sidebar(self) -> QListWidget:
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setIconSize(QSize(18, 18))
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(220)

        self.sidebar_host = QWidget()
        self.sidebar_host.setObjectName("sidebarHost")
        self.sidebar_host.setMinimumWidth(220)
        self.sidebar_host.setMaximumWidth(220)
        host_layout = QVBoxLayout(self.sidebar_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        header = QWidget()
        self.sidebar_header = header
        header.setObjectName("sidebarHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 12, 12)
        header_layout.setSpacing(8)
        logo = QLabel("R")
        self.sidebar_logo = logo
        logo.setObjectName("sidebarLogo")
        header_layout.addWidget(logo)
        title = QLabel("RepoScope")
        self.sidebar_title = title
        title.setObjectName("sidebarTitle")
        header_layout.addWidget(title)
        header_layout.addStretch(1)
        self.sidebar_toggle = QToolButton()
        self.sidebar_toggle.setObjectName("sidebarToggle")
        self.sidebar_toggle.setIcon(self._icon("cil-menu.png"))
        self.sidebar_toggle.setToolTip("text")
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.sidebar_toggle)
        host_layout.addWidget(header)

        page_index = 0
        for group, names in _NAV_GROUPS:
            header = QListWidgetItem(group)
            header.setFlags(Qt.NoItemFlags)
            header.setSizeHint(QSize(0, 30))
            header.setData(Qt.UserRole, "header")
            self.sidebar.addItem(header)

            for name in names:
                item = QListWidgetItem(name)
                icon_name = _NAV_ICONS.get(name)
                if icon_name:
                    item.setIcon(self._icon(icon_name))
                item.setSizeHint(QSize(0, 40))
                item.setData(Qt.UserRole, name)
                self.sidebar.addItem(item)
                self._row_to_page[self.sidebar.count() - 1] = page_index
                self._name_to_row[name] = self.sidebar.count() - 1
                self._nav_titles[self.sidebar.count() - 1] = name
                page_index += 1
        host_layout.addWidget(self.sidebar, 1)
        return self.sidebar_host

    @staticmethod
    def _icon(name: str) -> QIcon:
        path = Path(__file__).with_name("assets") / "icons" / name
        return QIcon(str(path)) if path.exists() else QIcon()

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        start = 220 if not self._sidebar_expanded else 64
        end = 220 if self._sidebar_expanded else 64
        # Hide the brand text while collapsed so the menu button remains
        # inside the 64px hit area and can always be used to expand again.
        self.sidebar_logo.setVisible(self._sidebar_expanded)
        self.sidebar_title.setVisible(self._sidebar_expanded)
        self.sidebar_header.layout().setContentsMargins(
            16 if self._sidebar_expanded else 10,
            14,
            12 if self._sidebar_expanded else 10,
            12,
        )
        self._sidebar_animation = QPropertyAnimation(self.sidebar_host, b"minimumWidth", self)
        self._sidebar_animation.setDuration(180)
        self._sidebar_animation.setStartValue(start)
        self._sidebar_animation.setEndValue(end)
        self._sidebar_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._sidebar_animation.start()
        self.sidebar_host.setMaximumWidth(end)
        self.sidebar.setMinimumWidth(end)
        self.sidebar.setMaximumWidth(end)
        for row, title in self._nav_titles.items():
            item = self.sidebar.item(row)
            item.setText(title if self._sidebar_expanded else "")
            item.setToolTip(title)
        for row in range(self.sidebar.count()):
            item = self.sidebar.item(row)
            if item.data(Qt.UserRole) == "header":
                item.setHidden(not self._sidebar_expanded)
        self.sidebar_toggle.setToolTip("text" if self._sidebar_expanded else "text")

    def _on_nav_changed(self, row: int) -> None:
        page = self._row_to_page.get(row)
        if page is not None:
            self.stack.setCurrentIndex(page)

    def goto(self, name: str) -> None:
        """text。text（textRisktext）text。"""
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

        self.repo_label = QLabel("textSelectrepository")
        self.repo_label.setObjectName("topbarRepo")
        layout.addWidget(self.repo_label, 1)

        self.analyze_btn = QPushButton("Re-analyze")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._analyze_current)
        layout.addWidget(self.analyze_btn)

        self.export_btn = QPushButton("Export report")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(lambda: self.goto("Reports"))
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
        self.progress_label = QLabel("Pending analysis")
        self.progress_label.setObjectName("pageHint")
        self.progress_label.setMinimumWidth(240)
        layout.addWidget(self.progress, 1)
        layout.addWidget(self.progress_label)
        return host

    # -- text ------------------------------------------------------------
    def _analyze_current(self) -> None:
        path = self.current_path()
        if not path:
            self.goto("Repository")
            self.statusBar().showMessage("Please firsttext「Repository」textlocal Git repository")
            return
        self._start_analysis(path)

    def current_path(self) -> str:
        return self.select_page.path_edit.text().strip()

    def _start_analysis(self, path: str) -> None:
        if self._thread is not None:
            dialogs.show_info(self, "Analyzing", "text，Please wait。")
            return

        if not path:
            dialogs.show_error(self, "MissingrepositoryPath", "Please firsttext「Repository」textSelecttextlocal Git repositorydirectory。")
            return
        if not Path(path).is_dir():
            dialogs.show_error(self, "Pathdoes not exist", f"Cannot findtextdirectory：\n{path}")
            return
        if not (Path(path) / ".git").exists():
            dialogs.show_error(
                self, "Not a Git repository",
                f"directorytext .git filestext：\n{path}\n\ntextSelectrepositoryroot directory，textsubdirectory。",
            )
            return
        if not self.settings_page.pattern_is_valid():
            dialogs.show_error(
                self, "Commit conventionregextext",
                "「Analysis Settings」textcommitsInformationtextvalidregex，Please firsttextanalyze。",
            )
            self.goto("Analysis Settings")
            return

        request: AnalysisRequest = self.settings_page.to_request(path)
        self.select_page.remember(path)
        self.repo_label.setText(f"{Path(path).name} · {path}")
        self.analyze_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress_label.setText("Preparing…")
        self._progress_host.setVisible(True)
        self.statusBar().showMessage(f"Analyzing {Path(path).name} …")

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
        self.progress_label.setText(f"Complete · elapsed {view.elapsed_seconds:.1f}s")
        self._progress_host.setVisible(False)   # Completetext，elapsedInformationtext
        self.analyze_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.statusBar().showMessage(
            f"{view.snapshot.repo_name} · {view.total_commits} textcommits · "
            f"{view.author_count} textauthors · health score {view.health_score:.0f} · "
            f"{len(view.warnings)} textanti-patterns · elapsed {view.elapsed_seconds:.1f}s"
        )
        self.goto("Dashboard")

    def _on_failed(self, message: str) -> None:
        self.progress_label.setText("analyzefailed")
        self._progress_host.setVisible(False)
        self.statusBar().showMessage("analyzefailed")
        dialogs.show_error(self, "analyzefailed", message)

    def _cleanup(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None

    # -- text ------------------------------------------------------
    def open_repo(self, path: str) -> None:
        """textanalyzetextrepository，text ``--path`` text。

        textdirectory：text，text，text"text"
        text。text show() text，text。
        """
        resolved = str(Path(path).resolve())
        self.select_page.path_edit.setText(resolved)
        if not Path(resolved).is_dir():
            dialogs.show_error(self, "Pathdoes not exist", f"Cannot findtextdirectory：\n{resolved}")
            return
        self._start_analysis(resolved)

    # -- text --------------------------------------------------------
    def load_demo(self) -> None:
        """text，text。

        textrepositorytext（textrepositorytextcommits），text。
        ``python main.py --demo`` text，text。
        """
        from . import mock_data

        view = mock_data.build("demo/workspace", force_synthetic=True)
        self.repo_label.setText("text · 160 textcommits · 4 textauthors")
        self._on_finished(view)
        self.analyze_btn.setEnabled(False)   # textPathtext
        self.statusBar().showMessage(
            "text · text，text metrics.py textResults"
        )

    # -- text ------------------------------------------------------------
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
        # textanalyze：text，text"text git"text
        QTimer.singleShot(150, lambda: window.open_repo(repo))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
