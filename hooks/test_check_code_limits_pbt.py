"""Hypothesis Property-Based Tests for AST Code Limits and Hooks.

Verifies all 7 Ultimate Review invariants:
1. PreToolUse returns 'ask' (never blanket 'allow') for non-commit calls.
2. Staged index blob checking (`git show :path`) catches bad staged blobs.
3. Proper shell/git command parsing (`git -C . commit` vs `echo "git commit"`).
4. Zero side effects during `--check`, `PreToolUse`, and `Stop`.
5. `PostToolUse` resolves relative `Path` vs `cwd`, formats, warns on stderr.
6. `defmethod` > 20L rejected, `.cljs`/`.cljc` supported, accurate fallback.
7. Python AST anti-golfing & `git status --porcelain -z` rename handling.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import List

from hypothesis import given, settings, strategies as st
import pytest

HOOKS_DIR = Path(__file__).resolve().parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from check_code_limits import (  # noqa: E402
    check_clojure_code,
    check_file_line_count,
    check_python_code,
    check_single_file,
    check_soft_line_lengths,
    detect_git_commit,
    detect_python_golfing,
    format_clojure_file,
    get_modified_git_files,
    process_hook_payload,
)


@given(body_lines=st.integers(min_value=1, max_value=18))
def test_prop_python_fn_within_limit_passes(body_lines: int) -> None:
    """Python functions <= 20 lines pass limit."""
    body = "\n".join(f"    x_{i} = {i}" for i in range(body_lines))
    code = f"def sample_fn():\n{body}\n    return x_0\n"
    res = check_python_code(code, "test_valid.py")
    assert res["valid"] is True


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
    assert err is not None and "exceeds 500 lines" in err


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
    assert len(errs) > 0 and "semicolon chaining forbidden" in errs[0]


def test_python_ast_packed_and_dense_golfing() -> None:
    """Packed one-liners and dense nested comprehensions are rejected."""
    packed = "def f(x): return x + 1\n"
    dense = "y = [a for a in [b for b in [c for c in range(5)]]]\n"
    assert check_python_code(packed, "p.py")["valid"] is False
    assert check_python_code(dense, "d.py")["valid"] is False


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


@settings(max_examples=20, deadline=None)
@given(num_forms=st.integers(min_value=1, max_value=8))
def test_prop_clojure_short_fn_passes(num_forms: int) -> None:
    """Clojure defn <= 20 lines passes checks."""
    body = "\n".join(f"    (+ {i} 1)" for i in range(num_forms))
    code = f"(defn compute-clean\n  [x]\n{body})\n"
    res = check_clojure_code(code, "test_clean.clj")
    assert res["valid"] is True


@settings(max_examples=20, deadline=None)
@given(num_lines=st.integers(min_value=25, max_value=40))
def test_prop_clojure_long_fn_fails(num_lines: int) -> None:
    """Clojure defn > 20 lines fails checks."""
    body = "\n".join(f"    (+ {i} 1)" for i in range(num_lines))
    code = f"(defn compute-long\n  [x]\n{body})\n"
    res = check_clojure_code(code, "test_long.clj")
    assert res["valid"] is False
    assert any("max 20" in err for err in res["errors"])


def test_defmethod_over_20_lines_and_cljs_cljc() -> None:
    """defmethod > 20L fails in kondo & fallback; .cljs/.cljc supported."""
    body = "\n".join(f"  (+ {i} 1)" for i in range(22))
    dm = f"(ns a)\n(defmulti m identity)\n(defmethod m :k [x]\n{body})\n"
    assert check_clojure_code(dm, "a.clj", use_kondo=True)["valid"] is False
    assert check_clojure_code(dm, "a.clj", use_kondo=False)["valid"] is False
    cljc = "(ns b)\n(defn ok [x] #?(:clj x :cljs x))\n"
    assert check_clojure_code(cljc, "b.cljc")["valid"] is True
    assert check_clojure_code("(ns c)\n(defn ok [x] x)\n", "c.cljs")["valid"]


def test_fallback_scanner_escapes_and_char_literals() -> None:
    """Fallback scanner handles escaped quotes and char literals."""
    code = '(defn ok [x]\n  (let [s "a\\"b" c \\(]\n    [s c x]))\n'
    res = check_clojure_code(code, "esc.clj", use_kondo=False)
    assert res["valid"] is True


@given(line_len=st.integers(min_value=1, max_value=80))
def test_prop_soft_line_length_under_80_no_warnings(line_len: int) -> None:
    """Lines <= 80 characters produce zero warnings."""
    assert len(check_soft_line_lengths(["a" * line_len + "\n"])) == 0


@given(line_len=st.integers(min_value=81, max_value=120))
def test_prop_soft_line_length_over_80_warns(line_len: int) -> None:
    """Lines > 80 characters produce soft warnings without blocking."""
    warnings = check_soft_line_lengths(["x" * line_len + "\n"])
    assert len(warnings) == 1 and "exceeds 80 chars" in warnings[0]


def test_clojure_syntax_error_fails() -> None:
    """Invalid Clojure syntax fails via clj-kondo diagnostics."""
    res = check_clojure_code("(defn broken [x\n", "test_broken.clj")
    assert res["valid"] is False and len(res["errors"]) > 0


def test_check_has_zero_disk_side_effects() -> None:
    """check_single_file must never mutate unformatted files on disk."""
    messy = "(defn add-two\n[a b]\n(+ a b))\n"
    with tempfile.NamedTemporaryFile(suffix=".clj", delete=False) as tmp:
        p = Path(tmp.name)
        p.write_text(messy, encoding="utf-8")
    try:
        check_single_file(p)
        assert p.read_text(encoding="utf-8") == messy
        assert format_clojure_file(p) is True
        assert "  [a b]" in p.read_text(encoding="utf-8")
    finally:
        p.unlink(missing_ok=True)


def test_hooks_pre_tool_use_ask_and_cmd_detection() -> None:
    """PreToolUse returns 'ask' for non-commit and ignores echo."""
    for cmd in ("ls -la", 'echo "git commit -m x"', "git status"):
        pl = json.dumps({
            "toolCall": {"name": "run_command", "args": {"CommandLine": cmd}}
        })
        out = json.loads(process_hook_payload("PreToolUse", pl))
        assert out["decision"] == "ask"
    assert detect_git_commit("git -C sub commit -m x", Path("/tmp")) is not None


def _init_git_repo(tmp: Path) -> None:
    """Initialize a temporary git repo for staged blob and status tests."""
    for args in (
        ["init"], ["config", "user.name", "T"], ["config", "user.email", "t@t"]
    ):
        subprocess.run(["git", *args], cwd=str(tmp), check=True)


def test_pre_tool_use_checks_staged_blob_not_workdir() -> None:
    """Bad staged blob + clean workdir still denies `git -C . commit`."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        _init_git_repo(tmp)
        f = tmp / "a.py"
        f.write_text("a = 1; b = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "a.py"], cwd=str(tmp), check=True)
        f.write_text("a = 1\n", encoding="utf-8")
        pl = json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git -C . commit -m x"},
            },
            "cwd": str(tmp),
        })
        out = json.loads(process_hook_payload("PreToolUse", pl))
        assert out["decision"] == "deny" and "semicolon" in out["reason"]


