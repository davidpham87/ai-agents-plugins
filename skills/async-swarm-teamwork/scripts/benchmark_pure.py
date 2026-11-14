"""Pure calculation and formatting helpers for Async vs Sync Benchmark.

Follows Rich Hickey's functional design principles:
- Plain immutable dictionaries and tuples.
- Zero side effects or I/O.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from cytoolz import groupby, pipe
from cytoolz.curried import filter as cfilter
from cytoolz.curried import map as cmap
from cytoolz.curried import valmap as cvalmap


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
    """Calculate theoretical makespan for sync and async pipelines."""
    step = work_sec + review_sec
    mult = num_subteams * increments if serialize_sync else increments
    sync_ms = mult * step
    async_ms = (increments * work_sec) + review_sec
    return round(sync_ms, 6), round(async_ms, 6)


def pure_calculate_lag(commit_time: float, audit_start: float) -> float:
    """Calculate reviewer lag for a single commit."""
    return max(0.0, audit_start - commit_time)


def pure_lag_stats(audits: Sequence[Dict[str, Any]]) -> Tuple[float, float]:
    """Compute mean and max reviewer lag from audit events."""
    lags = pipe(
        audits,
        cfilter(lambda a: "lag_sec" in a),
        cmap(lambda a: float(a["lag_sec"])),
        list,
    )
    mean_lag = sum(lags) / len(lags) if lags else 0.0
    max_lag = max(lags) if lags else 0.0
    return round(mean_lag, 4), round(max_lag, 4)


def pure_aggregate_metrics(
    mode: str,
    commits: Sequence[Dict[str, Any]],
    audits: Sequence[Dict[str, Any]],
    duration_sec: float,
    conflict_count: int,
) -> Dict[str, Any]:
    """Aggregate raw commit and audit events into summary metrics."""
    total = len(commits)
    mean_lag, max_lag = pure_lag_stats(audits)
    return {
        "mode": mode,
        "duration_sec": round(duration_sec, 4),
        "total_commits": total,
        "total_audits": len(audits),
        "throughput_cps": round(total / max(duration_sec, 0.0001), 2),
        "mean_reviewer_lag_sec": mean_lag,
        "max_reviewer_lag_sec": max_lag,
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
    commit_shas = pipe(commits, cmap(lambda c: c["sha"]), set)
    audit_shas = pipe(audits, cmap(lambda a: a["sha"]), set)
    return commit_shas == audit_shas and len(commits) == len(audits)


def _strictly_monotonic(indices: Sequence[int]) -> bool:
    """Return True when indices are sorted and unique."""
    vals = list(indices)
    return vals == sorted(vals) and len(vals) == len(set(vals))


def pure_verify_subteam_ordering(events: Sequence[Dict[str, Any]]) -> bool:
    """Verify per-subteam commit indices are strictly monotonic."""
    return pipe(
        events,
        lambda evs: groupby("subteam", evs),
        cvalmap(lambda grp: pipe(grp, cmap(lambda e: e["idx"]), list)),
        lambda m: all(cmap(_strictly_monotonic, m.values())),
    )


def _table_row(label: str, sync_val: str, async_val: str) -> str:
    """Format a single 3-column table row."""
    return f"{label:<32} | {sync_val:<18} | {async_val:<18}"


def _table_metric_rows(
    sync_m: Dict[str, Any], async_m: Dict[str, Any]
) -> List[str]:
    """Build metric rows for summary comparison table."""
    specs = [
        ("Wall-Clock Duration (s)", "duration_sec", ".4f"),
        ("Total Commits", "total_commits", "d"),
        ("Total Audited Commits", "total_audits", "d"),
        ("Throughput (commits/sec)", "throughput_cps", ".2f"),
        ("Mean Reviewer Lag (s)", "mean_reviewer_lag_sec", ".4f"),
        ("Max Reviewer Lag (s)", "max_reviewer_lag_sec", ".4f"),
        ("Git Conflicts", "conflict_count", "d"),
    ]
    return pipe(
        specs,
        cmap(lambda s: _table_row(s[0], f"{sync_m[s[1]]:{s[2]}}",
                                  f"{async_m[s[1]]:{s[2]}}")),
        list,
    )


def format_summary_table(
    sync_metrics: Dict[str, Any],
    async_metrics: Dict[str, Any],
    speedup: float,
) -> str:
    """Format benchmark results as an ASCII comparison table."""
    sep = "-" * 76
    hdr = _table_row("Metric", "Sync Pipeline", "Async Pipeline")
    foot = _table_row("SPEEDUP (Sync / Async)", f"{speedup:.2f}x", "FASTER")
    rows = _table_metric_rows(sync_metrics, async_metrics)
    lines = [
        "=" * 76, "  ASYNC SWARM vs SYNC BENCHMARK RESULTS", "=" * 76,
        hdr, sep, *rows, sep, foot, "=" * 76,
    ]
    return "\n".join(lines)
