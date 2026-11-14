"""Git command parsing and index/status scoping for Antigravity hooks.

Detects real `git commit` invocations (handling global options like `-C`,
pipelines, and chained commands without substring false positives) and reads
staged git index blobs (`git show :<path>`) or `git status --porcelain -z`.
"""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
from typing import Dict, List, Optional, Sequence

VALID_EXTS = {".py", ".clj", ".cljs", ".cljc"}
_GIT_VAL_OPTS = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"
}


def _split_tokens_by_ops(tokens: Sequence[str]) -> List[List[str]]:
    """Split shlex tokens into command segments on shell operators."""
    ops = {";", "&&", "||", "|", "&", "(", ")"}
    segments: List[List[str]] = []
    curr: List[str] = []
    for tok in tokens:
        if tok in ops:
            if curr:
                segments.append(curr)
                curr = []
        else:
            curr.append(tok)
    if curr:
        segments.append(curr)
    return segments


def _parse_git_commit_seg(tokens: Sequence[str]) -> Optional[str]:
    """Return `-C` dir (or '') if tokens invoke `git ... commit`."""
    if not tokens or Path(tokens[0]).name != "git":
        return None
    idx, c_dir = 1, ""
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in _GIT_VAL_OPTS:
            if tok == "-C" and idx + 1 < len(tokens):
                c_dir = tokens[idx + 1]
            idx += 2
        elif tok.startswith("-"):
            idx += 1
        else:
            return c_dir if tok == "commit" else None
    return None


def detect_git_commit(cmd: str, default_cwd: Path) -> Optional[Path]:
    """Return target repo cwd if cmd executes `git commit`, else None."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";|&()")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None
    for seg in _split_tokens_by_ops(tokens):
        c_dir = _parse_git_commit_seg(seg)
        if c_dir is not None:
            return (default_cwd / c_dir).resolve() if c_dir else default_cwd
    return None


def _run_git_bytes(cwd: Path, args: Sequence[str]) -> Optional[bytes]:
    """Execute git command and return raw stdout bytes on success."""
    try:
        res = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, timeout=5
        )
        return res.stdout if res.returncode == 0 else None
    except (subprocess.SubprocessError, OSError):
        return None


def get_staged_blobs(repo_dir: Path) -> Optional[Dict[Path, str]]:
    """Read staged index blobs via `git show :<path>`."""
    raw = _run_git_bytes(
        repo_dir, ["diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"]
    )
    if raw is None:
        return None
    blobs: Dict[Path, str] = {}
    for entry in raw.split(b"\x00"):
        rel = entry.decode("utf-8", errors="replace").strip()
        if not rel or Path(rel).suffix.lower() not in VALID_EXTS:
            continue
        blob = _run_git_bytes(repo_dir, ["show", f":{rel}"])
        if blob is not None:
            blobs[repo_dir / rel] = blob.decode("utf-8", errors="replace")
    return blobs


def get_modified_git_files(repo_dir: Path) -> Optional[List[Path]]:
    """Parse `git status --porcelain -z` (handling renames) for Stop gate."""
    raw = _run_git_bytes(repo_dir, ["status", "--porcelain", "-z"])
    if raw is None:
        return None
    parts = raw.split(b"\x00")
    files: List[Path] = []
    idx = 0
    while idx < len(parts):
        entry = parts[idx].decode("utf-8", errors="replace")
        idx += 1
        if len(entry) < 4:
            continue
        if entry[0] in ("R", "C") or entry[1] in ("R", "C"):
            idx += 1
        p = repo_dir / entry[3:]
        if p.suffix.lower() in VALID_EXTS and p.is_file():
            files.append(p)
    return files
