"""Git subprocess execution and pipeline runners for Async vs Sync Benchmark.

Isolates all side effects (git CLI operations, temp directories, thread pools)
at the outer shell boundary while delegating metrics to `benchmark_pure`.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
import queue
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from benchmark_pure import (
    pure_aggregate_metrics,
    pure_calculate_lag,
)


def git_run(cwd: Path, *args: str) -> str:
    """Run a git command in cwd and return stripped stdout."""
    res = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"git failed: {' '.join(args)} in {cwd}: {res.stderr}"
        )
    return res.stdout.strip()


def init_repo(base_dir: Path) -> Path:
    """Initialize a git repo with main branch and an initial commit."""
    repo = base_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    git_run(repo, "init", "-b", "main")
    git_run(repo, "config", "user.name", "BenchmarkRunner")
    git_run(repo, "config", "user.email", "runner@example.internal")
    git_run(repo, "config", "commit.gpgSign", "false")
    (repo / "README.md").write_text("# Benchmark Git Repo\n", encoding="utf-8")
    git_run(repo, "add", "README.md")
    git_run(repo, "commit", "-m", "Initial commit on main")
    return repo


def check_conflicts(repo: Path, subteams: Sequence[str]) -> int:
    """Check for git merge conflicts across subteam branches."""
    conflicts = 0
    for st in subteams:
        try:
            git_run(repo, "merge-tree", "main", f"subteam/{st}/work")
        except RuntimeError:
            conflicts += 1
    return conflicts


def _commit_increment(
    tree: Path, subteam: str, idx: int, work_sec: float, prefix: str = ""
) -> Dict[str, Any]:
    """Perform work latency and create a real git commit for an increment."""
    if work_sec > 0:
        time.sleep(work_sec)
    subteam_dir = tree / "skills" / f"subteam-{subteam}"
    subteam_dir.mkdir(parents=True, exist_ok=True)
    target = subteam_dir / f"step_{idx}.txt"
    msg = f"{prefix}subteam={subteam} increment={idx} time={time.time()}\n"
    target.write_text(msg, encoding="utf-8")
    git_run(tree, "add", str(target))
    git_run(tree, "commit", "-m", f"{prefix}subteam {subteam} commit {idx}")
    sha = git_run(tree, "rev-parse", "HEAD")
    return {
        "subteam": subteam, "idx": idx, "sha": sha, "commit_time": time.time()
    }


def _audit_increment(
    tree: Path, commit_ev: Dict[str, Any], review_sec: float
) -> Dict[str, Any]:
    """Audit a committed SHA using git show and bounded review latency."""
    t_start = time.time()
    if review_sec > 0:
        time.sleep(review_sec)
    git_run(tree, "show", "--stat", commit_ev["sha"])
    return {
        "subteam": commit_ev["subteam"],
        "idx": commit_ev["idx"],
        "sha": commit_ev["sha"],
        "audit_start": t_start,
        "audit_end": time.time(),
        "lag_sec": pure_calculate_lag(commit_ev["commit_time"], t_start),
    }


def run_sync_subteam(
    repo: Path,
    subteam: str,
    increments: int,
    work_sec: float,
    review_sec: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute a synchronous sequential workflow for a single subteam."""
    git_run(repo, "checkout", "-b", f"subteam/{subteam}/work", "main")
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []
    for i in range(increments):
        c_ev = _commit_increment(repo, subteam, i, work_sec)
        commits.append(c_ev)
        audits.append(_audit_increment(repo, c_ev, review_sec))
    return commits, audits


def _setup_sync_clone(tmp_path: Path, repo: Path, st: str) -> Path:
    """Create an isolated clone for parallel sync subteam execution."""
    clone_dir = tmp_path / f"clone_{st}"
    git_run(tmp_path, "clone", str(repo), str(clone_dir))
    git_run(clone_dir, "config", "user.name", f"Dev-{st}")
    git_run(clone_dir, "config", "user.email", f"dev-{st}@example.internal")
    return clone_dir


def _run_sync_clone(
    tmp_path: Path, repo: Path, st: str, cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Clone and execute a single sync subteam, then push its branch."""
    c_dir = _setup_sync_clone(tmp_path, repo, st)
    c, a = run_sync_subteam(
        c_dir, st, cfg["increments"],
        cfg["work_latency_sec"], cfg["review_latency_sec"],
    )
    git_run(c_dir, "push", "origin", f"subteam/{st}/work")
    return c, a


def _run_sync_parallel(
    tmp_path: Path, repo: Path, cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run sync subteams in parallel clones (still blocking internally)."""
    subteams = cfg["subteams"]
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(subteams)) as p:
        futs = [
            p.submit(_run_sync_clone, tmp_path, repo, st, cfg)
            for st in subteams
        ]
        for fut in futs:
            c, a = fut.result()
            commits.extend(c)
            audits.extend(a)
    return commits, audits


