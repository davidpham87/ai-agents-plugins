#!/usr/bin/env python3
"""Benchmark comparing Asynchronous Swarm Teamwork vs Synchronous Blocking.

Demonstrates the performance advantages of disjoint git branches,
continuous executioner commits, and concurrent reviewer worktrees
versus synchronous stop-and-wait handoffs.

Follows Rich Hickey's functional design principles:
- Information is represented as plain data (immutable dicts and tuples).
- Pure calculation functions are separated from I/O boundaries.
- Side effects (git subprocess execution, timers) live on the perimeter.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Pure Calculation Helpers (Rich Hickey: Data in, Data out, Zero complecting)
# ---------------------------------------------------------------------------


def pure_make_config(
    subteams: Sequence[str] = ("fc", "sw", "bm"),
    increments: int = 4,
    work_latency_sec: float = 0.05,
    review_latency_sec: float = 0.05,
    serialize_sync_teams: bool = True,
) -> Dict[str, Any]:
    """Create a pure configuration dictionary."""
    return {
        "subteams": list(subteams),
        "increments": int(increments),
        "work_latency_sec": float(work_latency_sec),
        "review_latency_sec": float(review_latency_sec),
        "serialize_sync_teams": bool(serialize_sync_teams),
    }


def pure_predict_makespan(
    num_subteams: int,
    increments: int,
    work_sec: float,
    review_sec: float,
    serialize_sync: bool = True,
) -> Tuple[float, float]:
    """Calculate theoretical makespan for sync and async pipelines.

    Sync makespan:
    - Serialized teams: M * K * (work + review)
    - Parallel teams: K * (work + review)

    Async makespan (pipelined work + review with concurrent subteams):
    - max_m(K * work + review) = K * work + review
    """
    if serialize_sync:
        sync_ms = num_subteams * increments * (work_sec + review_sec)
    else:
        sync_ms = increments * (work_sec + review_sec)
    async_ms = (increments * work_sec) + review_sec
    return round(sync_ms, 6), round(async_ms, 6)


def pure_calculate_lag(commit_time: float, audit_start: float) -> float:
    """Calculate reviewer lag for a single commit."""
    return max(0.0, audit_start - commit_time)


def pure_aggregate_metrics(
    mode: str,
    commits: Sequence[Dict[str, Any]],
    audits: Sequence[Dict[str, Any]],
    duration_sec: float,
    conflict_count: int,
) -> Dict[str, Any]:
    """Aggregate raw commit and audit events into immutable summary metrics."""
    total_commits = len(commits)
    total_audits = len(audits)
    dur = max(duration_sec, 0.0001)
    throughput = total_commits / dur

    lags = [float(a["lag_sec"]) for a in audits if "lag_sec" in a]
    mean_lag = sum(lags) / len(lags) if lags else 0.0
    max_lag = max(lags) if lags else 0.0

    return {
        "mode": mode,
        "duration_sec": round(duration_sec, 4),
        "total_commits": total_commits,
        "total_audits": total_audits,
        "throughput_cps": round(throughput, 2),
        "mean_reviewer_lag_sec": round(mean_lag, 4),
        "max_reviewer_lag_sec": round(max_lag, 4),
        "conflict_count": conflict_count,
    }


def pure_compute_speedup(
    sync_metrics: Dict[str, Any], async_metrics: Dict[str, Any]
) -> float:
    """Compute speedup factor: sync_duration / async_duration."""
    async_dur = float(async_metrics.get("duration_sec", 0.0))
    sync_dur = float(sync_metrics.get("duration_sec", 0.0))
    if async_dur <= 0.0:
        return 0.0
    return round(sync_dur / async_dur, 2)


def pure_verify_audit_completeness(
    commits: Sequence[Dict[str, Any]], audits: Sequence[Dict[str, Any]]
) -> bool:
    """Verify that every committed SHA was audited exactly once."""
    commit_shas = {c["sha"] for c in commits}
    audit_shas = {a["sha"] for a in audits}
    return commit_shas == audit_shas and len(commits) == len(audits)


def pure_verify_subteam_ordering(
    events: Sequence[Dict[str, Any]]
) -> bool:
    """Verify per-subteam commit indices are strictly monotonically increasing.
    """
    by_subteam: Dict[str, List[int]] = {}
    for ev in events:
        by_subteam.setdefault(ev["subteam"], []).append(ev["idx"])
    for indices in by_subteam.values():
        if indices != sorted(indices):
            return False
        if len(indices) != len(set(indices)):
            return False
    return True


# ---------------------------------------------------------------------------
# Shell Boundary: Git Subprocess Operations
# ---------------------------------------------------------------------------


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
            f"git command failed: {' '.join(args)} in {cwd}\n"
            f"exit code: {res.returncode}\n"
            f"stderr: {res.stderr}\n"
            f"stdout: {res.stdout}"
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

    readme = repo / "README.md"
    readme.write_text("# Benchmark Git Repository\n", encoding="utf-8")
    git_run(repo, "add", "README.md")
    git_run(repo, "commit", "-m", "Initial commit on main")
    return repo


def check_conflicts(repo: Path, subteams: Sequence[str]) -> int:
    """Check for git merge conflicts across subteam branches."""
    conflicts = 0
    for st in subteams:
        branch = f"subteam/{st}/work"
        # Try a merge-tree check against main
        try:
            git_run(repo, "merge-tree", "main", branch)
        except subprocess.CalledProcessError:
            conflicts += 1
    return conflicts


# ---------------------------------------------------------------------------
# Synchronous Pipeline: Executioner Blocks on Review
# ---------------------------------------------------------------------------


def run_sync_subteam(
    repo: Path,
    subteam: str,
    increments: int,
    work_sec: float,
    review_sec: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute a synchronous sequential workflow for a single subteam."""
    branch = f"subteam/{subteam}/work"
    git_run(repo, "checkout", "-b", branch, "main")

    subteam_dir = repo / "skills" / f"subteam-{subteam}"
    subteam_dir.mkdir(parents=True, exist_ok=True)

    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []

    for i in range(increments):
        # 1. Executioner works
        if work_sec > 0:
            time.sleep(work_sec)
        target_file = subteam_dir / f"step_{i}.txt"
        target_file.write_text(
            f"subteam={subteam} increment={i} timestamp={time.time()}\n",
            encoding="utf-8",
        )
        git_run(repo, "add", str(target_file))
        git_run(repo, "commit", "-m", f"subteam {subteam} commit {i}")
        commit_sha = git_run(repo, "rev-parse", "HEAD")
        t_commit = time.time()

        commits.append({
            "subteam": subteam,
            "idx": i,
            "sha": commit_sha,
            "commit_time": t_commit,
        })

        # 2. Executioner BLOCKS while reviewer audits
        t_audit_start = time.time()
        if review_sec > 0:
            time.sleep(review_sec)
        # Real git inspection: verify commit diff
        git_run(repo, "show", "--stat", commit_sha)
        t_audit_end = time.time()

        audits.append({
            "subteam": subteam,
            "idx": i,
            "sha": commit_sha,
            "audit_start": t_audit_start,
            "audit_end": t_audit_end,
            "lag_sec": pure_calculate_lag(t_commit, t_audit_start),
        })

    return commits, audits


