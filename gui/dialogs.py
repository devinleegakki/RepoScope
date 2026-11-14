"""对话框与用户输入的校验。

验收标准里的“无效输入有明确提示”，全部集中在这里实现——
不要在页面里散落 QMessageBox，否则样式和文案会前后不一致。
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
    """让用户选一个目录，并且当场校验它是不是 Git 仓库。

    返回选中的路径；用户取消或选了非法目录则返回 ``None``，由调用方决定接下来做什么。
    """
    selected = QFileDialog.getExistingDirectory(parent, "选择本地 Git 仓库")
    if not selected:
        return None
    if not (Path(selected) / ".git").exists():
        show_error(
            parent,
            "不是 Git 仓库",
            f"目录里没有 .git 文件夹：\n{selected}\n\n"
            "请选择仓库的根目录，而不是它的某个子文件夹。",
        )
        return None
    return selected


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)


class ExportDialog(QDialog):
    """导出格式选择。

    壳阶段只负责把用户的选择拿回来；真正写文件由 Wyh 的 reporters 模块完成。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("导出分析报告")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("选择要生成的格式："))

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
        """返回选中的格式标识，例如 ``["markdown"]``。"""
        formats = []
        if self.markdown.isChecked():
            formats.append("markdown")
        if self.html.isChecked():
            formats.append("html")
        if self.csv.isChecked():
            formats.append("csv")
        return formats
