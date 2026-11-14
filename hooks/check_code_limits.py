#!/usr/bin/env python3
"""Enforce readable Clojure and Python code limits for Antigravity hooks.

Enforces:
- Max 20 lines of code per function (defn, defn-, fn, defmacro, defmethod, def).
- Max 500 lines per namespace or module file.
- Anti-golfing: rejects semicolons, packed statements, dense one-liners.
- Soft limit: warnings for lines exceeding 80 characters.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
from pathlib import Path
import sys
import tokenize
from typing import Any, Dict, List, Optional, Sequence

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from clojure_ast import (  # noqa: E402, F401
    analyze_clojure_ast,
    format_clojure_file,
    format_clojure_stdin,
    parse_clojure_forms,
    run_clj_kondo,
)
from git_scope import (  # noqa: E402, F401
    VALID_EXTS,
    detect_git_commit,
    get_modified_git_files,
    get_staged_blobs,
)

_COMPOUND_NODES = (
    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
    ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try,
)
_DENSE_EXPR = (
    ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp
)


def check_file_line_count(
    lines: Sequence[str], max_lines: int = 500
) -> Optional[str]:
    """Check that file does not exceed maximum line count."""
    count = len(lines)
    if count > max_lines:
        return f"File exceeds {max_lines} lines (found {count})"
    return None


def check_soft_line_lengths(
    lines: Sequence[str], max_len: int = 80
) -> List[str]:
    """Collect warnings for lines exceeding soft character limit."""
    warnings: List[str] = []
    for idx, line in enumerate(lines, start=1):
        clean_len = len(line.rstrip("\r\n"))
        if clean_len > max_len:
            warnings.append(
                f"Line {idx} exceeds {max_len} chars ({clean_len})"
            )
    return warnings


def detect_python_golfing(source_code: str) -> List[str]:
    """Detect semicolon statement chaining in Python code."""
    violations: List[str] = []
    stream = io.BytesIO(source_code.encode("utf-8")).readline
    try:
        for tok in tokenize.tokenize(stream):
            if tok.exact_type == tokenize.SEMI:
                violations.append(
                    f"Line {tok.start[0]}: semicolon chaining forbidden"
                )
    except tokenize.TokenError:
        pass
    return violations


def detect_python_ast_golfing(tree: ast.AST) -> List[str]:
    """Detect packed compound one-liners and dense nested expressions."""
    errs: List[str] = []
    dense_by_line: Dict[int, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, _COMPOUND_NODES) and node.body:
            if node.body[0].lineno == node.lineno:
                errs.append(f"Line {node.lineno}: packed one-liner forbidden")
        if isinstance(node, _DENSE_EXPR):
            dense_by_line[node.lineno] = dense_by_line.get(node.lineno, 0) + 1
    for line, count in sorted(dense_by_line.items()):
        if count > 2:
            errs.append(f"Line {line}: dense nested expressions ({count})")
    return errs


def check_python_fn_lengths(
    tree: ast.AST, max_lines: int = 20
) -> List[str]:
    """Verify each Python function definition is at most max_lines long."""
    violations: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            length = end - node.lineno + 1
            if length > max_lines:
                violations.append(
                    f"Function '{node.name}' at line {node.lineno} "
                    f"is {length} lines (max {max_lines})"
                )
    return violations


def check_python_code(source: str, label: str = "<source>") -> Dict[str, Any]:
    """Analyze Python code for hard and soft limits."""
    lines = source.splitlines(keepends=True)
    errors: List[str] = []
    err = check_file_line_count(lines)
    if err:
        errors.append(err)
    errors.extend(detect_python_golfing(source))
    try:
        tree = ast.parse(source, filename=label)
        errors.extend(detect_python_ast_golfing(tree))
        errors.extend(check_python_fn_lengths(tree))
    except SyntaxError as exc:
        errors.append(f"Syntax error at line {exc.lineno}: {exc.msg}")
    return {
        "file": label, "valid": not errors,
        "errors": errors, "warnings": check_soft_line_lengths(lines),
    }


def check_clojure_code(
    source: str, label: str = "<source>", use_kondo: bool = True
) -> Dict[str, Any]:
    """Analyze Clojure code in memory without mutating disk."""
    lines = source.splitlines(keepends=True)
    errors: List[str] = []
    err = check_file_line_count(lines)
    if err:
        errors.append(err)
    errors.extend(analyze_clojure_ast(source, Path(label), use_kondo))
    return {
        "file": label, "valid": not errors,
        "errors": errors, "warnings": check_soft_line_lengths(lines),
    }


def check_source_for_path(source: str, path: Path) -> Dict[str, Any]:
    """Dispatch pure in-memory code check based on file extension."""
    ext = path.suffix.lower()
    if ext in (".clj", ".cljs", ".cljc"):
        return check_clojure_code(source, str(path))
    if ext == ".py":
        return check_python_code(source, str(path))
    return {"file": str(path), "valid": True, "errors": [], "warnings": []}


def check_single_file(path: Path) -> Dict[str, Any]:
    """Read and check a file on disk with zero side effects."""
    if not path.is_file() or path.suffix.lower() not in VALID_EXTS:
        return {"file": str(path), "valid": True, "errors": [], "warnings": []}
    content = path.read_text(encoding="utf-8", errors="replace")
    return check_source_for_path(content, path)


def find_target_files(root: Path) -> List[Path]:
    """Find all Python and Clojure files in directory tree."""
    targets: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d != "__pycache__"
        ]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in VALID_EXTS:
                targets.append(p)
    return sorted(targets)


def check_workspace(root: Path) -> List[Dict[str, Any]]:
    """Scan and analyze all relevant source files in workspace."""
    results = [check_single_file(p) for p in find_target_files(root)]
    return [r for r in results if not r["valid"] or r["warnings"]]


def format_violation_reasons(violations: Sequence[Dict[str, Any]]) -> str:
    """Format violations into a readable diagnostic string."""
    reasons = [f"{v['file']}: {'; '.join(v['errors'])}" for v in violations]
    return f"Code limits violated: {' | '.join(reasons)}"


def _check_commit_targets(commit_cwd: Path) -> List[Dict[str, Any]]:
    """Check staged index blobs if git repo, else workspace."""
    blobs = get_staged_blobs(commit_cwd)
    targets = (
        [check_source_for_path(src, p) for p, src in blobs.items()]
        if blobs is not None
        else check_workspace(commit_cwd)
    )
    return [r for r in targets if not r["valid"]]


def handle_pre_tool_use(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Gate git commit on staged index blobs; return 'ask' otherwise."""
    tool_call = payload.get("toolCall", {})
    if tool_call.get("name") != "run_command":
        return {"decision": "ask"}
    cmd = tool_call.get("args", {}).get("CommandLine", "")
    workspace = Path(payload.get("cwd", ".")).resolve()
    commit_cwd = detect_git_commit(cmd, workspace)
    if commit_cwd is None:
        return {"decision": "ask"}
    violations = _check_commit_targets(commit_cwd)
    if violations:
        return {
            "decision": "deny",
            "reason": format_violation_reasons(violations),
        }
    return {"decision": "ask"}


