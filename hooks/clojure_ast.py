"""Clojure AST analysis, formatting, and fallback scanner for code limits.

Uses `cljfmt` (in-memory stdin for checks, on-disk for PostToolUse) and
`clj-kondo` JSON AST/diagnostics, with a balanced-form fallback scanner
when `clj-kondo` is unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple


def lang_for_path(path: Path) -> str:
    """Return clj-kondo language flag for a Clojure file extension."""
    ext = path.suffix.lower()
    if ext == ".cljs":
        return "cljs"
    if ext == ".cljc":
        return "cljc"
    return "clj"


def format_clojure_stdin(source: str) -> str:
    """Format Clojure source in memory via cljfmt without touching disk."""
    cmd = shutil.which("cljfmt")
    if not cmd:
        return source
    try:
        res = subprocess.run(
            [cmd, "fix", "-"],
            input=source,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return res.stdout if res.returncode == 0 and res.stdout else source
    except (subprocess.SubprocessError, OSError):
        return source


def format_clojure_file(file_path: Path) -> bool:
    """Format Clojure file on disk via cljfmt or clojure-lsp."""
    if not file_path.exists():
        return False
    for tool, args_fn in (
        ("cljfmt", lambda c: [c, "fix", str(file_path)]),
        ("clojure-lsp", lambda c: [c, "format", "--filenames", str(file_path)]),
    ):
        cmd = shutil.which(tool)
        if cmd:
            try:
                res = subprocess.run(
                    args_fn(cmd), capture_output=True, timeout=10
                )
                return res.returncode == 0
            except (subprocess.SubprocessError, OSError):
                pass
    return False


def run_clj_kondo(source: str, lang: str = "clj") -> Optional[Dict[str, Any]]:
    """Run clj-kondo on stdin source and return parsed JSON output."""
    cmd = shutil.which("clj-kondo")
    if not cmd:
        return None
    cfg = "{:output {:format :json} :analysis true}"
    args = [cmd, "--lint", "-", "--lang", lang, "--config", cfg]
    try:
        res = subprocess.run(
            args, input=source, capture_output=True, text=True, timeout=10
        )
        return json.loads(res.stdout) if res.stdout.strip() else None
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None


def check_kondo_fn_lengths(
    analysis: Dict[str, Any], max_lines: int = 20
) -> List[str]:
    """Check defn/defn-/defmacro/defmethod/fn lengths from clj-kondo."""
    errs: List[str] = []
    for v in analysis.get("var-definitions", []):
        if any(k in v.get("defined-by", "") for k in ("defn", "defmacro")):
            errs.extend(_span_err(v.get("name", "fn"), v, max_lines))
    for u in analysis.get("var-usages", []):
        if u.get("name") in ("defmethod", "fn"):
            errs.extend(_span_err(u["name"], u, max_lines))
    return errs


def _span_err(name: str, item: Dict[str, Any], max_lines: int) -> List[str]:
    """Return error list if item row..end-row exceeds max_lines."""
    row, end_row = item.get("row", 1), item.get("end-row", 1)
    length = end_row - row + 1
    if length > max_lines:
        return [
            f"Clojure '{name}' at line {row} is {length}L (max {max_lines})"
        ]
    return []


def check_kondo_golfing(analysis: Dict[str, Any]) -> List[str]:
    """Reject multiple top-level definitions/methods packed on one line."""
    errs: List[str] = []
    seen: set[Tuple[int, str]] = set()
    usages = [
        u for u in analysis.get("var-usages", [])
        if u.get("name") == "defmethod"
    ]
    for item in list(analysis.get("var-definitions", [])) + usages:
        row, lang = item.get("row"), item.get("lang", "clj")
        if (row, lang) in seen:
            errs.append(f"Line {row}: anti-golfing (multiple forms on line)")
        if row is not None:
            seen.add((row, lang))
    return errs


def extract_kondo_errors(kondo_data: Dict[str, Any]) -> List[str]:
    """Extract AST limit violations and syntax errors from clj-kondo."""
    analysis = kondo_data.get("analysis", {})
    errs = check_kondo_golfing(analysis) + check_kondo_fn_lengths(analysis)
    for f in kondo_data.get("findings", []):
        if f.get("level") == "error":
            errs.append(f"Line {f.get('row', 1)}: {f.get('message')}")
    return errs


def _advance_scanner(
    src: str, idx: int, state: Dict[str, Any]
) -> Tuple[int, Optional[str]]:
    """Advance Clojure fallback scanner by one character or escape."""
    ch = src[idx]
    if state["in_comment"]:
        state["in_comment"] = ch != "\n"
        return idx + 1, None
    if state["in_str"]:
        if ch == "\\":
            return idx + 2, None
        state["in_str"] = ch != '"'
        return idx + 1, None
    if ch == "\\":
        return idx + 2, None
    if ch in ';"':
        state["in_comment" if ch == ";" else "in_str"] = True
        return idx + 1, None
    return idx + 1, ch


def _record_edge(
    ch: str, line: int, snippet: str, state: Dict[str, Any], forms: List[Dict]
) -> None:
    """Update paren/brace/bracket depth and record top-level forms."""
    if ch in "([{":
        if state["depth"] == 0:
            state["start"], state["snippet"] = line, snippet
        state["depth"] += 1
    elif ch in ")]}":
        state["depth"] = max(0, state["depth"] - 1)
        if state["depth"] == 0 and state["start"] is not None:
            forms.append({
                "start": state["start"],
                "end": line,
                "length": line - state["start"] + 1,
                "snippet": state["snippet"],
            })
            state["start"] = None


def parse_clojure_forms(source: str) -> List[Dict[str, Any]]:
    """Fallback balanced-form scanner handling escapes, chars, comments."""
    forms: List[Dict[str, Any]] = []
    state: Dict[str, Any] = {
        "depth": 0, "in_str": False, "in_comment": False,
        "start": None, "snippet": "",
    }
    idx, line, n = 0, 1, len(source)
    while idx < n:
        if source[idx] == "\n":
            line += 1
        next_idx, ch = _advance_scanner(source, idx, state)
        if ch is not None and ch in "([{}])":
            _record_edge(ch, line, source[idx : idx + 30], state, forms)
        idx = next_idx
    return forms


def check_fallback_fn_lengths(
    forms: Sequence[Dict[str, Any]], max_lines: int = 20
) -> List[str]:
    """Check Clojure function lengths using fallback form spans."""
    kws = (
        "(defn ", "(defn- ", "(fn ", "(defmulti ", "(defmethod ", "(defmacro "
    )
    errs: List[str] = []
    for form in forms:
        if any(kw in form.get("snippet", "") for kw in kws):
            if form["length"] > max_lines:
                errs.append(
                    f"Clojure fn at line {form['start']} is "
                    f"{form['length']}L (max {max_lines})"
                )
    return errs


def check_fallback_golfing(forms: Sequence[Dict[str, Any]]) -> List[str]:
    """Reject multiple top-level forms sharing a line in fallback mode."""
    errs: List[str] = []
    for i in range(1, len(forms)):
        if forms[i]["start"] <= forms[i - 1]["end"]:
            errs.append(
                f"Line {forms[i]['start']}: anti-golfing "
                "(multiple top-level forms on line)"
            )
    return errs


def analyze_clojure_ast(
    source: str, path: Path, use_kondo: bool = True
) -> List[str]:
    """Run in-memory cljfmt + clj-kondo (or fallback) AST checks."""
    formatted = format_clojure_stdin(source)
    if use_kondo:
        kondo_data = run_clj_kondo(formatted, lang=lang_for_path(path))
        if kondo_data is not None:
            return extract_kondo_errors(kondo_data)
    forms = parse_clojure_forms(formatted)
    return check_fallback_golfing(forms) + check_fallback_fn_lengths(forms)
