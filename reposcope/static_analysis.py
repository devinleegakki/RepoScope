"""Local, non-executing code quality, ownership, dependency and secret scans."""
from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from .models_analysis import (AnalysisConfig, CodeQualityMetrics, DependencyMetrics,
                                  FileOwnershipStat, OwnershipMetrics, SecurityFinding,
                                  RepositorySnapshotLike, _first_attr, as_utc_datetime)
except ImportError:
    from reposcope.models_analysis import (AnalysisConfig, CodeQualityMetrics, DependencyMetrics,
                                 FileOwnershipStat, OwnershipMetrics, SecurityFinding,
                                 RepositorySnapshotLike, _first_attr, as_utc_datetime)  # type: ignore

SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("api_key", re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]")),
    ("password", re.compile(r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
)
DANGEROUS_TEXT_PATTERNS = (
    ("os.system", re.compile(r"\bos\.system\s*\(")),
    ("subprocess.shell_true", re.compile(r"\bshell\s*=\s*True\b")),
)
MANIFESTS = {"requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "setup.py"}
LOCKFILES = {"poetry.lock", "Pipfile.lock", "requirements.lock", "uv.lock", "pdm.lock"}


def _repo_path(snapshot: Any) -> Path:
    return Path(str(_first_attr(snapshot, ("repo_path",), "")))


def _tracked_files(snapshot: Any) -> list[str]:
    return [str(_first_attr(f, ("path", "name"), "")) for f in (_first_attr(snapshot, ("files",), []) or [])]


def _cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    found: list[list[str]] = []
    def visit(node: str, stack: list[str], active: set[str]) -> None:
        if node in active:
            cycle = stack[stack.index(node):] + [node]
            key = tuple(sorted(cycle))
            if not any(tuple(sorted(x)) == key for x in found): found.append(cycle)
            return
        if node in stack or node not in graph: return
        for nxt in graph.get(node, []): visit(nxt, stack + [node], active | {node})
    for n in graph: visit(n, [], set())
    return found


def scan_code_quality(snapshot: RepositorySnapshotLike, config: AnalysisConfig) -> CodeQualityMetrics:
    root = _repo_path(snapshot); result = CodeQualityMetrics(); graph: dict[str, list[str]] = {}
    py_files = [p for p in _tracked_files(snapshot) if p.endswith(".py")]
    result.python_files = len(py_files); result.test_files = sum(1 for p in py_files if Path(p).name.startswith("test_") or "tests/" in p.replace("\\", "/"))
    for rel in py_files:
        path = root / rel
        try: text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError): continue
        lines = text.count("\n") + (1 if text else 0); result.lines += lines
        result.todo_count += len(re.findall(r"\b(?:TODO|FIXME)\b", text, re.I))
        if lines > result.max_file_lines: result.max_file_lines = lines
        if lines > config.max_file_lines: result.long_files.append({"path": rel, "lines": lines})
        try: tree = ast.parse(text, filename=rel)
        except SyntaxError: continue
        local_imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.functions += 1; length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno + 1
                result.max_function_lines = max(result.max_function_lines, length)
                if length > config.max_function_lines: result.long_functions.append({"path": rel, "name": node.name, "lines": length, "line": node.lineno})
            elif isinstance(node, ast.ClassDef): result.classes += 1
            elif isinstance(node, ast.ExceptHandler) and node.type is None: result.bare_except_count += 1
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else (f"{fn.value.id}.{fn.attr}" if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) else "")
                if name in {"eval", "exec", "os.system", "pickle.loads", "yaml.load"}:
                    result.dangerous_patterns.append({"path": rel, "kind": name, "line": getattr(node, "lineno", 0), "preview": name})
                if name.startswith("subprocess.") and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                    result.dangerous_patterns.append({"path": rel, "kind": "subprocess.shell_true", "line": getattr(node, "lineno", 0), "preview": "subprocess call with shell=True"})
            elif isinstance(node, ast.Import): local_imports.extend(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: local_imports.append(node.module.split(".")[0])
        for kind, pattern in DANGEROUS_TEXT_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                if not any(x["path"] == rel and x["line"] == line and x["kind"] == kind for x in result.dangerous_patterns):
                    result.dangerous_patterns.append({"path": rel, "kind": kind, "line": line, "preview": kind})
        module = rel[:-3].replace("\\", "/").replace("/", ".").replace(".", ".")
        graph[module] = local_imports
    result.test_ratio = result.test_files / result.python_files if result.python_files else 0.0
    result.imports = graph; result.cycles = _cycles(graph)
    return result


def scan_ownership(snapshot: RepositorySnapshotLike, config: AnalysisConfig) -> OwnershipMetrics:
    by_file: dict[str, Counter[str]] = defaultdict(Counter); last: dict[str, tuple[Any, str]] = {}
    for commit in (_first_attr(snapshot, ("commits",), []) or []):
        author = str(_first_attr(commit, ("author_name", "author"), "") or "(unknown)")
        when = as_utc_datetime(_first_attr(commit, ("authored_at", "timestamp", "date"), None))
        for p in (_first_attr(commit, ("files_changed",), []) or []):
            rel = str(_first_attr(p, ("path", "name"), p) if not isinstance(p, str) else p)
            by_file[rel][author] += 1
            if when and (rel not in last or when > last[rel][0]): last[rel] = (when, author)
    result = OwnershipMetrics()
    for path, authors in by_file.items():
        total = sum(authors.values()); top, count = authors.most_common(1)[0]
        row = FileOwnershipStat(path, total, len(authors), top, count / total if total else 0.0, last.get(path, (None, ""))[1])
        result.files.append(row)
        if row.top_author_ratio >= config.ownership_ratio and row.author_count > 0: result.high_risk_files.append(row)
    result.files.sort(key=lambda x: (-x.changes, x.path)); result.high_risk_files.sort(key=lambda x: (-x.top_author_ratio, -x.changes))
    return result


def scan_dependencies(snapshot: RepositorySnapshotLike) -> DependencyMetrics:
    root = _repo_path(snapshot); result = DependencyMetrics(); names: list[str] = []
    for rel in _tracked_files(snapshot):
        name = Path(rel).name
        if name in MANIFESTS:
            result.manifests.append(rel)
            try: text = (root / rel).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError): continue
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith(("#", "[", "-e ")): continue
                if name.endswith(".txt"):
                    dep = re.split(r"[<>=!~ ]", line, 1)[0]
                    if dep: names.append(dep); result.dependencies.append({"name": dep, "spec": line, "source": rel})
                    if not re.search(r"(==|~=|>=.*<|^\w+\s*$)", line): result.unpinned.append(line)
                elif name == "pyproject.toml" and re.match(r"[A-Za-z0-9_.-]+\s*=", line):
                    dep = line.split("=", 1)[0].strip(); names.append(dep); result.dependencies.append({"name": dep, "spec": line, "source": rel})
        if name in LOCKFILES: result.lockfiles.append(rel)
    result.duplicates = sorted({x for x, n in Counter(names).items() if n > 1}); return result


def scan_secrets(snapshot: RepositorySnapshotLike, config: AnalysisConfig) -> list[SecurityFinding]:
    if not config.enable_secret_scan: return []
    root = _repo_path(snapshot); findings: list[SecurityFinding] = []
    for rel in _tracked_files(snapshot):
        try: lines = (root / rel).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError: continue
        for no, line in enumerate(lines, 1):
            for kind, pattern in SECRET_PATTERNS:
                if pattern.search(line): findings.append(SecurityFinding(rel, kind, no, "<redacted>", "high")); break
    return findings


def run_static_analysis(snapshot: RepositorySnapshotLike, config: AnalysisConfig):
    quality = scan_code_quality(snapshot, config); ownership = scan_ownership(snapshot, config)
    dependencies = scan_dependencies(snapshot) if config.enable_dependency_scan else DependencyMetrics()
    return quality, ownership, dependencies, scan_secrets(snapshot, config)




