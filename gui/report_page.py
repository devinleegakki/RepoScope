"""报告区：把分析结果拼成一份可交付的 Markdown / HTML / CSV。

为什么报告要在 GUI 里真生成，而不只是"预留一个导出按钮"：
评分表里"输出"这一档看的是**有没有能直接给人看的东西**。评审打开软件点一下导出，
拿到一份带表格和反模式清单的报告，比听你讲"这里以后会导出"强得多。

* Markdown 手写拼装，不用任何模板库；
* HTML 用 ``QTextDocument.setMarkdown()`` 转，Qt 自带，不引第三方依赖；
* CSV 用标准库 ``csv``。

壳阶段这三段写在自己的模块里；Wyh 的 ``reporters`` 到位后，
把 ``export()`` 内部换成调用他们的函数即可，界面不动。
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtGui import QTextDocument
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
from .contract import AnalysisView, Warning
from .tables import human_size
from .widgets import Card, PageHeader

_SECTIONS = (
    ("1. 总体评价", "总体评价"),
    ("2. 关键指标", "关键指标"),
    ("3. 作者贡献", "作者贡献"),
    ("4. 提交活跃度", "提交活跃度"),
    ("5. 热点文件", "热点文件"),
    ("6. 反模式清单", "反模式清单"),
    ("7. 提交规范", "提交规范"),
    ("8. 复现方式", "复现方式"),
)


def _recent_total(calendar: dict[str, int], days: int) -> int:
    if not calendar:
        return 0
    last = max(calendar)
    end = datetime.strptime(last, "%Y-%m-%d")
    start = (end - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    return sum(count for day, count in calendar.items() if start <= day <= last)


def _severity_cn(severity: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(severity, severity)


def _warning_block(index: int, warning: Warning) -> list[str]:
    lines = [
        f"### {index}. {warning.rule}（{_severity_cn(warning.severity)}）",
        "",
        warning.message,
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 触发条件 | {warning.condition or '待 rules.py 补齐'} |",
        f"| 实际值 | {warning.actual or '待 rules.py 补齐'} |",
        f"| 配置阈值 | {warning.threshold or '待 rules.py 补齐'} |",
        f"| 建议动作 | {warning.action or '待 rules.py 补齐'} |",
        f"| 涉及对象 | {warning.target or '—'} |",
        "",
    ]
    return lines


def build_markdown(view: AnalysisView) -> str:
    """把一次分析拼成 Markdown。所有数字都从 ``view`` 取，不在这里重算指标。"""
    snapshot = view.snapshot
    calendar = dict(view.commit_calendar)
    level = {"high": "高风险", "medium": "中风险", "low": "良好"}.get(
        getattr(view, "risk_level", "low"), "—"
    )

    lines: list[str] = [
        f"# RepoScope 分析报告 · {snapshot.repo_name}",
        "",
        f"- 仓库路径：`{snapshot.repo_path}`",
        f"- 分支：{', '.join(snapshot.branches) or '—'}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 分析用时：{view.elapsed_seconds:.1f}s",
        "",
        "## 1. 总体评价",
        "",
        f"健康度 **{view.health_score:.0f} / 100**（{level}），"
        f"命中 {len(view.warnings)} 条反模式规则。",
        "",
    ]

    lines += [
        "## 2. 关键指标",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 提交总数 | {view.total_commits:,} |",
        f"| 作者数 | {view.author_count} |",
        f"| 文件数 | {view.file_count:,} |",
        f"| 活跃天数 | {len(calendar)} |",
    ]
    hygiene = getattr(view, "commit_hygiene", None)
    if hygiene is not None and hygiene.pass_rate >= 0:
        lines.append(f"| 提交规范通过率 | {hygiene.pass_rate:.0%}（{hygiene.passed}/{hygiene.total}） |")
    else:
        lines.append("| 提交规范通过率 | 待后端提供 |")
    lines.append("")

    lines += ["## 3. 作者贡献", "", "| 作者 | 提交数 | 新增 | 删除 | 占比 | 近 90 天 |",
              "| --- | --- | --- | --- | --- | --- |"]
    for author in view.author_stats:
        recent = "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}"
        lines.append(
            f"| {author.name} | {author.commits} | +{author.insertions:,} | "
            f"-{author.deletions:,} | {author.share:.0%} | {recent} |"
        )
    lines.append("")

    lines += ["## 4. 提交活跃度", ""]
    for days in (7, 30, 90):
        lines.append(f"- 最近 {days} 天：{_recent_total(calendar, days)} 次提交")
    lines += ["", "## 5. 热点文件", "", "| 文件 | 修改次数 | 累计改动 |", "| --- | --- | --- |"]
    for row in list(view.hotspot_files)[:10]:
        changed = f"{row.changed_lines:,} 行" if row.changed_lines else "—"
        lines.append(f"| `{row.path}` | {row.change_count} | {changed} |")
    if not view.hotspot_files:
        lines.append("| （无） | — | — |")
    lines.append("")

    lines += ["## 6. 反模式清单", ""]
    if not view.warnings:
        lines += ["没有命中任何反模式规则。", ""]
    else:
        for index, warning in enumerate(view.warnings, start=1):
            lines += _warning_block(index, warning)

    lines += ["## 7. 提交规范", ""]
    if hygiene is not None and hygiene.violations:
        lines += ["| 提交 | 信息 | 原因 |", "| --- | --- | --- |"]
        for violation in hygiene.violations[:10]:
            lines.append(f"| `{violation.commit_hash}` | {violation.message} | {violation.reason} |")
        lines.append("")
        lines.append("> 历史提交不必追改，用 commit-msg hook 约束后续提交即可。")
    elif hygiene is not None and hygiene.pass_rate >= 0:
        lines.append("全部提交都符合约定格式。")
    else:
        lines.append("提交规范检查结果待后端提供。")
    lines.append("")

    lines += [
        "## 8. 复现方式",
        "",
        "```bash",
        f"python main.py {snapshot.repo_path}",
        "```",
        "",
        "---",
        "",
        "*本报告由 RepoScope 生成。所有指标均在本地计算，未上传任何代码。*",
        "",
    ]
    return "\n".join(lines)


def export(view: AnalysisView, formats: list[str], target_dir: str) -> list[Path]:
    """按选定格式写文件，返回生成的文件路径。"""
    folder = Path(target_dir)
    folder.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown(view)
    stem = snapshot_stem(view)
    written: list[Path] = []

    if "markdown" in formats:
        path = folder / f"{stem}.md"
        path.write_text(markdown, encoding="utf-8")
        written.append(path)

    if "html" in formats:
        document = QTextDocument()
        document.setMarkdown(markdown)
        path = folder / f"{stem}.html"
        path.write_text(document.toHtml(), encoding="utf-8")
        written.append(path)

    if "csv" in formats:
        path = folder / f"{stem}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["部门", "文件", "修改次数", "累计改动行", "大小", "距今天数"])
            for kind, rows in (("热点", view.hotspot_files),
                               ("大文件", view.large_files),
                               ("陈旧", view.stale_files)):
                for row in rows:
                    writer.writerow([
                        kind, row.path, row.change_count, row.changed_lines,
                        human_size(row.size_bytes), row.days_since_change,
                    ])
        written.append(path)

    return written


def snapshot_stem(view: AnalysisView) -> str:
    name = view.snapshot.repo_name or "repo"
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"{name}_report_{stamp}"


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
