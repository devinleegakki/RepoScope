"""Render an ``AnalysisView`` as Markdown, HTML, or CSV reports.

All renderers consume the same view model so GUI previews and CLI exports stay
consistent.

Notes PySide6，NotesGUI analysis
Notes ``AnalysisView``，Notes
"report"（Notes 2.5 / Notes
"""

from __future__ import annotations

import html as html_mod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Sequence

from gui.contract import AnalysisView  # Notes + models，Notes PySide6 Notes

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

CSV_COLUMNS = (
    "Category",
    "Name",
    "commits",
    "ratio",
    "Insertions",
    "Deletions",
    "size",
    "Notes",
    "information",
)


def human_size(size_bytes: int) -> str:
    """NotesGUI report"""
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
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(severity, severity)


def _risk_cn(risk_level: str) -> str:
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(risk_level, "—")


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
        "busiest": f"{busiest_day} ({calendar[busiest_day]} commits)",
    }


def _md_cell(text: object) -> str:
    """Markdown Notes"""
    return str(text).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


# --- Markdown -------------------------------------------------------------


def render_markdown(view: AnalysisView) -> str:
    """analysis Markdown。Notes ``view`` Notes"""
    snapshot = view.snapshot
    calendar = dict(view.commit_calendar)
    calendar_sum = _calendar_summary(calendar)
    hygiene = getattr(view, "commit_hygiene", None)
    risk_cn = _risk_cn(view.risk_level or "low")
    level_desc = {"high": "High risk", "medium": "Medium risk", "low": "Low risk"}[
        (view.risk_level or "low")
    ]

    lines: list[str] = [
        f"# RepoScope analysis · {snapshot.repo_name}",
        "",
        f"- Repository: `{snapshot.repo_path}`",
        f"- Branches: {', '.join(snapshot.branches) or '—'}",
        f"- Tags: {', '.join(snapshot.tags) or '—'}",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Duration: {view.elapsed_seconds:.1f}s",
        "",
        "## 1. Overview",
        "",
        f"Health score: **{view.health_score:.0f} / 100** ({level_desc}); "
        f"{len(view.warnings)} anti-patterns; overall risk: **{risk_cn}**.",
        "",
        "## 2. Repository summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| commits | {view.total_commits:,} |",
        f"| authors | {view.author_count} |",
        f"| files | {view.file_count:,} |",
        f"| Active days | {calendar_sum['active_days']} |",
        f"| Risk level | {risk_cn} |",
    ]
    if hygiene is not None and hygiene.pass_rate >= 0:
        lines.append(
            f"| Commit quality | {hygiene.pass_rate:.0%} ({hygiene.passed}/{hygiene.total}) |"
        )
    else:
        lines.append("| Commit quality | Pending |")
    lines.append("")

    lines += [
        "## 3. authors",
        "",
        "| Author | Commits | Insertions | Deletions | Share | Recent 90-day share |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for author in view.author_stats:
        recent = "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}"
        lines.append(
            f"| {_md_cell(author.name)} | {author.commits} | +{author.insertions:,} | "
            f"-{author.deletions:,} | {author.share:.0%} | {recent} |"
        )
    lines.append("")

    lines += ["## 4. commits", ""]
    for days in (7, 30, 90):
        lines.append(f"- Last {days} days: {_recent_total(calendar, days)} commits")
    lines.append(f"- Busiest day: {calendar_sum['busiest']}")
    lines.append("")

    lines += ["## 5. Hotspot files", "", "| File | Changes | Changed lines | Type | Binary |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.hotspot_files)[:100]:
        changed = f"{row.changed_lines:,}" if row.changed_lines else "—"
        binary = "Yes" if row.is_binary else "No"
        lines.append(f"| `{row.path}` | {row.change_count} | {changed} | {row.file_type or '—'} | {binary} |")
    if not view.hotspot_files:
        lines.append("| No files | — | — | — | — |")
    lines.append("")

    lines += ["## 6. Large files", "", "| File | Size | Type | Binary | Changes |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.large_files)[:100]:
        binary = "Yes" if row.is_binary else "No"
        lines.append(
            f"| `{row.path}` | {human_size(row.size_bytes)} | {row.file_type or '—'} | "
            f"{binary} | {row.change_count} |"
        )
    if not view.large_files:
        lines.append("| No files | — | — | — | — |")
    lines.append("")

    lines += ["## 7. Stale files", "", "| File | Days since change | Size | Type | Changes |",
              "| --- | --- | --- | --- | --- |"]
    for row in list(view.stale_files)[:100]:
        lines.append(
            f"| `{row.path}` | {row.days_since_change}  days | "
            f"{human_size(row.size_bytes)} | {row.file_type or '—'} | {row.change_count} |"
        )
    if not view.stale_files:
        lines.append("| No files | — | — | — | — |")
    lines.append("")

    quality = getattr(view, "code_quality", None)
    ownership = getattr(view, "ownership", None)
    dependencies = getattr(view, "dependencies", None)
    findings = getattr(view, "security_findings", ())
    if quality is not None:
        lines += ["## 8. Code quality", "", "| Metric | Value |", "| --- | --- |",
                  f"| Python files | {quality.python_files} |", f"| code | {quality.lines:,} |",
                  f"| Functions / classes | {quality.functions} / {quality.classes} |",
                  f"| Test file ratio | {quality.test_ratio:.0%} |",
                  f"| TODO/FIXME | {quality.todo_count} |", f"| Bare except blocks | {quality.bare_except_count} |", ""]
    if ownership is not None:
        lines += ["## 9. Ownership risks", "", f"High-risk files: {len(ownership.high_risk_files)}", ""]
        lines += ["| File | Changes | Authors | Top author | Top author share |", "| --- | --- | --- | --- | --- |"]
        for row in ownership.high_risk_files[:50]:
            lines.append(f"| `{row.path}` | {row.changes} | {row.author_count} | {_md_cell(row.top_author)} | {row.top_author_ratio:.0%} |")
        lines.append("")
    if dependencies is not None or findings:
        lines += ["## 10. Dependencies and security", ""]
        if dependencies is not None:
            lines += [f"Dependencies: {len(dependencies.dependencies)}; unpinned: {len(dependencies.unpinned)}; duplicates: {len(dependencies.duplicates)}; lockfiles: {len(dependencies.lockfiles)}.", ""]
        lines.append(f"Security findings: {len(findings)}." if findings else "No security findings.")
        lines.append("")

    lines += ["## 11. anti-patterns", ""]
    if not view.warnings:
        lines += ["No anti-patterns detected.", ""]
    else:
        for index, warning in enumerate(view.warnings, start=1):
            lines += _warning_block(index, warning)

    lines += ["## 12. Commit message quality", ""]
    if hygiene is None:
        lines.append("Commit quality data is unavailable.")
    elif hygiene.pass_rate < 0:
        lines.append("Commit quality data is unavailable.")
    elif hygiene.violations:
        lines += ["| Commit | Message | Reason |", "| --- | --- | --- |"]
        for violation in hygiene.violations[:20]:
            lines.append(
                f"| `{violation.commit_hash}` | {_md_cell(violation.message)} | "
                f"{_md_cell(violation.reason)} |"
            )
        lines.append("")
        lines.append(
            "> passed {pass_rate:.0%}（{passed}/{total}）".format(
                pass_rate=hygiene.pass_rate, passed=hygiene.passed, total=hygiene.total
            )
        )
        lines.append(
            "> Commit messages are checked against the configured pattern "
            f"`{hygiene.pattern or 'not configured'}`"
        )
    else:
        lines.append(f"All {hygiene.total} commits match the configured pattern.")
    lines.append("")

    lines += [
        "## 13. Reproduce this report",
        "",
        "```bash",
        f"python main.py analyze {snapshot.repo_path}",
        "```",
        "",
        "---",
        "",
        "*Generated locally by RepoScope.*",
        "",
    ]
    return "\n".join(lines)


def _warning_block(index: int, warning: Warning) -> list[str]:
    return [
        f"### {index}. {warning.rule} ({_severity_cn(warning.severity)})",
        "",
        warning.message or "—",
        "",
        "| Evidence | Value |",
        "| --- | --- |",
        f"| Condition | {warning.condition or 'Pending'} |",
        f"| Observed value | {warning.actual or 'Pending'} |",
        f"| Threshold | {warning.threshold or 'Pending'} |",
        f"| Suggested action | {warning.action or 'Pending'} |",
        f"| Target | {warning.target or '—'} |",
        "",
    ]


# --- HTML -----------------------------------------------------------------


def render_html(view: AnalysisView) -> str:
    """analysis HTML report"""
    snapshot = view.snapshot
    calendar = dict(view.commit_calendar)
    calendar_sum = _calendar_summary(calendar)
    hygiene = getattr(view, "commit_hygiene", None)
    risk_cn = _risk_cn(view.risk_level or "low")
    level_key = (view.risk_level or "low")
    level_desc = {"high": "High risk", "medium": "Medium risk", "low": "Low risk"}[level_key]
    severity_css = {"high": "sev-high", "medium": "sev-medium", "low": "sev-low"}

    body: list[str] = []
    body.append(f'<h1>RepoScope analysis · {_escape(snapshot.repo_name)}</h1>')
    body.append(
        f'<p class="meta"><strong>repository</strong>{_escape(snapshot.repo_path)}<br>'
        f'<strong>branches</strong>{_escape(", ".join(snapshot.branches) or "—")}<br>'
        f'<strong>tags</strong>{_escape(", ".join(snapshot.tags) or "—")}<br>'
        f'<strong>time</strong>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>'
        f'<strong>Duration</strong>{view.elapsed_seconds:.1f}s</p>'
    )

    body.append('<section><h2>1. Overview</h2>')
    body.append(
        f'<p>health <strong>{view.health_score:.0f} / 100</strong>（{level_desc}），'
        f'medium <strong>{len(view.warnings)}</strong> rules'
        f'risk<span class="badge badge-{level_key}">{risk_cn}</span>。</p>'
    )
    body.append("</section>")

    body.append('<section><h2>2. Repository summary</h2><table>')
    body.append("<tr><th>Metric</th><th>Value</th></tr>")
    body.append(f"<tr><td>commits</td><td>{view.total_commits:,}</td></tr>")
    body.append(f"<tr><td>authors</td><td>{view.author_count}</td></tr>")
    body.append(f"<tr><td>files</td><td>{view.file_count:,}</td></tr>")
    body.append(f"<tr><td> days</td><td>{calendar_sum['active_days']}</td></tr>")
    body.append(f"<tr><td>risk</td><td>{risk_cn}</td></tr>")
    if hygiene is not None and hygiene.pass_rate >= 0:
        body.append(
            f"<tr><td>commits</td><td>{hygiene.pass_rate:.0%} "
            f"({hygiene.passed}/{hygiene.total})</td></tr>"
        )
    else:
        body.append("<tr><td>commits</td><td>pending</td></tr>")
    body.append("</table></section>")

    body.append(_table_section(
        "3. authors",
        ["Author", "Commits", "Insertions", "Deletions", "Share", "Recent 90-day share"],
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

    body.append('<section><h2>4. commits</h2><ul>')
    for days in (7, 30, 90):
        body.append(f"<li>recent {days}  days{_recent_total(calendar, days)} commits</li>")
    body.append(f"<li>of{_escape(calendar_sum['busiest'])}</li>")
    body.append("</ul></section>")

    body.append(_table_section(
        "5. Hotspot files",
        ["File", "Changes", "Changed lines", "Type", "Binary"],
        [
            [
                f"`{_escape(row.path)}`",
                str(row.change_count),
                f"{row.changed_lines:,}" if row.changed_lines else "—",
                row.file_type or "—",
                "Yes" if row.is_binary else "No",
            ]
            for row in list(view.hotspot_files)[:100]
        ],
        empty="（none",
    ))

    body.append(_table_section(
        "6. Large files",
        ["File", "Size", "Type", "Binary", "Changes"],
        [
            [
                f"`{_escape(row.path)}`",
                human_size(row.size_bytes),
                row.file_type or "—",
                "Yes" if row.is_binary else "No",
                str(row.change_count),
            ]
            for row in list(view.large_files)[:100]
        ],
        empty="（none",
    ))

    body.append(_table_section(
        "7. Stale files",
        ["File", "Days since change", "Size", "Type", "Changes"],
        [
            [
                f"`{_escape(row.path)}`",
                f"{row.days_since_change}  days",
                human_size(row.size_bytes),
                row.file_type or "—",
                str(row.change_count),
            ]
            for row in list(view.stale_files)[:100]
        ],
        empty="（none",
    ))

    body.append('<section><h2>8. anti-patterns</h2>')
    if not view.warnings:
        body.append("<p>No anti-patterns detected.</p>")
    else:
        for index, warning in enumerate(view.warnings, start=1):
            cls = severity_css.get(warning.severity, "sev-low")
            body.append(
                f'<div class="warning {cls}">'
                f'<strong>{index}. {_escape(warning.rule)}</strong> '
                f'<span class="badge">{_severity_cn(warning.severity)}</span>'
                f'<p>{_escape(warning.message or "—")}</p>'
                f"<table><tr><th> items</th><td>{_escape(warning.condition or 'pending')}</td></tr>"
                f"<tr><th>value</th><td>{_escape(warning.actual or 'pending')}</td></tr>"
                f"<tr><th>configuration</th><td>{_escape(warning.threshold or 'pending')}</td></tr>"
                f"<tr><th>Suggested action</th><td>{_escape(warning.action or 'Pending')}</td></tr>"
                f"<tr><th>Target</th><td>{_escape(warning.target or '—')}</td></tr></table>"
                f"</div>"
            )
    body.append("</section>")

    body.append('<section><h2>9. commits</h2>')
    if hygiene is None:
        body.append("<p>Commit quality data is unavailable.</p>")
    elif hygiene.pass_rate < 0:
        body.append("<p>Commit quality data is unavailable.</p>")
    elif hygiene.violations:
        body.append("<table><tr><th>Commit</th><th>Message</th><th>Reason</th></tr>")
        for violation in hygiene.violations[:20]:
            body.append(
                f"<tr><td>`{violation.commit_hash}`</td>"
                f"<td>{_escape(violation.message)}</td>"
                f"<td>{_escape(violation.reason)}</td></tr>"
            )
        body.append("</table>")
        body.append(
            f"<p>passed <strong>{hygiene.pass_rate:.0%}</strong> "
            f"({hygiene.passed}/{hygiene.total})，"
            f"Pattern: <code>{_escape(hygiene.pattern or 'not configured')}</code>"
        )
        body.append(
            "<br>commits commit-msg hook commits</p>"
        )
    else:
        body.append(f"<p>All {hygiene.total} commits match the configured pattern.</p>")
    body.append("</section>")

    body.append('<section><h2>10. Reproduce this report</h2>')
    body.append(
        f'<pre><code>python main.py analyze {_escape(snapshot.repo_path)}</code></pre>'
        '<hr><p><small>Generated locally by RepoScope.</small></p>'
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
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>RepoScope - {snapshot.repo_name}</title>"
        f"<style>{css}</style></head><body>{''.join(body)}</body></html>"
    )


def _table_section(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]],
                   empty: str = "（none") -> str:
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
    """analysis CSV，Notes Excel / Notes"""

    def author_rows():
        out = []
        for author in view.author_stats:
            recent = "—" if author.recent_90d_share < 0 else f"{author.recent_90d_share:.0%}"
            out.append(
                (
                    "authors",
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
            binary_suffix = " · binary" if row.is_binary else ""
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
    out_rows += file_rows("files", view.hotspot_files)
    out_rows += file_rows("files", view.large_files)
    out_rows += file_rows("files", view.stale_files)
    for index, warning in enumerate(view.warnings, start=1):
        out_rows.append(
            ("anti-patterns", f"{index}. {warning.rule}", "—", "—", "—", "—",
             "—", "—",
             f"{warning.severity} · {warning.message or '—'} |  items{warning.condition or '—'} | "
             f"value{warning.actual or '—'} | value{warning.threshold or '—'} | "
             f"Action: {warning.action or '—'}"),
        )
    out_rows.append(
        ("Summary", "health", f"{view.health_score:.0f}", "—", "—", "—", "—", "—",
         f"Risk: {_risk_cn(view.risk_level or 'low')} · commits {view.total_commits} · authors {view.author_count}")
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


# --- Notes -----------------------------------------------------------------


def write_report(view: AnalysisView, formats: Sequence[str], output_dir: str | Path,
                 *, stem: str | None = None) -> list[Path]:
    """files"""
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
            raise ValueError(f"Unsupported report format: {fmt} (use markdown, html, or csv)")
        ext = {"markdown": ".md", "md": ".md", "html": ".html", "csv": ".csv"}[key]
        content = renderer[key](view)
        path = folder / f"{stem}{ext}"
        path.write_text(content, encoding="utf-8-sig" if key == "csv" else "utf-8",
                        newline="")
        written.append(path)
    return written


# --- Notes -------------------------------------------------------------


def render_summary_markdown(summaries: Sequence, failures: Sequence = (),
                            generated_at: datetime | None = None) -> str:
    """repository"""
    lines: list[str] = [
        "# RepoScope analysis",
        "",
        f"- time{(generated_at or datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Repositories: {len(summaries) + len(failures)}; successful: {len(summaries)}; failed: {len(failures)}",
        "",
        "| repository | path | commits | authors | health | files | files | risk |",
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
        lines.append("| Repository | Error |")
        lines.append("| --- | --- |")
        for failure in failures:
            name = getattr(failure, "repo_name", failure.path)
            lines.append(f"| {_md_cell(name)} | {_md_cell(failure.error)} |")
        lines.append("")
    lines += [
        "---",
        "",
        "*This summary was generated locally by RepoScope.*",
        "",
    ]
    return "\n".join(lines)


def render_summary_csv(rows: Sequence) -> str:
    """repository CSV；Notes repo_name / path / commits / authors /
    health_score / hotspot_count / stale_count / risk_level。"""
    lines = [
        ",".join(_csv_field(c) for c in (
            "repository", "path", "commits", "authors", "health", "files", "files", "risk",
        ))
    ]
    for row in rows:
        lines.append(",".join(_csv_field(str(getattr(row, name))) for name in (
            "repo_name", "path", "commits", "authors", "health_score",
            "hotspot_count", "stale_count", "risk_level",
        )))
    return "\n".join(lines) + "\n"



