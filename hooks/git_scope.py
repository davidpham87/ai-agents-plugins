"""Git command parsing and index/status scoping for Antigravity hooks.

Detects real `git commit` invocations (handling global options like `-C`,
pipelines, and chained commands without substring false positives) and reads
staged git index blobs (`git show :<path>`) or `git status --porcelain -z`.
"""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

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


_COMMIT_VAL_OPTS = {
    "-m", "--message", "-F", "--file", "-C", "--reuse-message",
    "-c", "--reedit-message", "-t", "--template", "--author", "--date",
}


def _has_commit_all_flag(args: Sequence[str]) -> bool:
    """Return True if commit args include -a, --all, or -am cluster."""
    idx = 0
    while idx < len(args):
        tok = args[idx]
        if tok == "--":
            break
        if tok in _COMMIT_VAL_OPTS:
            idx += 2
            continue
        if tok == "--all" or (
            tok.startswith("-") and not tok.startswith("--") and "a" in tok
        ):
            return True
        idx += 1
    return False


def _parse_git_commit_seg(tokens: Sequence[str]) -> Optional[Tuple[str, bool]]:
    """Return (c_dir, include_all) if tokens invoke `git ... commit`."""
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
            if tok == "commit":
                return c_dir, _has_commit_all_flag(tokens[idx + 1 :])
            return None
    return None


def detect_git_commit(
    cmd: str, default_cwd: Path
) -> Optional[Tuple[Path, bool]]:
    """Return (repo_cwd, include_all) if cmd runs `git commit`, else None."""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";|&()")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return None
    for seg in _split_tokens_by_ops(tokens):
        parsed = _parse_git_commit_seg(seg)
        if parsed is not None:
            c_dir, inc_all = parsed
            cwd = (default_cwd / c_dir).resolve() if c_dir else default_cwd
            return cwd, inc_all
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


def _add_unstaged_tracked(repo_dir: Path, blobs: Dict[Path, str]) -> None:
    """Add unstaged modified tracked files for `git commit -a`."""
    raw = _run_git_bytes(
        repo_dir, ["diff", "--name-only", "--diff-filter=ACM", "-z"]
    )
    if raw is None:
        return
    for entry in raw.split(b"\x00"):
        rel = entry.decode("utf-8", errors="replace").strip()
        p = repo_dir / rel
        if rel and p.suffix.lower() in VALID_EXTS and p.is_file():
            blobs[p] = p.read_text(encoding="utf-8", errors="replace")


def get_staged_blobs(
    repo_dir: Path, include_all: bool = False
) -> Optional[Dict[Path, str]]:
    """Read staged index blobs via `git show :<path>` (plus `-a` workdir)."""
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
    if include_all:
        _add_unstaged_tracked(repo_dir, blobs)
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
