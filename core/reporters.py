"""报告生成核心：Markdown / HTML / CSV，同源同数据。

不依赖 PySide6，命令行、GUI 和批量分析都从此模块拿报告文本。
三种格式的数值全部来自同一个 ``AnalysisView``，做到
"三种报告数据一致"（组长文档 2.5 / 验收要求）。
"""

from __future__ import annotations

import csv
import html as html_mod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from gui.contract import AnalysisView  # 只依赖标准库 + models，可不装 PySide6 导入

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

CSV_COLUMNS = (
    "类别",
    "对象",
    "提交数",
    "占比",
    "修改次数",
    "累计改动行",
    "大小",
    "距今天数",
    "说明",
)


def human_size(size_bytes: int) -> str:
    """把字节数拼成人类可读的体积（可复用：GUI 表格与报告公用）。"""
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(max(size_bytes, 0))
    unit = units[0]
    for candidate in units[1:]:
        if value >= 1024:
            value /= 1024
            unit = candidate
        else:
            break
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.2f} {unit}"


def _severity_cn(severity: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "提示"}.get(severity, severity)


def _risk_cn(risk_level: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "良好"}.get(risk_level, "—")


def _recent_total(calendar: dict[str, int], days: int) -> int:
    if not calendar:
        return 0
    last = max(calendar)
    end = datetime.strptime(last, "%Y-%m-%d")
    start = (end - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    return sum(count for day, count in calendar.items() if start <= day <= last)


def _calendar_summary(calendar: dict[str, int]) -> dict:
    if not calendar:
        return {"active_days": 0, "busiest": "—"}
    busiest_day = max(calendar, key=lambda day: calendar[day])
    return {
        "active_days": len(calendar),
        "busiest": f"{busiest_day}（{calendar[busiest_day]} 次）",
    }


def _md_cell(text: object) -> str:
    """Markdown 表格单元格转义：竖线会拆列、换行会拆行。"""
    return str(text).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


# --- Markdown -------------------------------------------------------------


def render_markdown(view: AnalysisView) -> str:
    """把一次分析拼成 Markdown。所有数字都从 ``view`` 取，不在这里重算指标。"""
    snapshot = view.snapshot
    calendar = dict(view.commit_calendar)
    calendar_sum = _calendar_summary(calendar)
    hygiene = getattr(view, "commit_hygiene", None)
    risk_cn = _risk_cn(view.risk_level or "low")
    level_desc = {"high": "高风险", "medium": "中风险", "low": "良好"}[
        (view.risk_level or "low")
    ]

    lines: list[str] = [
        f"# RepoScope 分析报告 · {snapshot.repo_name}",
        "",
        f"- 仓库路径：`{snapshot.repo_path}`",
        f"- 分支：{', '.join(snapshot.branches) or '—'}",
        f"- 标签：{', '.join(snapshot.tags) or '—'}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 分析用时：{view.elapsed_seconds:.1f}s",
        "",
        "## 1. 总体评价",
        "",
        f"健康度 **{view.health_score:.0f} / 100**（{level_desc}），"
        f"命中 {len(view.warnings)} 条反模式规则，"
        f"风险等级：{risk_cn}。",
        "",
        "## 2. 关键指标",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 提交总数 | {view.total_commits:,} |",
        f"| 作者数 | {view.author_count} |",
        f"| 文件数 | {view.file_count:,} |",
        f"| 活跃天数 | {calendar_sum['active_days']} |",
        f"| 风险等级 | {risk_cn} |",
    ]
    if hygiene is not None and hygiene.pass_rate >= 0:
        lines.append(
            f"| 提交规范通过率 | {hygiene.pass_rate:.0%}（{hygiene.passed}/{hygiene.total}） |"
        )
    else:
        lines.append("| 提交规范通过率 | 待后端提供 |")
    lines.append("")

    lines += [
        "## 3. 作者贡献",
        "",
        "| 作者 | 提交数 | 新增 | 删除 | 占比 | 近 90 天 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for author in view.author_stats:
        recent = "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}"
        lines.append(
            f"| {_md_cell(author.name)} | {author.commits} | +{author.insertions:,} | "
            f"-{author.deletions:,} | {author.share:.0%} | {recent} |"
        )
    lines.append("")

    lines += ["## 4. 提交活跃度", ""]
    for days in (7, 30, 90):
        lines.append(f"- 最近 {days} 天：{_recent_total(calendar, days)} 次提交")
    lines.append(f"- 最活跃的一天：{calendar_sum['busiest']}")
    lines.append("")

    lines += ["## 5. 文件热点", "", "| 文件 | 修改次数 | 累计改动 | 类型 | 二进制 |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.hotspot_files)[:100]:
        changed = f"{row.changed_lines:,} 行" if row.changed_lines else "—"
        binary = "是" if row.is_binary else "—"
        lines.append(f"| `{row.path}` | {row.change_count} | {changed} | {row.file_type or '—'} | {binary} |")
    if not view.hotspot_files:
        lines.append("| （无） | — | — | — | — |")
    lines.append("")

    lines += ["## 6. 大文件", "", "| 文件 | 大小 | 类型 | 二进制 | 修改次数 |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.large_files)[:100]:
        binary = "是" if row.is_binary else "—"
        lines.append(
            f"| `{row.path}` | {human_size(row.size_bytes)} | {row.file_type or '—'} | "
            f"{binary} | {row.change_count} |"
        )
    if not view.large_files:
        lines.append("| （无） | — | — | — | — |")
    lines.append("")

    lines += ["## 7. 陈旧文件", "", "| 文件 | 陈旧天数 | 大小 | 类型 | 修改次数 |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.stale_files)[:100]:
        lines.append(
            f"| `{row.path}` | {row.days_since_change} 天 | "
            f"{human_size(row.size_bytes)} | {row.file_type or '—'} | {row.change_count} |"
        )
    if not view.stale_files:
        lines.append("| （无） | — | — | — | — |")
    lines.append("")

    quality = getattr(view, "code_quality", None)
    ownership = getattr(view, "ownership", None)
    dependencies = getattr(view, "dependencies", None)
    findings = getattr(view, "security_findings", ())
    if quality is not None:
        lines += ["## 8. 代码质量", "", "| 指标 | 数值 |", "| --- | --- |",
                  f"| Python 文件 | {quality.python_files} |", f"| 代码行数 | {quality.lines:,} |",
                  f"| 函数 / 类 | {quality.functions} / {quality.classes} |",
                  f"| 测试文件比例 | {quality.test_ratio:.0%} |",
                  f"| TODO/FIXME | {quality.todo_count} |", f"| 裸 except | {quality.bare_except_count} |", ""]
    if ownership is not None:
        lines += ["## 9. 文件级协作风险", "", f"高风险单作者文件：{len(ownership.high_risk_files)}", ""]
        lines += ["| 文件 | 修改次数 | 作者数 | 主要作者 | 集中度 |", "| --- | --- | --- | --- | --- |"]
        for row in ownership.high_risk_files[:50]:
            lines.append(f"| `{row.path}` | {row.changes} | {row.author_count} | {_md_cell(row.top_author)} | {row.top_author_ratio:.0%} |")
        lines.append("")
    if dependencies is not None or findings:
        lines += ["## 10. 依赖与安全", ""]
        if dependencies is not None:
            lines += [f"依赖清单：{len(dependencies.dependencies)}，未固定：{len(dependencies.unpinned)}，重复：{len(dependencies.duplicates)}，锁文件：{len(dependencies.lockfiles)}。", ""]
        lines.append(f"疑似安全发现：{len(findings)}。" if findings else "未发现疑似硬编码凭据。")
        lines.append("")

    lines += ["## 11. 反模式清单", ""]
    if not view.warnings:
        lines += ["没有命中任何反模式规则。", ""]
    else:
        for index, warning in enumerate(view.warnings, start=1):
            lines += _warning_block(index, warning)

    lines += ["## 12. 提交规范", ""]
    if hygiene is None:
        lines.append("提交规范检查结果待后端提供。")
    elif hygiene.pass_rate < 0:
        lines.append("提交规范检查尚未执行。")
    elif hygiene.violations:
        lines += ["| 提交 | 信息 | 原因 |", "| --- | --- | --- |"]
        for violation in hygiene.violations[:20]:
            lines.append(
                f"| `{violation.commit_hash}` | {_md_cell(violation.message)} | "
                f"{_md_cell(violation.reason)} |"
            )
        lines.append("")
        lines.append(
            "> 通过率 {pass_rate:.0%}（{passed}/{total}）".format(
                pass_rate=hygiene.pass_rate, passed=hygiene.passed, total=hygiene.total
            )
        )
        lines.append(
            "> 历史提交不必追改，用 commit-msg hook 约束后续提交即可。模式："
            f"`{hygiene.pattern or '（未配置）'}`"
        )
    else:
        lines.append(f"全部 {hygiene.total} 个提交都符合约定格式。")
    lines.append("")

    lines += [
        "## 13. 复现方式",
        "",
        "```bash",
        f"python main.py analyze {snapshot.repo_path}",
        "```",
        "",
        "---",
        "",
        "*本报告由 RepoScope 生成。所有指标均在本地计算，未上传任何代码。*",
        "",
    ]
    return "\n".join(lines)


def _warning_block(index: int, warning: Warning) -> list[str]:
    return [
        f"### {index}. {warning.rule}（{_severity_cn(warning.severity)}）",
        "",
        warning.message or "—",
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 触发条件 | {warning.condition or '待后端提供'} |",
        f"| 实际值 | {warning.actual or '待后端提供'} |",
        f"| 配置阈值 | {warning.threshold or '待后端提供'} |",
        f"| 建议动作 | {warning.action or '待后端提供'} |",
        f"| 涉及对象 | {warning.target or '—'} |",
        "",
    ]


# --- HTML -----------------------------------------------------------------


def render_html(view: AnalysisView) -> str:
    """把一次分析拼成一份可离线打开的 HTML 报告，样式内嵌，不依赖外部资源。"""
    snapshot = view.snapshot
    calendar = dict(view.commit_calendar)
    calendar_sum = _calendar_summary(calendar)
    hygiene = getattr(view, "commit_hygiene", None)
    risk_cn = _risk_cn(view.risk_level or "low")
    level_key = (view.risk_level or "low")
    level_desc = {"high": "高风险", "medium": "中风险", "low": "良好"}[level_key]
    severity_css = {"high": "sev-high", "medium": "sev-medium", "low": "sev-low"}

    body: list[str] = []
    body.append(f'<h1>RepoScope 分析报告 · {_escape(snapshot.repo_name)}</h1>')
    body.append(
        f'<p class="meta"><strong>仓库路径：</strong>{_escape(snapshot.repo_path)}<br>'
        f'<strong>分支：</strong>{_escape(", ".join(snapshot.branches) or "—")}<br>'
        f'<strong>标签：</strong>{_escape(", ".join(snapshot.tags) or "—")}<br>'
        f'<strong>生成时间：</strong>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>'
        f'<strong>分析用时：</strong>{view.elapsed_seconds:.1f}秒</p>'
    )

    body.append('<section><h2>1. 总体评价</h2>')
    body.append(
        f'<p>健康度 <strong>{view.health_score:.0f} / 100</strong>（{level_desc}），'
        f'命中 <strong>{len(view.warnings)}</strong> 条反模式规则，'
        f'风险等级：<span class="badge badge-{level_key}">{risk_cn}</span>。</p>'
    )
    body.append("</section>")

    body.append('<section><h2>2. 关键指标</h2><table>')
    body.append("<tr><th>指标</th><th>数值</th></tr>")
    body.append(f"<tr><td>提交总数</td><td>{view.total_commits:,}</td></tr>")
    body.append(f"<tr><td>作者数</td><td>{view.author_count}</td></tr>")
    body.append(f"<tr><td>文件数</td><td>{view.file_count:,}</td></tr>")
    body.append(f"<tr><td>活跃天数</td><td>{calendar_sum['active_days']}</td></tr>")
    body.append(f"<tr><td>风险等级</td><td>{risk_cn}</td></tr>")
    if hygiene is not None and hygiene.pass_rate >= 0:
        body.append(
            f"<tr><td>提交规范通过率</td><td>{hygiene.pass_rate:.0%} "
            f"({hygiene.passed}/{hygiene.total})</td></tr>"
        )
    else:
        body.append("<tr><td>提交规范通过率</td><td>待后端提供</td></tr>")
    body.append("</table></section>")

    body.append(_table_section(
        "3. 作者贡献",
        ["作者", "提交数", "新增", "删除", "占比", "近 90 天"],
        [
            [
                _escape(author.name),
                str(author.commits),
                f"+{author.insertions:,}",
                f"-{author.deletions:,}",
                f"{author.share:.0%}",
                "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}",
            ]
            for author in view.author_stats
        ],
    ))

    body.append('<section><h2>4. 提交活跃度</h2><ul>')
    for days in (7, 30, 90):
        body.append(f"<li>最近 {days} 天：{_recent_total(calendar, days)} 次提交</li>")
    body.append(f"<li>最活跃的一天：{_escape(calendar_sum['busiest'])}</li>")
    body.append("</ul></section>")

    body.append(_table_section(
        "5. 文件热点",
        ["文件", "修改次数", "累计改动", "类型", "二进制"],
        [
            [
                f"`{_escape(row.path)}`",
                str(row.change_count),
                f"{row.changed_lines:,} 行" if row.changed_lines else "—",
                row.file_type or "—",
                "是" if row.is_binary else "—",
            ]
            for row in list(view.hotspot_files)[:100]
        ],
        empty="（无）",
    ))

    body.append(_table_section(
        "6. 大文件",
        ["文件", "大小", "类型", "二进制", "修改次数"],
        [
            [
                f"`{_escape(row.path)}`",
                human_size(row.size_bytes),
                row.file_type or "—",
                "是" if row.is_binary else "—",
                str(row.change_count),
            ]
            for row in list(view.large_files)[:100]
        ],
        empty="（无）",
    ))

    body.append(_table_section(
        "7. 陈旧文件",
        ["文件", "陈旧天数", "大小", "类型", "修改次数"],
        [
            [
                f"`{_escape(row.path)}`",
                f"{row.days_since_change} 天",
                human_size(row.size_bytes),
                row.file_type or "—",
                str(row.change_count),
            ]
            for row in list(view.stale_files)[:100]
        ],
        empty="（无）",
    ))

    body.append('<section><h2>8. 反模式清单</h2>')
    if not view.warnings:
        body.append("<p>没有命中任何反模式规则。</p>")
    else:
        for index, warning in enumerate(view.warnings, start=1):
            cls = severity_css.get(warning.severity, "sev-low")
            body.append(
                f'<div class="warning {cls}">'
                f'<strong>{index}. {_escape(warning.rule)}</strong> '
                f'<span class="badge">{_severity_cn(warning.severity)}</span>'
                f'<p>{_escape(warning.message or "—")}</p>'
                f"<table><tr><th>触发条件</th><td>{_escape(warning.condition or '待后端提供')}</td></tr>"
                f"<tr><th>实际值</th><td>{_escape(warning.actual or '待后端提供')}</td></tr>"
                f"<tr><th>配置阈值</th><td>{_escape(warning.threshold or '待后端提供')}</td></tr>"
                f"<tr><th>建议动作</th><td>{_escape(warning.action or '待后端提供')}</td></tr>"
                f"<tr><th>涉及对象</th><td>{_escape(warning.target or '—')}</td></tr></table>"
                f"</div>"
            )
    body.append("</section>")

    body.append('<section><h2>9. 提交规范</h2>')
    if hygiene is None:
        body.append("<p>提交规范检查结果待后端提供。</p>")
    elif hygiene.pass_rate < 0:
        body.append("<p>提交规范检查尚未执行。</p>")
    elif hygiene.violations:
        body.append("<table><tr><th>提交</th><th>信息</th><th>原因</th></tr>")
        for violation in hygiene.violations[:20]:
            body.append(
                f"<tr><td>`{violation.commit_hash}`</td>"
                f"<td>{_escape(violation.message)}</td>"
                f"<td>{_escape(violation.reason)}</td></tr>"
            )
        body.append("</table>")
        body.append(
            f"<p>通过率 <strong>{hygiene.pass_rate:.0%}</strong> "
            f"({hygiene.passed}/{hygiene.total})，"
            f"模式：<code>{_escape(hygiene.pattern or '（未配置）')}</code>"
        )
        body.append(
            "<br>历史提交不必追改，用 commit-msg hook 约束后续提交即可。</p>"
        )
    else:
        body.append(f"<p>全部 {hygiene.total} 个提交都符合约定格式。</p>")
    body.append("</section>")

    body.append('<section><h2>10. 复现方式</h2>')
    body.append(
        f'<pre><code>python main.py analyze {_escape(snapshot.repo_path)}</code></pre>'
        '<hr><p><small>本报告由 RepoScope 生成。所有指标均在本地计算，未上传任何代码。</small></p>'
    )
    body.append("</section>")

    css = """
    :root { --bg: #ffffff; --card: #f6f8fb; --line: #d9dee6; --text: #1f2937; }
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue",
        "PingFang SC", "Microsoft YaHei", sans-serif; color: var(--text);
        line-height: 1.55; padding: 24px; max-width: 1100px; margin: auto; }
    h1 { font-size: 24px; border-bottom: 2px solid var(--line); padding-bottom: 8px; }
    h2 { font-size: 17px; margin: 22px 0 10px; color: #2563eb; }
    p { margin: 6px 0; }
    .meta { color: #4b5563; font-size: 13px; border-left: 4px solid #2563eb;
        padding-left: 10px; background: var(--card); padding: 10px; }
    table { border-collapse: collapse; width: 100%; margin: 8px 0 16px; font-size: 13px; }
    th, td { border: 1px solid var(--line); padding: 5px 8px; text-align: left; }
    th { background: var(--card); }
    .badge { display: inline-block; padding: 1px 7px; border-radius: 9px; font-size: 12px;
        font-weight: 600; color: #fff; }
    .badge-low { background: #0ea5e9; } .badge-medium { background: #f59e0b; }
    .badge-high { background: #ef4444; }
    .warning { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px;
        margin: 10px 0; background: #fffbf0; }
    .warning.sev-high { border-color: #fca5a5; background: #fef2f2; }
    .warning.sev-medium { border-color: #fdba74; background: #fff7ed; }
    .warning.sev-low { border-color: #bfdbfe; background: #eff6ff; }
    pre { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow-x: auto; }
    hr { border: none; border-top: 1px solid var(--line); margin: 24px 0; }
    small { color: #6b7280; }
    """
    return (
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>RepoScope - {snapshot.repo_name}</title>"
        f"<style>{css}</style></head><body>{''.join(body)}</body></html>"
    )


def _table_section(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]],
                   empty: str = "（无）") -> str:
    cells = "".join(f"<th>{html_mod.escape(h)}</th>" for h in headers)
    if not rows:
        colspan = len(headers)
        body_rows = f"<tr><td colspan=\"{colspan}\">{empty}</td></tr>"
    else:
        body_rows = "".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
        )
    return (
        f'<section><h2>{_escape(title)}</h2><table>'
        f"<tr>{cells}</tr>{body_rows}</table></section>"
    )


def _escape(text: str) -> str:
    return html_mod.escape(str(text))


# --- CSV ------------------------------------------------------------------


def render_csv(view: AnalysisView) -> str:
    """把一次分析拼成 CSV，供 Excel / 后续数据处理使用。"""

    def author_rows():
        out = []
        for author in view.author_stats:
            recent = "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}"
            out.append(
                (
                    "作者",
                    author.name,
                    str(author.commits),
                    f"{author.share:.0%}",
                    "—",
                    "—",
                    f"+{author.insertions:,}",
                    f"-{author.deletions:,}",
                    recent,
                )
            )
        return out

    def file_rows(kind: str, rows: Sequence):
        out = []
        for row in rows:
            binary_suffix = " · 二进制" if row.is_binary else ""
            out.append(
                (
                    kind,
                    row.path,
                    "—",
                    "—",
                    str(row.change_count),
                    f"{row.changed_lines:,}" if row.changed_lines else "—",
                    human_size(row.size_bytes),
                    str(row.days_since_change) if row.days_since_change else "—",
                    f"{row.file_type or '—'}{binary_suffix}",
                )
            )
        return out

    out_rows: list[tuple] = []
    out_rows += author_rows()
    out_rows += file_rows("热点文件", view.hotspot_files)
    out_rows += file_rows("大文件", view.large_files)
    out_rows += file_rows("陈旧文件", view.stale_files)
    for index, warning in enumerate(view.warnings, start=1):
        out_rows.append(
            ("反模式警告", f"{index}. {warning.rule}", "—", "—", "—", "—",
             "—", "—",
             f"{warning.severity} · {warning.message or '—'} | 条件：{warning.condition or '—'} | "
             f"实际值：{warning.actual or '—'} | 阈值：{warning.threshold or '—'} | "
             f"动作：{warning.action or '—'}"),
        )
    out_rows.append(
        ("汇总", "健康度", f"{view.health_score:.0f}", "—", "—", "—", "—", "—",
         f"风险：{_risk_cn(view.risk_level or 'low')} · 提交 {view.total_commits} · 作者 {view.author_count}")
    )

    lines = [",".join(_csv_field(c) for c in CSV_COLUMNS)]
    for row in out_rows:
        lines.append(",".join(_csv_field(c) for c in row))
    return "\n".join(lines) + "\n"


def _csv_field(value: str) -> str:
    value = str(value)
    if any(ch in value for ch in (",", '"', "\n", "\r")):
        return '"' + value.replace('"', '""') + '"'
    return value


# --- 写入 -----------------------------------------------------------------


def write_report(view: AnalysisView, formats: Sequence[str], output_dir: str | Path,
                 *, stem: str | None = None) -> list[Path]:
    """按选定格式把报告写进目录，返回生成的文件路径列表。"""
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    if stem is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        stem = f"{view.snapshot.repo_name}_report_{stamp}"

    renderer = {
        "markdown": render_markdown,
        "md": render_markdown,
        "html": render_html,
        "csv": render_csv,
    }

    written: list[Path] = []
    for fmt in formats:
        key = fmt.lower()
        if key not in renderer:
            raise ValueError(f"不支持的报告格式：{fmt}（可选：markdown、html、csv）")
        ext = {"markdown": ".md", "md": ".md", "html": ".html", "csv": ".csv"}[key]
        content = renderer[key](view)
        path = folder / f"{stem}{ext}"
        path.write_text(content, encoding="utf-8-sig" if key == "csv" else "utf-8",
                        newline="")
        written.append(path)
    return written


# --- 批量汇总 -------------------------------------------------------------


def render_summary_markdown(summaries: Sequence, failures: Sequence = (),
                            generated_at: datetime | None = None) -> str:
    """多仓库对比表：每行一个仓库，失败的仓库单独列出来。"""
    lines: list[str] = [
        "# RepoScope 批量分析汇总",
        "",
        f"- 生成时间：{(generated_at or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 仓库总数：{len(summaries) + len(failures)}，成功：{len(summaries)}，失败：{len(failures)}",
        "",
        "| 仓库 | 路径 | 提交数 | 作者数 | 健康度 | 热点文件 | 陈旧文件 | 风险等级 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in summaries:
        lines.append(
            f"| {_md_cell(summary.repo_name)} | {_md_cell(summary.path)} | "
            f"{summary.commits:,} | {summary.authors} | {summary.health_score:.0f} | "
            f"{summary.hotspot_count} | {summary.stale_count} | "
            f"{_risk_cn(summary.risk_level)} |"
        )
    lines.append("")
    if failures:
        lines.append("| 分析失败的仓库 | 原因 |")
        lines.append("| --- | --- |")
        for failure in failures:
            name = getattr(failure, "repo_name", failure.path)
            lines.append(f"| {_md_cell(name)} | {_md_cell(failure.error)} |")
        lines.append("")
    lines += [
        "---",
        "",
        "*本汇总由 RepoScope 生成。所有指标均在本地计算，未上传任何代码。*",
        "",
    ]
    return "\n".join(lines)


def render_summary_csv(rows: Sequence) -> str:
    """多仓库汇总 CSV；行对象需提供 repo_name / path / commits / authors /
    health_score / hotspot_count / stale_count / risk_level。"""
    lines = [
        ",".join(_csv_field(c) for c in (
            "仓库", "路径", "提交数", "作者数", "健康度", "热点文件", "陈旧文件", "风险等级",
        ))
    ]
    for row in rows:
        lines.append(",".join(_csv_field(str(getattr(row, name))) for name in (
            "repo_name", "path", "commits", "authors", "health_score",
            "hotspot_count", "stale_count", "risk_level",
        )))
    return "\n".join(lines) + "\n"