def run_sync_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run the synchronous benchmark pipeline."""
    with tempfile.TemporaryDirectory(prefix="bm_sync_") as tmp_str:
        tmp_path = Path(tmp_str)
        repo = init_repo(tmp_path)

        subteams = config["subteams"]
        increments = config["increments"]
        work_sec = config["work_latency_sec"]
        review_sec = config["review_latency_sec"]
        serialize = config.get("serialize_sync_teams", True)

        start_time = time.time()
        all_commits: List[Dict[str, Any]] = []
        all_audits: List[Dict[str, Any]] = []

        if serialize:
            for st in subteams:
                c, a = run_sync_subteam(
                    repo, st, increments, work_sec, review_sec
                )
                all_commits.extend(c)
                all_audits.extend(a)
        else:
            # Parallel subteams, but each subteam blocks internally
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(subteams)
            ) as pool:
                futures = []
                for st in subteams:
                    # Separate clone per subteam to simulate independent devs
                    clone_dir = tmp_path / f"clone_{st}"
                    git_run(tmp_path, "clone", str(repo), str(clone_dir))
                    git_run(
                        clone_dir, "config", "user.name", f"Dev-{st}"
                    )
                    git_run(
                        clone_dir,
                        "config",
                        "user.email",
                        f"dev-{st}@example.internal",
                    )
                    fut = pool.submit(
                        run_sync_subteam,
                        clone_dir,
                        st,
                        increments,
                        work_sec,
                        review_sec,
                    )
                    futures.append((st, clone_dir, fut))

                for st, clone_dir, fut in futures:
                    c, a = fut.result()
                    all_commits.extend(c)
                    all_audits.extend(a)
                    # Push branch back to central repo
                    git_run(
                        clone_dir, "push", "origin", f"subteam/{st}/work"
                    )

        duration = time.time() - start_time
        conflicts = check_conflicts(repo, subteams)

        metrics = pure_aggregate_metrics(
            mode="synchronous",
            commits=all_commits,
            audits=all_audits,
            duration_sec=duration,
            conflict_count=conflicts,
        )
        return {
            "metrics": metrics,
            "commits": all_commits,
            "audits": all_audits,
        }


# ---------------------------------------------------------------------------
# Asynchronous Pipeline: Continuous Execution + Concurrent Review Worktrees
# ---------------------------------------------------------------------------


def run_async_subteam(
    base_dir: Path,
    repo: Path,
    subteam: str,
    increments: int,
    work_sec: float,
    review_sec: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute an async subteam with concurrent exec and review worktrees."""
    work_branch = f"subteam/{subteam}/work"
    review_branch = f"subteam/{subteam}/review"

    # Executioner workspace (worktree 1)
    exec_tree = base_dir / f"worktree_{subteam}_exec"
    git_run(repo, "worktree", "add", "-b", work_branch, str(exec_tree), "main")

    # Reviewer workspace (worktree 2)
    review_tree = base_dir / f"worktree_{subteam}_rev"
    git_run(
        repo, "worktree", "add", "-b", review_branch, str(review_tree), "main"
    )

    handoff_q: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue()
    commits: List[Dict[str, Any]] = []
    audits: List[Dict[str, Any]] = []

    def executioner_worker() -> None:
        subteam_dir = exec_tree / "skills" / f"subteam-{subteam}"
        subteam_dir.mkdir(parents=True, exist_ok=True)

        for i in range(increments):
            if work_sec > 0:
                time.sleep(work_sec)
            target_file = subteam_dir / f"step_{i}.txt"
            target_file.write_text(
                f"async subteam={subteam} increment={i} time={time.time()}\n",
                encoding="utf-8",
            )
            git_run(exec_tree, "add", str(target_file))
            git_run(
                exec_tree,
                "commit",
                "-m",
                f"async subteam {subteam} commit {i}",
            )
            sha = git_run(exec_tree, "rev-parse", "HEAD")
            t_commit = time.time()

            ev = {
                "subteam": subteam,
                "idx": i,
                "sha": sha,
                "commit_time": t_commit,
            }
            commits.append(ev)
            # Continuous handoff: post to queue and immediately keep working!
            handoff_q.put(ev)

        handoff_q.put(None)  # Sentinel to stop reviewer

    def reviewer_worker() -> None:
        while True:
            item = handoff_q.get()
            if item is None:
                handoff_q.task_done()
                break

            t_audit_start = time.time()
            sha = item["sha"]

            # Reviewer audits SHA concurrently in review worktree
            # Fetch / check commit directly from the repository
            git_run(review_tree, "show", "--stat", sha)
            if review_sec > 0:
                time.sleep(review_sec)
            t_audit_end = time.time()

            audits.append({
                "subteam": subteam,
                "idx": item["idx"],
                "sha": sha,
                "audit_start": t_audit_start,
                "audit_end": t_audit_end,
                "lag_sec": pure_calculate_lag(
                    item["commit_time"], t_audit_start
                ),
            })
            handoff_q.task_done()

    # Run executioner and reviewer concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_rev = pool.submit(reviewer_worker)
        fut_exec = pool.submit(executioner_worker)
        fut_exec.result()
        fut_rev.result()

    return commits, audits


