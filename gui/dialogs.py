"""Notes

none
Notes QMessageBox，Notes
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


def ask_repository(parent: QWidget) -> str | None:
    """Notes Git repository

    path ``None``，Notes
    """
    selected = QFileDialog.getExistingDirectory(parent, "select Git repository")
    if not selected:
        return None
    if not (Path(selected) / ".git").exists():
        show_error(
            parent,
            "Choose a Git repository",
            f"no .git files\n{selected}\n\n"
            "repository",
        )
        return None
    return selected


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


class ExportDialog(QDialog):
    """select

    files Wyh Notes reporters complete
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("analysis")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("select"))

        self.markdown = QCheckBox("Markdown (.md)")
        self.html = QCheckBox("HTML (.html)")
        self.csv = QCheckBox("CSV (.csv)")
        for box in (self.markdown, self.html, self.csv):
            layout.addWidget(box)
        self.markdown.setChecked(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_formats(self) -> list[str]:
        """medium ``["markdown"]``。"""
        formats = []
        if self.markdown.isChecked():
            formats.append("markdown")
        if self.html.isChecked():
            formats.append("html")
        if self.csv.isChecked():
            formats.append("csv")
        return formats



