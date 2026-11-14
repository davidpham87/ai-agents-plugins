#!/usr/bin/env python3
"""Enforce readable Clojure and Python code limits for Antigravity hooks.

Enforces:
- Max 20 lines of code per function (defn, defn-, fn, def, async def).
- Max 500 lines per namespace or module file.
- Anti-golfing: rejects semicolon-chained statements and packed forms.
- Soft limit: warnings for lines exceeding 80 characters.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tokenize
from typing import Any, Dict, List, Optional, Sequence, Tuple


def run_cljfmt_fix(file_path: Path) -> bool:
    """Format Clojure file using cljfmt or clojure-lsp fallback."""
    if not file_path.exists():
        return False
    cmd = shutil.which("cljfmt")
    if cmd:
        try:
            res = subprocess.run([cmd, "fix", str(file_path)], timeout=10)
            return res.returncode == 0
        except (subprocess.SubprocessError, OSError):
            pass
    lsp = shutil.which("clojure-lsp")
    if lsp:
        try:
            cmd_args = [lsp, "format", "--filenames", str(file_path)]
            return subprocess.run(cmd_args, timeout=10).returncode == 0
        except (subprocess.SubprocessError, OSError):
            pass
    return False


def build_kondo_args(cmd: str, target: str) -> List[str]:
    """Construct command line arguments for clj-kondo JSON analysis."""
    return [
        cmd,
        "--lint",
        target,
        "--lang",
        "clj",
        "--config",
        "{:output {:format :json} :analysis true}",
    ]


def run_clj_kondo(
    path: Path, content: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Run clj-kondo to extract AST analysis and findings JSON."""
    cmd = shutil.which("clj-kondo")
    if not cmd:
        return None
    try:
        args = build_kondo_args(cmd, "-" if content is not None else str(path))
        res = subprocess.run(
            args,
            input=content,
            stdout=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return json.loads(res.stdout) if res.stdout.strip() else None
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None


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
                f"Line {idx} exceeds {max_len} characters ({clean_len})"
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
        errors.extend(check_python_fn_lengths(tree))
    except SyntaxError as exc:
        errors.append(f"Syntax error at line {exc.lineno}: {exc.msg}")
    return {
        "file": label,
        "valid": not errors,
        "errors": errors,
        "warnings": check_soft_line_lengths(lines),
    }


def update_clojure_char(
    char: str, depth: int, in_str: bool
) -> Tuple[int, bool, bool]:
    """Track depth and string boundary for a single Clojure character."""
    if char == '"':
        return depth, not in_str, False
    if in_str:
        return depth, True, False
    if char in "([":
        return depth + 1, False, depth == 0
    if char in ")]":
        new_depth = max(0, depth - 1)
        return new_depth, False, new_depth == 0
    return depth, False, False


def parse_clojure_forms(source_code: str) -> List[Dict[str, Any]]:
    """Extract top-level forms and line spans from Clojure source."""
    forms: List[Dict[str, Any]] = []
    depth, in_str, start_line, first_line = 0, False, 1, ""
    for line_idx, line in enumerate(source_code.splitlines(), start=1):
        if not line.strip() or line.strip().startswith(";"):
            continue
        for char in line:
            depth, in_str, is_edge = update_clojure_char(char, depth, in_str)
            if is_edge and depth == 1:
                start_line, first_line = line_idx, line.strip()[:40]
            elif is_edge and depth == 0:
                forms.append({
                    "start": start_line,
                    "end": line_idx,
                    "length": line_idx - start_line + 1,
                    "snippet": first_line,
                })
    return forms


def check_clojure_fn_lengths(
    forms: Sequence[Dict[str, Any]], max_lines: int = 20
) -> List[str]:
    """Check that Clojure function definitions do not exceed max_lines."""
    violations: List[str] = []
    fn_keywords = ("(defn ", "(defn- ", "(fn ", "(defmulti ")
    for form in forms:
        snippet = form.get("snippet", "")
        if any(kw in snippet for kw in fn_keywords):
            length = form["length"]
            if length > max_lines:
                violations.append(
                    f"Clojure function starting at line {form['start']} "
                    f"is {length} lines (max {max_lines})"
                )
    return violations


def detect_clojure_golfing(forms: Sequence[Dict[str, Any]]) -> List[str]:
    """Reject multiple top-level forms sharing the same line number."""
    violations: List[str] = []
    for i in range(1, len(forms)):
        prev, curr = forms[i - 1], forms[i]
        if curr["start"] <= prev["end"]:
            violations.append(
                f"Line {curr['start']}: anti-golfing violation "
                "(multiple top-level forms on line)"
            )
    return violations


def check_kondo_fn_lengths(
    analysis: Dict[str, Any], max_lines: int = 20
) -> List[str]:
    """Check function lengths from clj-kondo var-definitions analysis."""
    violations: List[str] = []
    for v in analysis.get("var-definitions", []):
        def_by = v.get("defined-by", "")
        if any(k in def_by for k in ("defn", "fn", "defmulti")):
            row, end_row = v.get("row", 1), v.get("end-row", 1)
            length = end_row - row + 1
            if length > max_lines:
                violations.append(
                    f"Clojure function '{v.get('name')}' at line {row} "
                    f"is {length} lines (max {max_lines})"
                )
    return violations


def check_kondo_golfing(analysis: Dict[str, Any]) -> List[str]:
    """Check for multiple var definitions on the same row via clj-kondo."""
    violations: List[str] = []
    seen_rows: set[int] = set()
    for v in analysis.get("var-definitions", []):
        row = v.get("row")
        if row in seen_rows:
            violations.append(
                f"Line {row}: anti-golfing violation (multiple forms on line)"
            )
        seen_rows.add(row)
    return violations


def extract_kondo_errors(kondo_data: Dict[str, Any]) -> List[str]:
    """Extract AST limit violations and syntax errors from clj-kondo."""
    analysis = kondo_data.get("analysis", {})
    errs = list(check_kondo_golfing(analysis))
    errs.extend(check_kondo_fn_lengths(analysis))
    for f in kondo_data.get("findings", []):
        if f.get("level") == "error":
            errs.append(f"Line {f.get('row', 1)}: {f.get('message')}")
    return errs


def check_clojure_ast_errors(source: str, label: str) -> List[str]:
    """Extract Clojure AST errors via clj-kondo or fallback."""
    kondo_data = run_clj_kondo(Path(label), content=source)
    if kondo_data:
        return extract_kondo_errors(kondo_data)
    forms = parse_clojure_forms(source)
    return detect_clojure_golfing(forms) + check_clojure_fn_lengths(forms)


def check_clojure_code(source: str, label: str = "<source>") -> Dict[str, Any]:
    """Analyze Clojure code via clj-kondo or balanced AST fallback."""
    lines = source.splitlines(keepends=True)
    errors: List[str] = []
    err = check_file_line_count(lines)
    if err:
        errors.append(err)
    errors.extend(check_clojure_ast_errors(source, label))
    return {
        "file": label,
        "valid": not errors,
        "errors": errors,
        "warnings": check_soft_line_lengths(lines),
    }


def check_single_file(path: Path) -> Dict[str, Any]:
    """Check a single Python or Clojure file on disk."""
    if not path.is_file():
        return {"file": str(path), "valid": True, "errors": [], "warnings": []}
    ext = path.suffix.lower()
    if ext in (".clj", ".cljs", ".cljc"):
        run_cljfmt_fix(path)
        content = path.read_text(encoding="utf-8", errors="replace")
        return check_clojure_code(content, str(path))
    elif ext == ".py":
        content = path.read_text(encoding="utf-8", errors="replace")
        return check_python_code(content, str(path))
    return {"file": str(path), "valid": True, "errors": [], "warnings": []}


def find_target_files(root: Path) -> List[Path]:
    """Find all Python and Clojure files in directory tree."""
    valid_exts = {".py", ".clj", ".cljs", ".cljc"}
    targets: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d != "__pycache__"
        ]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in valid_exts:
                targets.append(p)
    return sorted(targets)