def run_async_pipeline(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run the asynchronous benchmark pipeline with concurrent subteams."""
    with tempfile.TemporaryDirectory(prefix="bm_async_") as tmp_str:
        tmp_path = Path(tmp_str)
        repo = init_repo(tmp_path)

        subteams = config["subteams"]
        increments = config["increments"]
        work_sec = config["work_latency_sec"]
        review_sec = config["review_latency_sec"]

        start_time = time.time()
        all_commits: List[Dict[str, Any]] = []
        all_audits: List[Dict[str, Any]] = []

        # All subteams run concurrently
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(subteams)
        ) as pool:
            futures = [
                pool.submit(
                    run_async_subteam,
                    tmp_path,
                    repo,
                    st,
                    increments,
                    work_sec,
                    review_sec,
                )
                for st in subteams
            ]
            for fut in futures:
                c, a = fut.result()
                all_commits.extend(c)
                all_audits.extend(a)

        duration = time.time() - start_time
        conflicts = check_conflicts(repo, subteams)

        metrics = pure_aggregate_metrics(
            mode="asynchronous",
            commits=all_commits,
            audits=all_audits,
            duration_sec=duration,
            conflict_count=conflicts,
        )
        return {
            "metrics": metrics,
            "commits": all_commits,
            "audits": all_audits,
        }


# ---------------------------------------------------------------------------
# Formatting & Presentation
# ---------------------------------------------------------------------------


def format_summary_table(
    sync_metrics: Dict[str, Any],
    async_metrics: Dict[str, Any],
    speedup: float,
) -> str:
    """Format benchmark results as an ASCII comparison table."""
    lines = [
        "=" * 76,
        "  ASYNC SWARM vs SYNC BENCHMARK RESULTS",
        "=" * 76,
        f"{'Metric':<32} | {'Sync Pipeline':<18} | {'Async Pipeline':<18}",
        "-" * 76,
        f"{'Wall-Clock Duration (s)':<32} | "
        f"{sync_metrics['duration_sec']:<18.4f} | "
        f"{async_metrics['duration_sec']:<18.4f}",
        f"{'Total Commits':<32} | "
        f"{sync_metrics['total_commits']:<18} | "
        f"{async_metrics['total_commits']:<18}",
        f"{'Total Audited Commits':<32} | "
        f"{sync_metrics['total_audits']:<18} | "
        f"{async_metrics['total_audits']:<18}",
        f"{'Throughput (commits/sec)':<32} | "
        f"{sync_metrics['throughput_cps']:<18.2f} | "
        f"{async_metrics['throughput_cps']:<18.2f}",
        f"{'Mean Reviewer Lag (s)':<32} | "
        f"{sync_metrics['mean_reviewer_lag_sec']:<18.4f} | "
        f"{async_metrics['mean_reviewer_lag_sec']:<18.4f}",
        f"{'Max Reviewer Lag (s)':<32} | "
        f"{sync_metrics['max_reviewer_lag_sec']:<18.4f} | "
        f"{async_metrics['max_reviewer_lag_sec']:<18.4f}",
        f"{'Git Conflicts':<32} | "
        f"{sync_metrics['conflict_count']:<18} | "
        f"{async_metrics['conflict_count']:<18}",
        "-" * 76,
        f"{'SPEEDUP FACTOR (Sync / Async)':<32} | {speedup:<18.2f}x | "
        f"{'FASTER':<18}",
        "=" * 76,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark Async Swarm Teamwork vs Sync Pipelines."
    )
    parser.add_argument(
        "--subteams",
        nargs="+",
        default=["fc", "sw", "bm"],
        help="Subteam identifiers (default: fc sw bm)",
    )
    parser.add_argument(
        "--increments",
        type=int,
        default=4,
        help="Increments per subteam (default: 4)",
    )
    parser.add_argument(
        "--work-latency",
        type=float,
        default=0.05,
        help="Work stage latency in seconds (default: 0.05)",
    )
    parser.add_argument(
        "--review-latency",
        type=float,
        default=0.05,
        help="Review stage latency in seconds (default: 0.05)",
    )
    parser.add_argument(
        "--parallel-sync-teams",
        action="store_true",
        help="Run subteams in parallel in sync mode (still blocking within)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    config = pure_make_config(
        subteams=args.subteams,
        increments=args.increments,
        work_latency_sec=args.work_latency,
        review_latency_sec=args.review_latency,
        serialize_sync_teams=not args.parallel_sync_teams,
    )

    sync_result = run_sync_pipeline(config)
    async_result = run_async_pipeline(config)

    speedup = pure_compute_speedup(
        sync_result["metrics"], async_result["metrics"]
    )

    if args.json:
        out = {
            "config": config,
            "sync": sync_result["metrics"],
            "async": async_result["metrics"],
            "speedup": speedup,
        }
        print(json.dumps(out, indent=2))
    else:
        table = format_summary_table(
            sync_result["metrics"], async_result["metrics"], speedup
        )
        print(table)


if __name__ == "__main__":
    main()
