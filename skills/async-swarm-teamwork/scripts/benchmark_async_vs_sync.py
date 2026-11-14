#!/usr/bin/env python3
"""Benchmark comparing Asynchronous Swarm Teamwork vs Synchronous Blocking.

Thin CLI entrypoint and public API facade re-exporting pure helpers
(`benchmark_pure`) and git-backed pipeline runners (`benchmark_git`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_git import (  # noqa: E402, F401
    check_conflicts,
    git_run,
    init_repo,
    run_async_pipeline,
    run_async_subteam,
    run_sync_pipeline,
    run_sync_subteam,
)
from benchmark_pure import (  # noqa: E402, F401
    format_summary_table,
    pure_aggregate_metrics,
    pure_calculate_lag,
    pure_compute_speedup,
    pure_make_config,
    pure_predict_makespan,
    pure_verify_audit_completeness,
    pure_verify_subteam_ordering,
)


def parse_args() -> argparse.Namespace:
    """Parse benchmark CLI arguments."""
    p = argparse.ArgumentParser(description="Benchmark Async vs Sync Swarm.")
    p.add_argument("--subteams", nargs="+", default=["fc", "sw", "bm"])
    p.add_argument("--increments", type=int, default=4)
    p.add_argument("--work-latency", type=float, default=0.05)
    p.add_argument("--review-latency", type=float, default=0.05)
    p.add_argument("--parallel-sync-teams", action="store_true")
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def main() -> None:
    """Execute sync and async benchmarks and print summary output."""
    args = parse_args()
    config = pure_make_config(
        subteams=args.subteams,
        increments=args.increments,
        work_latency_sec=args.work_latency,
        review_latency_sec=args.review_latency,
        serialize_sync_teams=not args.parallel_sync_teams,
    )
    sync_m = run_sync_pipeline(config)["metrics"]
    async_m = run_async_pipeline(config)["metrics"]
    speedup = pure_compute_speedup(sync_m, async_m)
    if args.json:
        out = {"config": config, "sync": sync_m, "async": async_m}
        out["speedup"] = speedup
        print(json.dumps(out, indent=2))
        return
    print(format_summary_table(sync_m, async_m, speedup))


if __name__ == "__main__":
    main()
