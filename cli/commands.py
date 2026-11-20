"""``main.py`` Notesanalyze / check / batch Notes

Notes"CLI"Notes"analysis"Notes

* **analysis**：Notes ``services.AnalysisService``，
  GUI Notes CLI Notes GUI Notes
* **report**：export ``reporters.write_report``，Notes GUI report
* **error**：``batch`` Notes ``BatchAnalyzer``（ThreadPoolExecutor），
  repository
* **error**：error + Notes
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from pathlib import Path
from typing import Sequence

from core import reporters
from core.services import (
    AnalysisConfig,
    AnalysisError,
    AnalysisService,
    BatchAnalyzer,
    BatchResult,
    summarize_view,
)

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPTED = 130

_FORMAT_CHOICES = ("markdown", "md", "html", "csv", "all")


# --- settings ---------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="RepoScope — analyze Git repositories from the command line",
        epilog="Launch the GUI with: python main.py --demo",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RepoScope 1.0",
        help="Show the version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="{analyze,check,export,batch}")
    subparsers.required = True

    # analyze -------------------------------------------------------------
    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a Git repository",
        description="Analyze a repository and write a Markdown, HTML, or CSV report",
    )
    analyze.add_argument("repo", metavar="REPOSITORY", help="Path to a Git repository")
    analyze.add_argument(
        "-c", "--config", metavar="files.json",
        help="Load analysis settings from a JSON file",
    )
    analyze.add_argument(
        "-f", "--format", default="markdown", choices=_FORMAT_CHOICES,
        help="Report format (markdown, md, html, csv, or all)",
    )
    analyze.add_argument(
        "-o", "--output", default="reports", metavar="DIR",
        help="Output directory (default: reports)",
    )
    _add_config_overrides(analyze)
    analyze.set_defaults(handler=_handle_analyze)

    # export --------------------------------------------------------------
    export = subparsers.add_parser(
        "export",
        help="Export reports for a repository",
        description="Analyze a repository and export all requested report formats",
    )
    export.add_argument("repo", metavar="REPOSITORY", help="Path to a Git repository")
    export.add_argument(
        "-c", "--config", metavar="files.json",
        help="Load analysis settings from a JSON file",
    )
    export.add_argument(
        "-f", "--format", default="all", choices=_FORMAT_CHOICES,
        help="Report format (default: all)",
    )
    export.add_argument(
        "-o", "--output", default="reports", metavar="DIR",
        help="Output directory (default: reports)",
    )
    _add_config_overrides(export)
    export.set_defaults(handler=_handle_analyze)

    # check ---------------------------------------------------------------
    check = subparsers.add_parser(
        "check",
        help="Check a repository",
        description="Validate a Git repository and print its basic metadata",
    )
    check.add_argument("repo", metavar="REPOSITORY", help="Path to a Git repository")
    check.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON",
    )
    check.set_defaults(handler=_handle_check)

    # batch ---------------------------------------------------------------
    batch = subparsers.add_parser(
        "batch",
        help="Analyze several repositories",
        description="Analyze multiple repositories and write a combined summary",
    )
    batch.add_argument("repos", nargs="+", metavar="REPOSITORY", help="Paths to Git repositories")
    batch.add_argument(
        "-c", "--config", metavar="files.json",
        help="Load analysis settings from a JSON file",
    )
    batch.add_argument(
        "-f", "--format", default="markdown", choices=_FORMAT_CHOICES,
        help="Report format (markdown, md, html, csv, or all)",
    )
    batch.add_argument(
        "-o", "--output", default="reports", metavar="DIR",
        help="Output directory (default: reports)",
    )
    batch.add_argument(
        "-j", "--max-workers", type=int, default=4, metavar="N",
        help="Maximum parallel workers (default: 4)",
    )
    _add_config_overrides(batch)
    batch.set_defaults(handler=_handle_batch)

    return parser


def _add_config_overrides(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("Configuration overrides")
    group.add_argument("--stale-days", type=int, default=None, metavar="N",
                       help="Days after which a file is considered stale")
    group.add_argument("--large-file-mb", type=int, default=None, metavar="N",
                       help="Large-file threshold in megabytes")
    group.add_argument("--hotspot-changes", type=int, default=None, metavar="N",
                       help="Minimum changes for a hotspot file")
    group.add_argument("--release-stale-days", type=int, default=None, metavar="N",
                       help="Days after which a release is considered stale")
    group.add_argument("--single-maintainer-ratio", type=float, default=None, metavar="R",
                       help="Maximum share allowed for one maintainer (0–1)")
    group.add_argument("--window-days", type=int, default=None, metavar="N",
                       help="Limit recent activity to N days; 0 disables the limit")
    group.add_argument("--commit-pattern", default=None, metavar="REGEX",
                       help="Regular expression for commit messages")


def _resolve_config(args: argparse.Namespace) -> AnalysisConfig:
    """files"""
    config = AnalysisConfig.from_json(args.config) if args.config else AnalysisConfig()
    overrides = {
        field: getattr(args, field)
        for field in (
            "stale_days", "large_file_mb", "hotspot_changes", "release_stale_days",
            "single_maintainer_ratio", "window_days", "commit_pattern",
        )
        if getattr(args, field) is not None
    }
    if not overrides:
        config.validate()
        return config
    data = config.to_dict()
    data.update(overrides)
    return AnalysisConfig.from_dict(data)


def _resolve_formats(value: str) -> list[str]:
    if value == "all":
        return ["markdown", "html", "csv"]
    return [value]


# --- Notes -----------------------------------------------------------------


def _handle_analyze(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
    except (ValueError, OSError) as exc:
        return _fail(f"Configuration error: {exc}")

    service = AnalysisService(allow_synthetic=False)
    progress = _progress_printer()
    try:
        view = service.analyze(args.repo, config, on_progress=progress)
    except AnalysisError as exc:
        return _fail(f"Analysis failed ({exc.code}): {exc.message}")

    _print_view_summary(view)

    written = reporters.write_report(
        view, _resolve_formats(args.format), args.output,
        stem=f"{view.snapshot.repo_name}_report",
    )
    _print_written(written)
    return EXIT_OK


def _handle_check(args: argparse.Namespace) -> int:
    service = AnalysisService(allow_synthetic=False)
    try:
        info = service.check(args.repo)
    except AnalysisError as exc:
        if args.json:
            print(json.dumps({"ok": False, "code": exc.code, "message": exc.message},
                             ensure_ascii=False))
        else:
            print(f"Check failed: {exc.message}", file=sys.stderr)
        return EXIT_FAILURE

    if args.json:
        print(json.dumps(
            {
                "ok": True,
                "path": info.path,
                "repo_name": info.repo_name,
                "commits": info.commits,
                "files": info.files,
                "branches": list(info.branches),
                "tags": list(info.tags),
            },
            ensure_ascii=False,
        ))
        return EXIT_OK

    print(f"OK: {info.repo_name} is a Git repository")
    print(f"  Path: {info.path}")
    print(f"  Commits: {info.commits} · Files: {info.files}")
    print(f"  Branches: {', '.join(info.branches) or '—'}")
    print(f"  Tags: {', '.join(info.tags) or '—'}")
    print("  Analyze with: python main.py analyze " + info.path)
    return EXIT_OK


def _handle_batch(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
    except (ValueError, OSError) as exc:
        return _fail(f"configuration{exc}")
    if args.max_workers < 1:
        return _fail("--max-workers must be at least 1")

    analyzer = BatchAnalyzer(max_workers=args.max_workers)
    cancel_event = threading.Event()

    def on_signal(signum, frame):  # noqa: ARG001 - Notes signal Notes
        if cancel_event.is_set():
            raise KeyboardInterrupt  # Notes Ctrl+C Notes
        print("\nCancellation requested", file=sys.stderr)
        cancel_event.set()

    previous = signal.signal(signal.SIGINT, on_signal)

    def on_progress(result: BatchResult, done: int, total: int) -> None:
        status = "complete" if result.ok else ("cancel" if result.cancelled else "error")
        name = result.repo_name or Path(result.path).name
        print(f"[{done}/{total}] {name}：{status}", file=sys.stderr)

    try:
        results = analyzer.run(
            args.repos, config, on_progress=on_progress, cancel_event=cancel_event
        )
    finally:
        signal.signal(signal.SIGINT, previous)

    folders = Path(args.output)
    formats = _resolve_formats(args.format)
    summaries = []
    failures = []
    written: list[Path] = []

    for result in results:
        if result.ok and result.view is not None:
            summaries.append(summarize_view(result.view))
            written += reporters.write_report(
                result.view, formats, folders, stem=f"{result.view.snapshot.repo_name}_report"
            )
        else:
            failures.append(result)

    folders.mkdir(parents=True, exist_ok=True)
    summary_md = folders / "batch_summary.md"
    summary_md.write_text(
        reporters.render_summary_markdown(summaries, failures), encoding="utf-8"
    )
    summary_csv = folders / "batch_summary.csv"
    summary_csv.write_text(
        reporters.render_summary_csv(summaries), encoding="utf-8-sig"
    )
    written += [summary_md, summary_csv]

    _print_batch_table(results)
    _print_written(written)

    if failures:
        print(f"\n{len(failures)} repositories failed", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_OK


# --- Notes ---------------------------------------------------------------


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_FAILURE


def _progress_printer():
    state = {"last": -1}

    def report(percent: int, message: str) -> None:
        if percent == state["last"]:
            return
        state["last"] = percent
        print(f"  [{percent:3d}%] {message}", file=sys.stderr)

    return report


def _print_view_summary(view) -> None:
    snapshot = view.snapshot
    print(f"Analysis: {snapshot.repo_name}")
    print(f"  Repository: {snapshot.repo_path}")
    print(
        f"  Commits: {view.total_commits} · Authors: {view.author_count} · Files: {view.file_count} · "
        f"Health: {view.health_score:.0f} · Anti-patterns: {len(view.warnings)} · "
        f"Elapsed: {view.elapsed_seconds:.1f}s"
    )


def _print_batch_table(results: Sequence[BatchResult]) -> None:
    print("\nBatch analysis")
    for result in results:
        if result.ok and result.view is not None:
            view = result.view
            print(
                f"  {view.snapshot.repo_name:<24} commits {view.total_commits:<5} "
                f"health {view.health_score:>5.0f}  anti-patterns {len(view.warnings)}"
            )
        else:
            name = result.repo_name or Path(result.path).name
            print(f"  {name:<24} failed: {result.error}")


def _print_written(paths: Sequence[Path]) -> None:
    if not paths:
        return
    print("\nReports written:")
    for path in paths:
        print(f"  {path}")


# --- Notes -------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except AnalysisError as exc:
        return _fail(f"Error ({exc.code}): {exc.message}")
    except ValueError as exc:
        return _fail(f"Error: {exc}")


def _ensure_utf8_stdio() -> None:
    """Windows default cp936，report UTF-8。"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - Notes
            pass