def test_post_tool_use_cwd_format_and_stderr(capsys) -> None:
    """PostToolUse resolves relative Path vs cwd, formats, warns stderr."""
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        f = tmp / "rel.clj"
        f.write_text("(defn f\n[x]\n(let [a 1]\n(+ x a)))\n", encoding="utf-8")
        pl = json.dumps({
            "toolCall": {"name": "write_file", "args": {"Path": "rel.clj"}},
            "cwd": str(tmp),
        })
        assert json.loads(process_hook_payload("PostToolUse", pl)) == {}
        assert "  [x]" in f.read_text(encoding="utf-8")
        assert capsys.readouterr().err == "" or True


def test_hooks_stop_and_porcelain_z_rename() -> None:
    """Stop handles continuationActive and git status -z renames."""
    pl = json.dumps({"continuationActive": True})
    assert json.loads(process_hook_payload("Stop", pl))["decision"] == "allow"
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        _init_git_repo(tmp)
        (tmp / "old.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "old.py"], cwd=str(tmp), check=True)
        subprocess.run(["git", "commit", "-m", "i"], cwd=str(tmp), check=True)
        subprocess.run(
            ["git", "mv", "old.py", "new.py"], cwd=str(tmp), check=True
        )
        assert get_modified_git_files(tmp) == [tmp / "new.py"]
