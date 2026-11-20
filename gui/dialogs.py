"""textcheck。

text“InvalidtextNotice”，text——
text QMessageBox，text。
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
    """textdirectory，textchecktextNot a Git repository。

    textPath；textcancelledtextdirectorytext ``None``，text。
    """
    selected = QFileDialog.getExistingDirectory(parent, "Selectlocal Git repository")
    if not selected:
        return None
    if not (Path(selected) / ".git").exists():
        show_error(
            parent,
            "Not a Git repository",
            f"directorytext .git filestext：\n{selected}\n\n"
            "textSelectrepositorytextroot directory，textfilestext。",
        )
        return None
    return selected


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


class ExportDialog(QDialog):
    """textSelect。

    textSelecttext；textfilestext Wyh text reporters textComplete。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export analysis report")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select output formats："))

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
        """text，text ``["markdown"]``。"""
        formats = []
        if self.markdown.isChecked():
            formats.append("markdown")
        if self.html.isChecked():
            formats.append("html")
        if self.csv.isChecked():
            formats.append("csv")
        return formats
