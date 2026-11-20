"""报告区：把分析结果拼成一份可交付的 Markdown / HTML / CSV。

为什么报告要在 GUI 里真生成，而不只是"预留一个导出按钮"：
评分表里"输出"这一档看的是**有没有能直接给人看的东西**。评审打开软件点一下导出，
拿到一份带表格和反模式清单的报告，比听你讲"这里以后会导出"强得多。

* Markdown / HTML / CSV 全部由 ``reporters`` 生成，与命令行版本同源，
  保证界面导出和命令行导出的数据一致。
* 预览直接渲染 Markdown；导出文件本身是标准 HTML，不引入第三方依赖。
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
    ("1. 总体评价", "总体评价"),
    ("2. 关键指标", "关键指标"),
    ("3. 作者贡献", "作者贡献"),
    ("4. 提交活跃度", "提交活跃度"),
    ("5. 文件热点", "热点文件"),
    ("6. 大文件", "大文件"),
    ("7. 陈旧文件", "陈旧文件"),
    ("8. 反模式清单", "反模式清单"),
    ("9. 提交规范", "提交规范"),
    ("10. 复现方式", "复现方式"),
)

# 报告页只负责展示和导出，真正的拼装交给 reporters（和命令行共用）：
build_markdown = reporters.render_markdown
export = reporters.write_report

class ReportPage(QWidget):
    """报告区：左大纲、右预览、底部导出。"""

    def __init__(self) -> None:
        super().__init__()
        self._view: AnalysisView | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(12)

        self.header = PageHeader("报告区", "分析完成后这里会生成一份可直接交付的报告")
        outer.addWidget(self.header)

        body = QHBoxLayout()
        body.setSpacing(12)

        outline_card = Card()
        outline_layout = QVBoxLayout(outline_card)
        outline_layout.setContentsMargins(12, 12, 12, 12)
        outline_layout.setSpacing(8)
        title = QLabel("大纲")
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
        self.tabs.addTab(self.preview, "预览")
        self.tabs.addTab(self.source, "Markdown 源码")
        preview_layout.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        self.status = QLabel("尚未生成报告")
        self.status.setObjectName("pageHint")
        actions.addWidget(self.status)
        actions.addStretch(1)
        self.export_btn = QPushButton("导出报告…")
        self.export_btn.setObjectName("primary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export)
        actions.addWidget(self.export_btn)
        preview_layout.addLayout(actions)
        body.addWidget(preview_card, 3)

        outer.addLayout(body, 1)

    # -- 数据 ------------------------------------------------------------
    def set_data(self, view: AnalysisView | None) -> None:
        if view is None:
            return
        self._view = view
        markdown = build_markdown(view)
        self.preview.setMarkdown(markdown)
        self.source.setPlainText(markdown)
        self.status.setText(f"已生成 · {len(markdown.splitlines())} 行 · 可导出 Markdown / HTML / CSV")
        self.export_btn.setEnabled(True)
        self.header.set_hint(
            f"{view.snapshot.repo_name} · 共 {len(view.warnings)} 条反模式 · "
            f"健康度 {view.health_score:.0f}"
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
            dialogs.show_error(self, "没有选择格式", "请至少勾选一种导出格式。")
            return
        target = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not target:
            return
        try:
            written = export(self._view, formats, target)
        except OSError as exc:
            dialogs.show_error(self, "导出失败", f"写文件时出错：{exc}")
            return
        self.status.setText(f"已导出 {len(written)} 个文件到 {target}")
        dialogs.show_info(
            self,
            "导出完成",
            "\n".join(str(path) for path in written),
        )

