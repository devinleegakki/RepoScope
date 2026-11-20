"""Reports：textResultstext Markdown / HTML / CSV。

textreporttext GUI text，text"text"：
text"text"text**text**。text，
textAnti-pattern listtextreport，text"text"text。

* Markdown / HTML / CSV text ``reporters`` text，text，
  text。
* Previewtext Markdown；textfilestext HTML，text。
"""

from __future__ import annotations

from core import reporters
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from . import dialogs
from .contract import AnalysisView
from .widgets import Card, PageHeader

_SECTIONS = (
    ("1. Overall assessment", "Overall assessment"),
    ("2. Key metrics", "Key metrics"),
    ("3. Author Contributions", "Author Contributions"),
    ("4. Commit activity", "Commit activity"),
    ("5. File hotspots", "Hot files"),
    ("6. Large files", "Large files"),
    ("7. Stale files", "Stale files"),
    ("8. Anti-pattern list", "Anti-pattern list"),
    ("9. Commit convention", "Commit convention"),
    ("10. Reproduction", "Reproduction"),
)

# reporttext，text reporters（text）：
build_markdown = reporters.render_markdown
export = reporters.write_report

class ReportPage(QWidget):
    """Reports：text、textPreview、text。"""

    def __init__(self) -> None:
        super().__init__()
        self._view: AnalysisView | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.header = PageHeader("Reports", "Analysis completetextreport")
        outer.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)

        outline_card = Card()
        outline_layout = QVBoxLayout(outline_card)
        outline_layout.setContentsMargins(12, 12, 12, 12)
        outline_layout.setSpacing(8)
        title = QLabel("text")
        title.setObjectName("sectionTitle")
        outline_layout.addWidget(title)
        self.outline = QListWidget()
        self.outline.setObjectName("outline")
        self.outline.addItems([label for label, _ in _SECTIONS])
        self.outline.currentRowChanged.connect(self._jump)
        outline_layout.addWidget(self.outline, 1)
        body.addWidget(outline_card, 1)

        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(8)
        self.tabs = QTabWidget()
        self.preview = QTextBrowser()
        self.preview.setObjectName("reportPreview")
        self.preview.setOpenExternalLinks(False)
        self.source = QTextBrowser()
        self.source.setObjectName("reportSource")
        self.tabs.addTab(self.preview, "Preview")
        self.tabs.addTab(self.source, "Markdown Source")
        preview_layout.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        self.status = QLabel("textreport")
        self.status.setObjectName("pageHint")
        actions.addWidget(self.status)
        actions.addStretch(1)
        self.export_btn = QPushButton("Export report…")
        self.export_btn.setObjectName("primary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        actions.addWidget(self.export_btn)
        preview_layout.addLayout(actions)
        body.addWidget(preview_card, 3)

        outer.addLayout(body, 1)

    # -- text ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self._view = view
        markdown = build_markdown(view)
        self.preview.setMarkdown(markdown)
        self.source.setPlainText(markdown)
        self.status.setText(f"text · {len(markdown.splitlines())} text · text Markdown / HTML / CSV")
        self.export_btn.setEnabled(True)
        self.header.set_hint(
            f"{view.snapshot.repo_name} · text {len(view.warnings)} textanti-patterns · "
            f"health score {view.health_score:.0f}"
        )

    def _jump(self, row: int) -> None:
        if row < 0:
            return
        _, keyword = _SECTIONS[row]
        cursor = self.preview.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.preview.setTextCursor(cursor)
        self.preview.find(keyword)

    def _export(self) -> None:
        if self._view is None:
            return
        dialog = dialogs.ExportDialog(self)
        if dialog.exec() != dialog.Accepted:
            return
        formats = dialog.selected_formats()
        if not formats:
            dialogs.show_error(self, "textSelecttext", "text。")
            return
        target = QFileDialog.getExistingDirectory(self, "Selecttextdirectory")
        if not target:
            return
        try:
            written = export(self._view, formats, target)
        except OSError as exc:
            dialogs.show_error(self, "textfailed", f"textfilestext：{exc}")
            return
        self.status.setText(f"text {len(written)} textfilestext {target}")
        dialogs.show_info(
            self,
            "textComplete",
            "\n".join(str(path) for path in written),
        )