def check_workspace(root: Path) -> List[Dict[str, Any]]:
    """Scan and analyze all relevant source files in workspace."""
    results = [check_single_file(p) for p in find_target_files(root)]
    return [r for r in results if not r["valid"] or r["warnings"]]


def filter_valid_paths(root: Path, names: Sequence[str]) -> List[Path]:
    """Filter relative file paths for valid code extensions."""
    valid_exts = {".py", ".clj", ".cljs", ".cljc"}
    res: List[Path] = []
    for n in names:
        p = root / n
        if p.suffix.lower() in valid_exts and p.is_file():
            res.append(p)
    return res


def get_staged_git_files(repo_dir: Path) -> Optional[List[Path]]:
    """Get list of staged files for controlled blast radius."""
    try:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
        res = subprocess.run(
            cmd, cwd=str(repo_dir), stdout=subprocess.PIPE, text=True, timeout=5
        )
        if res.returncode != 0:
            return None
        lines = [line.strip() for line in res.stdout.splitlines()]
        return filter_valid_paths(repo_dir, lines)
    except (subprocess.SubprocessError, OSError):
        return None


def get_modified_git_files(repo_dir: Path) -> Optional[List[Path]]:
    """Get modified and untracked files for stop gate check."""
    try:
        cmd = ["git", "status", "--porcelain"]
        res = subprocess.run(
            cmd, cwd=str(repo_dir), stdout=subprocess.PIPE, text=True, timeout=5
        )
        if res.returncode != 0:
            return None
        lines = [line[3:].strip() for line in res.stdout.splitlines()]
        return filter_valid_paths(repo_dir, lines)
    except (subprocess.SubprocessError, OSError):
        return None


