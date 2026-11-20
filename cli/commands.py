"""``main.py`` 背后的命令行实现：analyze / check / batch 三个子命令。

设计要点（对应组长文档"CLI"与"批量分析"两栏）：

* **同一分析服务**：三个子命令全部走 ``services.AnalysisService``，
  GUI 也走同一个入口，保证 CLI 与 GUI 的结果一致。
* **同一份报告**：导出调用 ``reporters.write_report``，与 GUI 报告区同源。
* **失败隔离**：``batch`` 用 ``BatchAnalyzer``（ThreadPoolExecutor），
  单个仓库失败只影响它自己那一行。
* **可读错误**：所有预期错误都变成一行中文提示 + 非零退出码，不打堆栈。
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


# --- 参数解析 ---------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="RepoScope — 本地 Git 仓库健康分析（CLI）",
        epilog="GUI 版本：python main.py（或 python main.py --demo）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="RepoScope 1.0",
        help="显示版本号后退出",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="{analyze,check,export,batch}")
    subparsers.required = True

    # analyze -------------------------------------------------------------
    analyze = subparsers.add_parser(
        "analyze",
        help="分析一个本地 Git 仓库并导出报告",
        description="分析单个仓库，打印健康摘要并生成 Markdown / HTML / CSV 报告。",
    )
    analyze.add_argument("repo", metavar="仓库目录", help="本地 Git 仓库根目录")
    analyze.add_argument(
        "-c", "--config", metavar="配置文件.json",
        help="JSON 配置文件（阈值、时间范围、提交格式）",
    )
    analyze.add_argument(
        "-f", "--format", default="markdown", choices=_FORMAT_CHOICES,
        help="报告格式（默认 markdown；all = 三种都导出）",
    )
    analyze.add_argument(
        "-o", "--output", default="reports", metavar="输出目录",
        help="报告输出目录（默认 ./reports）",
    )
    _add_config_overrides(analyze)
    analyze.set_defaults(handler=_handle_analyze)

    # export --------------------------------------------------------------
    export = subparsers.add_parser(
        "export",
        help="分析仓库并导出报告（默认三种格式全导出）",
        description="与 analyze 同一套分析，默认把 Markdown / HTML / CSV 一次全导出。",
    )
    export.add_argument("repo", metavar="仓库目录", help="本地 Git 仓库根目录")
    export.add_argument(
        "-c", "--config", metavar="配置文件.json",
        help="JSON 配置文件（阈值、时间范围、提交格式）",
    )
    export.add_argument(
        "-f", "--format", default="all", choices=_FORMAT_CHOICES,
        help="报告格式（默认 all = 三种都导出）",
    )
    export.add_argument(
        "-o", "--output", default="reports", metavar="输出目录",
        help="报告输出目录（默认 ./reports）",
    )
    _add_config_overrides(export)
    export.set_defaults(handler=_handle_analyze)

    # check ---------------------------------------------------------------
    check = subparsers.add_parser(
        "check",
        help="校验仓库是否可分析（不写任何文件）",
        description="确认路径是 Git 仓库根目录、Git 可用、仓库能读出提交历史。",
    )
    check.add_argument("repo", metavar="仓库目录", help="本地 Git 仓库根目录")
    check.add_argument(
        "--json", action="store_true", help="以 JSON 输出校验结果（便于脚本调用）",
    )
    check.set_defaults(handler=_handle_check)

    # batch ---------------------------------------------------------------
    batch = subparsers.add_parser(
        "batch",
        help="并发分析多个仓库并生成对比汇总",
        description="用线程池并发分析多个仓库；单个仓库失败不影响其它任务。",
    )
    batch.add_argument("repos", nargs="+", metavar="仓库目录", help="一个或多个本地 Git 仓库根目录")
    batch.add_argument(
        "-c", "--config", metavar="配置文件.json",
        help="JSON 配置文件（阈值、时间范围、提交格式）",
    )
    batch.add_argument(
        "-f", "--format", default="markdown", choices=_FORMAT_CHOICES,
        help="每个仓库的报告格式（默认 markdown；all = 三种都导出）",
    )
    batch.add_argument(
        "-o", "--output", default="reports", metavar="输出目录",
        help="报告输出目录（默认 ./reports）",
    )
    batch.add_argument(
        "-j", "--max-workers", type=int, default=4, metavar="N",
        help="并发线程数（默认 4）",
    )
    _add_config_overrides(batch)
    batch.set_defaults(handler=_handle_batch)

    return parser


def _add_config_overrides(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("配置覆盖（优先级高于 --config 文件）")
    group.add_argument("--stale-days", type=int, default=None, metavar="N",
                       help="陈旧文件阈值（天）")
    group.add_argument("--large-file-mb", type=int, default=None, metavar="N",
                       help="大文件阈值（MB）")
    group.add_argument("--hotspot-changes", type=int, default=None, metavar="N",
                       help="热点文件修改次数阈值")
    group.add_argument("--release-stale-days", type=int, default=None, metavar="N",
                       help="发布停滞阈值（天）")
    group.add_argument("--single-maintainer-ratio", type=float, default=None, metavar="R",
                       help="单一维护者占比阈值（0~1）")
    group.add_argument("--window-days", type=int, default=None, metavar="N",
                       help="只统计最近 N 天的提交（0 = 全部历史）")
    group.add_argument("--commit-pattern", default=None, metavar="正则",
                       help="提交信息规范的正则")


def _resolve_config(args: argparse.Namespace) -> AnalysisConfig:
    """配置文件打底，命令行参数覆盖，最后统一校验。"""
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


# --- 子命令 -----------------------------------------------------------------


def _handle_analyze(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
    except (ValueError, OSError) as exc:
        return _fail(f"配置有误：{exc}")

    service = AnalysisService(allow_synthetic=False)
    progress = _progress_printer()
    try:
        view = service.analyze(args.repo, config, on_progress=progress)
    except AnalysisError as exc:
        return _fail(f"分析失败（{exc.code}）：{exc.message}")

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
            print(f"校验失败：{exc.message}", file=sys.stderr)
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

    print(f"OK：{info.repo_name} 是有效的 Git 仓库")
    print(f"  路径：{info.path}")
    print(f"  提交：{info.commits} · 文件：{info.files}")
    print(f"  分支：{', '.join(info.branches) or '—'}")
    print(f"  标签：{', '.join(info.tags) or '—'}")
    print("可以运行：python main.py analyze " + info.path)
    return EXIT_OK


def _handle_batch(args: argparse.Namespace) -> int:
    try:
        config = _resolve_config(args)
    except (ValueError, OSError) as exc:
        return _fail(f"配置有误：{exc}")
    if args.max_workers < 1:
        return _fail("--max-workers 至少为 1")

    analyzer = BatchAnalyzer(max_workers=args.max_workers)
    cancel_event = threading.Event()

    def on_signal(signum, frame):  # noqa: ARG001 - 签名由 signal 规定
        if cancel_event.is_set():
            raise KeyboardInterrupt  # 第二次 Ctrl+C 直接退出
        print("\n收到中断信号，正在等待已开始的仓库收尾（再按一次强制退出）…", file=sys.stderr)
        cancel_event.set()

    previous = signal.signal(signal.SIGINT, on_signal)

    def on_progress(result: BatchResult, done: int, total: int) -> None:
        status = "成功" if result.ok else ("已取消" if result.cancelled else "失败")
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
        print(f"\n{len(failures)} 个仓库失败或已取消，详见汇总表。", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_OK


# --- 输出辅助 ---------------------------------------------------------------


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
    print(f"分析完成：{snapshot.repo_name}")
    print(f"  仓库：{snapshot.repo_path}")
    print(
        f"  提交 {view.total_commits} · 作者 {view.author_count} · 文件 {view.file_count} · "
        f"健康度 {view.health_score:.0f} · 反模式 {len(view.warnings)} 条 · "
        f"用时 {view.elapsed_seconds:.1f}s"
    )


def _print_batch_table(results: Sequence[BatchResult]) -> None:
    print("\n批量分析结果：")
    for result in results:
        if result.ok and result.view is not None:
            view = result.view
            print(
                f"  {view.snapshot.repo_name:<24} 提交 {view.total_commits:<5} "
                f"健康度 {view.health_score:>5.0f}  反模式 {len(view.warnings)} 条"
            )
        else:
            name = result.repo_name or Path(result.path).name
            print(f"  {name:<24} 失败：{result.error}")


def _print_written(paths: Sequence[Path]) -> None:
    if not paths:
        return
    print("\n报告已生成：")
    for path in paths:
        print(f"  {path}")


# --- 入口 -------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    _ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        return EXIT_INTERRUPTED
    except AnalysisError as exc:
        return _fail(f"错误（{exc.code}）：{exc.message}")
    except ValueError as exc:
        return _fail(f"错误：{exc}")


def _ensure_utf8_stdio() -> None:
    """Windows 控制台默认 cp936，打印中文报告路径可能乱码；尽力切到 UTF-8。"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - 某些被重定向的流不支持
            pass