def run_sync_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run the synchronous benchmark pipeline."""
    with tempfile.TemporaryDirectory(prefix="bm_sync_") as tmp_str:
        tmp_path = Path(tmp_str)
        repo = init_repo(tmp_path)
        t0 = time.time()
        if config.get("serialize_sync_teams", True):
            commits, audits = _run_sync_serial(repo, config)
        else:
            commits, audits = _run_sync_parallel(tmp_path, repo, config)
        dur = time.time() - t0
        conflicts = check_conflicts(repo, config["subteams"])
        metrics = pure_aggregate_metrics(
            "synchronous", commits, audits, dur, conflicts
        )
        return {"metrics": metrics, "commits": commits, "audits": audits}


def _run_sync_serial(
    repo: Path, cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run sync subteams sequentially on the repository."""
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []
    for st in cfg["subteams"]:
        c, a = run_sync_subteam(
            repo,
            st,
            cfg["increments"],
            cfg["work_latency_sec"],
            cfg["review_latency_sec"],
        )
        commits.extend(c)
        audits.extend(a)
    return commits, audits


def _setup_async_worktrees(
    base_dir: Path, repo: Path, subteam: str
) -> Tuple[Path, Path]:
    """Create disjoint exec and review git worktrees for a subteam."""
    exec_tree = base_dir / f"worktree_{subteam}_exec"
    rev_tree = base_dir / f"worktree_{subteam}_rev"
    git_run(
        repo, "worktree", "add", "-b", f"subteam/{subteam}/work",
        str(exec_tree), "main"
    )
    git_run(
        repo, "worktree", "add", "-b", f"subteam/{subteam}/review",
        str(rev_tree), "main"
    )
    return exec_tree, rev_tree


def _async_exec_worker(
    exec_tree: Path,
    subteam: str,
    increments: int,
    work_sec: float,
    handoff_q: queue.Queue[Optional[Dict[str, Any]]],
    commits: List[Dict[str, Any]],
) -> None:
    """Continuously commit increments and enqueue SHAs without blocking."""
    for i in range(increments):
        ev = _commit_increment(exec_tree, subteam, i, work_sec, "async ")
        commits.append(ev)
        handoff_q.put(ev)
    handoff_q.put(None)


def _async_rev_worker(
    rev_tree: Path,
    review_sec: float,
    handoff_q: queue.Queue[Optional[Dict[str, Any]]],
    audits: List[Dict[str, Any]],
) -> None:
    """Concurrently audit committed SHAs from the handoff queue."""
    while True:
        item = handoff_q.get()
        if item is None:
            handoff_q.task_done()
            break
        audits.append(_audit_increment(rev_tree, item, review_sec))
        handoff_q.task_done()


def run_async_subteam(
    base_dir: Path,
    repo: Path,
    subteam: str,
    increments: int,
    work_sec: float,
    review_sec: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute an async subteam with concurrent exec and review worktrees."""
    ex, rev = _setup_async_worktrees(base_dir, repo, subteam)
    q: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue()
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_r = pool.submit(_async_rev_worker, rev, review_sec, q, audits)
        f_e = pool.submit(
            _async_exec_worker, ex, subteam, increments, work_sec, q, commits
        )
        f_e.result(), f_r.result()
    return commits, audits


def run_async_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run the asynchronous benchmark pipeline with concurrent subteams."""
    with tempfile.TemporaryDirectory(prefix="bm_async_") as tmp_str:
        tmp_path = Path(tmp_str)
        repo = init_repo(tmp_path)
        subteams = config["subteams"]
        t0 = time.time()
        commits, audits = _run_async_pool(tmp_path, repo, config)
        dur = time.time() - t0
        conflicts = check_conflicts(repo, subteams)
        metrics = pure_aggregate_metrics(
            "asynchronous", commits, audits, dur, conflicts
        )
        return {"metrics": metrics, "commits": commits, "audits": audits}


def _run_async_pool(
    tmp_path: Path, repo: Path, cfg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Dispatch all async subteams concurrently in a thread pool."""
    subteams, inc = cfg["subteams"], cfg["increments"]
    w_sec, r_sec = cfg["work_latency_sec"], cfg["review_latency_sec"]
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(subteams)) as p:
        futs = [
            p.submit(run_async_subteam, tmp_path, repo, st, inc, w_sec, r_sec)
            for st in subteams
        ]
        for fut in futs:
            c, a = fut.result()
            commits.extend(c)
            audits.extend(a)
    return commits, audits