def format_violation_reasons(violations: Sequence[Dict[str, Any]]) -> str:
    """Format violations into a readable diagnostic string."""
    reasons = [f"{v['file']}: {'; '.join(v['errors'])}" for v in violations]
    return f"Code limits violated: {' | '.join(reasons)}"


def check_commit_pre_tool(payload: Dict[str, Any]) -> Optional[str]:
    """Return denial reason if git commit violates limits."""
    workspace = Path(payload.get("cwd", ".")).resolve()
    staged = get_staged_git_files(workspace)
    targets = (
        [check_single_file(p) for p in staged]
        if staged is not None
        else check_workspace(workspace)
    )
    violations = [r for r in targets if not r["valid"]]
    return format_violation_reasons(violations) if violations else None


def handle_pre_tool_use(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Gate git commit tool calls with controlled blast radius."""
    tool_call = payload.get("toolCall", {})
    if tool_call.get("name") != "run_command":
        return {"decision": "allow"}
    cmd = tool_call.get("args", {}).get("CommandLine", "")
    if "git commit" not in cmd:
        return {"decision": "allow"}
    reason = check_commit_pre_tool(payload)
    if reason:
        return {"decision": "deny", "reason": reason}
    return {"decision": "allow"}


def handle_post_tool_use(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-format and check files modified by write_file or edit_file."""
    tool_call = payload.get("toolCall", {})
    args = tool_call.get("args", {})
    target_path = args.get("Path")
    if target_path:
        check_single_file(Path(target_path))
    return {}


def handle_stop(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Check workspace integrity before agent stop with blast radius."""
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
    if event == "PreToolUse":
        res = handle_pre_tool_use(data)
    elif event == "PostToolUse":
        res = handle_post_tool_use(data)
    elif event == "Stop":
        res = handle_stop(data)
    else:
        res = {"decision": "allow"}
    return json.dumps(res)


def parse_cli_args() -> argparse.Namespace:
    """Parse command line arguments for checking and hooks."""
    parser = argparse.ArgumentParser(description="Code limits enforcer")
    parser.add_argument(
        "--event", choices=["PreToolUse", "PostToolUse", "Stop"]
    )
    parser.add_argument("--check", type=str, help="Path to check")
    return parser.parse_args()


def run_cli_check(target: Path) -> int:
    """Run interactive or batch check on target path."""
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
        payload_str = sys.stdin.read()
        print(process_hook_payload(args.event, payload_str))
        return
    target = Path(args.check or ".").resolve()
    sys.exit(run_cli_check(target))


if __name__ == "__main__":
    main()