def _emit_post_diagnostics(res: Dict[str, Any]) -> None:
    """Write PostToolUse check errors/warnings to stderr."""
    for err in res.get("errors", []):
        print(f"[code-limits] ERROR {res['file']}: {err}", file=sys.stderr)
    for warn in res.get("warnings", []):
        print(f"[code-limits] WARN  {res['file']}: {warn}", file=sys.stderr)


def handle_post_tool_use(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Format Clojure on disk and emit diagnostics to stderr; return {}."""
    args = payload.get("toolCall", {}).get("args", {})
    raw_path = args.get("Path")
    if not raw_path:
        return {}
    cwd = Path(payload.get("cwd", ".")).resolve()
    p = Path(raw_path)
    target = p if p.is_absolute() else (cwd / p).resolve()
    if target.suffix.lower() in (".clj", ".cljs", ".cljc"):
        format_clojure_file(target)
    _emit_post_diagnostics(check_single_file(target))
    return {}


def handle_stop(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Check modified files before agent stop with controlled blast radius."""
    if payload.get("continuationActive"):
        return {"decision": "allow"}
    workspace = Path(payload.get("cwd", ".")).resolve()
    modified = get_modified_git_files(workspace)
    targets = (
        [check_single_file(p) for p in modified]
        if modified is not None
        else check_workspace(workspace)
    )
    violations = [r for r in targets if not r["valid"]]
    if violations:
        return {
            "decision": "continue",
            "reason": "Outstanding code limit violations must be resolved.",
        }
    return {"decision": "allow"}


def process_hook_payload(event: str, payload_str: str) -> str:
    """Parse JSON payload, dispatch event, and return JSON response."""
    try:
        data = json.loads(payload_str) if payload_str.strip() else {}
    except json.JSONDecodeError:
        data = {}
    dispatch = {
        "PreToolUse": handle_pre_tool_use,
        "PostToolUse": handle_post_tool_use,
        "Stop": handle_stop,
    }
    fn = dispatch.get(event)
    return json.dumps(fn(data) if fn else {"decision": "ask"})


def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments for checking and hooks."""
    parser = argparse.ArgumentParser(description="Code limits enforcer")
    parser.add_argument(
        "--event", choices=["PreToolUse", "PostToolUse", "Stop"]
    )
    parser.add_argument("--check", type=str, help="Path to check")
    return parser.parse_args()


def run_cli_check(target: Path) -> int:
    """Run non-mutating check on target path."""
    results = (
        check_workspace(target)
        if target.is_dir()
        else [check_single_file(target)]
    )
    has_errors = any(not r["valid"] for r in results)
    for r in results:
        status = "FAIL" if not r["valid"] else "PASS"
        print(f"[{status}] {r['file']}")
        for err in r["errors"]:
            print(f"  ERROR: {err}")
        for warn in r["warnings"]:
            print(f"  WARN:  {warn}")
    return 1 if has_errors else 0


def main() -> None:
    """CLI entrypoint for Antigravity hooks and direct checking."""
    args = parse_cli_args()
    if args.event:
        print(process_hook_payload(args.event, sys.stdin.read()))
        return
    target = Path(args.check or ".").resolve()
    sys.exit(run_cli_check(target))


if __name__ == "__main__":
    main()
