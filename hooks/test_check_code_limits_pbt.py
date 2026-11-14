"""Hypothesis Property-Based Tests for AST Code Limits and Hooks.

Verifies:
1. Function length limits (<=20 pass, >20 fail for Python and Clojure).
2. File length limits (<=500 pass, >500 fail).
3. Anti-golfing detection (semicolons in Python, packed forms in Clojure).
4. Nested Clojure sibling expressions pass without false positives.
5. Soft 80-character line warnings.
6. cljfmt pre-formatting integration.
7. hooks.json stdin/stdout contract and controlled blast radius.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from typing import List

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

HOOKS_DIR = Path(__file__).resolve().parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from check_code_limits import (  # noqa: E402
    check_clojure_code,
    check_file_line_count,
    check_python_code,
    check_soft_line_lengths,
    detect_clojure_golfing,
    detect_python_golfing,
    handle_post_tool_use,
    handle_pre_tool_use,
    handle_stop,
    parse_clojure_forms,
    process_hook_payload,
    run_cljfmt_fix,
)


# ---------------------------------------------------------------------------
# Python AST Function & File Limits PBT
# ---------------------------------------------------------------------------


@given(body_lines=st.integers(min_value=1, max_value=18))
def test_prop_python_fn_within_limit_passes(body_lines: int) -> None:
    """Python functions <= 20 lines pass limit."""
    body = "\n".join(f"    x_{i} = {i}" for i in range(body_lines))
    code = f"def sample_fn():\n{body}\n    return x_0\n"
    res = check_python_code(code, "test_valid.py")
    assert res["valid"] is True
    assert len(res["errors"]) == 0


@given(body_lines=st.integers(min_value=22, max_value=40))
def test_prop_python_fn_over_limit_fails(body_lines: int) -> None:
    """Python functions > 20 lines trigger hard error."""
    body = "\n".join(f"    x_{i} = {i}" for i in range(body_lines))
    code = f"def oversized_fn():\n{body}\n    return 0\n"
    res = check_python_code(code, "test_invalid.py")
    assert res["valid"] is False
    assert any("max 20" in err for err in res["errors"])


@given(total_lines=st.integers(min_value=1, max_value=500))
def test_prop_file_line_count_pass(total_lines: int) -> None:
    """Files with <= 500 lines pass file limit."""
    lines = [f"line_{i}\n" for i in range(total_lines)]
    assert check_file_line_count(lines) is None


@given(total_lines=st.integers(min_value=501, max_value=700))
def test_prop_file_line_count_fail(total_lines: int) -> None:
    """Files with > 500 lines fail file limit."""
    lines = [f"line_{i}\n" for i in range(total_lines)]
    err = check_file_line_count(lines)
    assert err is not None
    assert "exceeds 500 lines" in err


# ---------------------------------------------------------------------------
# Anti-Golfing & Clojure Form PBT
# ---------------------------------------------------------------------------


@given(
    stmts=st.lists(
        st.text(alphabet="abcdef", min_size=1, max_size=5),
        min_size=2,
        max_size=5,
    )
)
def test_prop_python_semicolon_golfing_detected(stmts: List[str]) -> None:
    """Semicolon statement chaining is rejected as code-golfing."""
    code = "; ".join(f"{s} = 1" for s in stmts) + "\n"
    errs = detect_python_golfing(code)
    assert len(errs) > 0
    assert "semicolon chaining forbidden" in errs[0]


@settings(max_examples=20, deadline=None)
@given(
    names=st.lists(
        st.text(alphabet="abcdef", min_size=1, max_size=4),
        min_size=2,
        max_size=4,
    )
)
def test_prop_clojure_packed_forms_detected(names: List[str]) -> None:
    """Multiple top-level forms packed on a single line are rejected."""
    code = " ".join(f"(def {n} 1)" for n in names) + "\n"
    res = check_clojure_code(code, "test_packed.clj")
    assert res["valid"] is False
    assert any("anti-golfing" in err for err in res["errors"])


@settings(max_examples=20, deadline=None)
@given(
    ops=st.lists(
        st.sampled_from(["inc", "dec", "identity"]),
        min_size=2,
        max_size=4,
    )
)
def test_prop_clojure_nested_sibling_calls_pass(ops: List[str]) -> None:
    """Nested sibling calls like [(inc x) (dec x)] pass cleanly."""
    body = " ".join(f"({op} x)" for op in ops)
    code = f"(defn calc [x]\n  [{body}])\n"
    res = check_clojure_code(code, "test_nested.clj")
    assert res["valid"] is True
    assert len(res["errors"]) == 0


@settings(max_examples=20, deadline=None)
@given(num_forms=st.integers(min_value=1, max_value=8))
def test_prop_clojure_short_fn_passes(num_forms: int) -> None:
    """Clojure defn <= 20 lines passes checks."""
    body = "\n".join(f"    (+ {i} 1)" for i in range(num_forms))
    code = f"(defn compute-clean\n  [x]\n{body})\n"
    res = check_clojure_code(code, "test_clean.clj")
    assert res["valid"] is True
    assert len(res["errors"]) == 0


@settings(max_examples=20, deadline=None)
@given(num_lines=st.integers(min_value=25, max_value=40))
def test_prop_clojure_long_fn_fails(num_lines: int) -> None:
    """Clojure defn > 20 lines fails checks."""
    body = "\n".join(f"    (+ {i} 1)" for i in range(num_lines))
    code = f"(defn compute-long\n  [x]\n{body})\n"
    res = check_clojure_code(code, "test_long.clj")
    assert res["valid"] is False
    assert any("max 20" in err for err in res["errors"])


# ---------------------------------------------------------------------------
# Soft Line Length Limit PBT
# ---------------------------------------------------------------------------


@given(line_len=st.integers(min_value=1, max_value=80))
def test_prop_soft_line_length_under_80_no_warnings(line_len: int) -> None:
    """Lines <= 80 characters produce zero warnings."""
    lines = ["a" * line_len + "\n"]
    warnings = check_soft_line_lengths(lines)
    assert len(warnings) == 0


@given(line_len=st.integers(min_value=81, max_value=120))
def test_prop_soft_line_length_over_80_warns(line_len: int) -> None:
    """Lines > 80 characters produce soft warnings without blocking."""
    lines = ["x" * line_len + "\n"]
    warnings = check_soft_line_lengths(lines)
    assert len(warnings) == 1
    assert "exceeds 80 characters" in warnings[0]


# ---------------------------------------------------------------------------
# Clojure Formatting & Hooks Contract Tests
# ---------------------------------------------------------------------------


def test_clojure_syntax_error_fails() -> None:
    """Invalid Clojure syntax fails via clj-kondo diagnostics."""
    broken_code = "(defn broken [x\n"
    res = check_clojure_code(broken_code, "test_broken.clj")
    assert res["valid"] is False
    assert len(res["errors"]) > 0


def test_cljfmt_preformatting_integration() -> None:
    """cljfmt fix successfully cleans unindented Clojure source."""
    messy_clj = "(defn add-two\n[a b]\n(+ a b))\n"
    with tempfile.NamedTemporaryFile(suffix=".clj", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_text(messy_clj, encoding="utf-8")
    try:
        ok = run_cljfmt_fix(tmp_path)
        formatted = tmp_path.read_text(encoding="utf-8")
        assert ok is True
        assert "  [a b]" in formatted
    finally:
        tmp_path.unlink(missing_ok=True)


def test_hooks_pre_tool_use_allow() -> None:
    """PreToolUse allows non-commit commands."""
    payload = json.dumps({
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": "git status"},
        }
    })
    out = json.loads(process_hook_payload("PreToolUse", payload))
    assert out["decision"] == "allow"


def test_hooks_pre_tool_use_deny_git_commit() -> None:
    """PreToolUse denies git commit if workspace has violations."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        bad_file = tmp / "bad.py"
        bad_file.write_text("a = 1; b = 2\n", encoding="utf-8")
        payload = json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git commit -m test"},
            },
            "cwd": str(tmp),
        })
        out = json.loads(process_hook_payload("PreToolUse", payload))
        assert out["decision"] == "deny"
        assert "semicolon" in out["reason"]


def test_hooks_post_tool_use_contract() -> None:
    """PostToolUse always returns an empty JSON object."""
    payload = json.dumps({
        "toolCall": {
            "name": "write_file",
            "args": {"Path": "clean.py"},
        }
    })
    out = json.loads(process_hook_payload("PostToolUse", payload))
    assert out == {}


def test_hooks_stop_contract() -> None:
    """Stop allows agent to exit when continuationActive is True."""
    payload = json.dumps({"continuationActive": True})
    out = json.loads(process_hook_payload("Stop", payload))
    assert out["decision"] == "allow"
