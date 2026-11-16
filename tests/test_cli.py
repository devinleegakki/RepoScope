"""集成测试：命令行（main.py）。

对应验收要求：
* analyze / check / batch 三个命令可运行；
* 支持仓库路径、配置文件、时间范围、输出格式、输出目录参数；
* 错误输入给可读提示、退出码非零、不打堆栈；
* 批量分析单个仓库失败不影响其他仓库。
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

from .test_services import make_repo  # noqa: E402


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "main.py"), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path)


def test_version_flag() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert "RepoScope" in (result.stdout + result.stderr)


def test_missing_subcommand_exits_with_usage_error() -> None:
    result = run_cli()
    assert result.returncode != 0
    assert "usage" in (result.stdout + result.stderr).lower()


def test_check_valid_repository(repo: Path) -> None:
    result = run_cli("check", str(repo))
    assert result.returncode == 0
    assert "有效" in result.stdout
    assert repo.name in result.stdout


def test_check_invalid_repository_is_readable(repo: Path, tmp_path: Path) -> None:
    result = run_cli("check", str(tmp_path / "missing"))
    assert result.returncode == 1
    assert "校验失败" in result.stderr
    assert "Traceback" not in result.stderr + result.stdout


def test_check_json_output(repo: Path) -> None:
    result = run_cli("check", str(repo), "--json")
    assert result.returncode == 0
    assert '"ok": true' in result.stdout
    assert '"commits": 3' in result.stdout


def test_analyze_exports_three_formats(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "reports"
    result = run_cli("analyze", str(repo), "--format", "all", "--output", str(out))
    assert result.returncode == 0, result.stderr
    stem = repo.name
    for suffix in (".md", ".html", ".csv"):
        path = out / f"{stem}_report{suffix}"
        assert path.exists(), f"缺少报告文件：{path}"
        assert path.stat().st_size > 0


def test_export_defaults_to_all_formats(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "reports"
    result = run_cli("export", str(repo), "--output", str(out))
    assert result.returncode == 0, result.stderr
    stem = repo.name
    for suffix in (".md", ".html", ".csv"):
        path = out / f"{stem}_report{suffix}"
        assert path.exists(), f"缺少报告文件：{path}"
        assert path.stat().st_size > 0


def test_analyze_window_days_respects_time_range(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "reports"
    result = run_cli(
        "analyze", str(repo), "--window-days", "30",
        "--format", "markdown", "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    assert "提交 2" in result.stdout          # 400 天前那条提交被时间范围过滤


def test_analyze_config_file_and_override(repo: Path, tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"stale_days": 30, "window_days": 90}', encoding="utf-8")
    out = tmp_path / "reports"
    result = run_cli(
        "analyze", str(repo), "--config", str(config),
        "--window-days", "30",           # 命令行覆盖配置文件
        "--format", "markdown", "--output", str(out),
    )
    assert result.returncode == 0, result.stderr
    assert "提交 2" in result.stdout


def test_analyze_invalid_path_is_readable(tmp_path: Path) -> None:
    result = run_cli("analyze", str(tmp_path / "missing"), "--output", str(tmp_path / "out"))
    assert result.returncode == 1
    assert "分析失败" in result.stderr
    assert "Traceback" not in result.stderr + result.stdout
    assert not (tmp_path / "out").exists()


def test_analyze_invalid_config_is_readable(repo: Path, tmp_path: Path) -> None:
    config = tmp_path / "bad.json"
    config.write_text('{"stale_days": 0}', encoding="utf-8")
    result = run_cli("analyze", str(repo), "--config", str(config))
    assert result.returncode == 1
    assert "配置有误" in result.stderr


def test_batch_isolates_failures_and_writes_summary(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "reports"
    result = run_cli(
        "batch", str(repo), str(tmp_path / "missing"),
        "--format", "markdown", "--output", str(out), "--max-workers", "2",
    )
    assert result.returncode == 1          # 有失败仓库 → 非零退出
    assert (out / f"{repo.name}_report.md").exists()
    assert (out / "batch_summary.md").exists()
    assert (out / "batch_summary.csv").exists()
    assert "失败" in result.stderr


def test_batch_all_success(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "reports"
    result = run_cli(
        "batch", str(repo), str(repo),
        "--format", "markdown", "--output", str(out), "--max-workers", "2",
    )
    assert result.returncode == 0, result.stderr
    summary = (out / "batch_summary.md").read_text(encoding="utf-8")
    assert "成功：2" in summary
