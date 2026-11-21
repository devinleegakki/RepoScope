"""analysis Markdown / HTML / CSV。

report GUI Notes"export"：
Notes"Notes"Notes**none**。export
report"export"Notes

* Markdown / HTML / CSV Notes ``reporters`` Notes
  export
* Notes Markdown；files HTML，Notes
"""

from __future__ import annotations

from pathlib import Path

from core import reporters
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
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
    ("1. Overview", "Overview"),
    ("2. Repository summary", "Repository summary"),
    ("3. authors", "authors"),
    ("4. commits", "commits"),
    ("5. Hotspot files", "Hotspot files"),
    ("6. Large files", "Large files"),
    ("7. Stale files", "Stale files"),
    ("8. anti-patterns", "anti-patterns"),
    ("9. commits", "commits"),
    ("10. Dependencies and security", "Dependencies and security"),
)

# report reporters（Notes
build_markdown = reporters.render_markdown
export = reporters.write_report

class ReportPage(QWidget):
    """report"""

    def __init__(self) -> None:
        super().__init__()
        self._view: AnalysisView | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.header = PageHeader("Reports", "Generated analysis outputs")
        outer.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)

        outline_card = Card()
        outline_layout = QVBoxLayout(outline_card)
        outline_layout.setContentsMargins(12, 12, 12, 12)
        outline_layout.setSpacing(8)
        title = QLabel("Report sections")
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
        self.tabs.addTab(self.source, "Markdown source")
        preview_layout.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        self.status = QLabel("No report generated")
        self.status.setObjectName("pageHint")
        actions.addWidget(self.status)
        actions.addStretch(1)
        self.export_btn = QPushButton("Export report")
        self.export_btn.setObjectName("primary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        actions.addWidget(self.export_btn)
        preview_layout.addLayout(actions)
        body.addWidget(preview_card, 3)

        outer.addLayout(body, 1)

    # -- Notes ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self._view = view
        markdown = build_markdown(view)
        self.preview.setMarkdown(markdown)
        self.source.setPlainText(markdown)
        self.status.setText(f"Generated {len(markdown.splitlines())} lines · export as Markdown, HTML, or CSV")
        self.export_btn.setEnabled(True)
        self.header.set_hint(
            f"{view.snapshot.repo_name} · {len(view.warnings)} anti-patterns · "
            f"health {view.health_score:.0f}"
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
        if dialog.exec() != QDialog.Accepted:
            return
        formats = dialog.selected_formats()
        if not formats:
            self.status.setText("Export cancelled · select at least one format")
            dialogs.show_error(self, "Export", "Select at least one output format.")
            return
        self.status.setText("Preparing export…")
        self.export_btn.setEnabled(False)
        QApplication.processEvents()

        repository_path = Path(self._view.snapshot.repo_path)
        default_dir = repository_path / "reports"
        if not default_dir.is_dir():
            default_dir = Path.cwd() / "reports"
        target = QFileDialog.getExistingDirectory(
            self,
            "Choose output folder",
            str(default_dir),
        )
        if not target:
            self.status.setText("Export cancelled")
            self.export_btn.setEnabled(True)
            return
        try:
            written = export(self._view, formats, target)
        except (OSError, ValueError, RuntimeError) as exc:
            self.status.setText("Export failed")
            self.export_btn.setEnabled(True)
            dialogs.show_error(self, "Export failed", str(exc))
            return
        self.status.setText(f"Exported {len(written)} files to {target}")
        self.export_btn.setEnabled(True)
        dialogs.show_info(
            self,
            "Export complete",
            "\n".join(str(path) for path in written),
        )




