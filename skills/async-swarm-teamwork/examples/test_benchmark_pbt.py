"""Hypothesis Property-Based Tests for Async vs Sync Swarm Benchmark.

Verifies fundamental invariants of the benchmark and git pipeline:
1. Schedule makespan: Async pipeline is faster or equal to sync pipeline.
2. Zero git merge conflicts across disjoint subteam worktrees/branches.
3. Audit completeness: Every committed SHA is audited exactly once.
4. Monotonic subteam ordering: Commits within each subteam maintain order.
5. Metric math invariants: Throughput, lag bounds, and speedup ratios.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

from hypothesis import HealthCheck, given, settings, strategies as st
import pytest

# Ensure scripts directory is importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from benchmark_async_vs_sync import (  # noqa: E402
    pure_aggregate_metrics,
    pure_calculate_lag,
    pure_compute_speedup,
    pure_make_config,
    pure_predict_makespan,
    pure_verify_audit_completeness,
    pure_verify_subteam_ordering,
    run_async_pipeline,
    run_sync_pipeline,
)


# ---------------------------------------------------------------------------
# Pure Calculation Property Tests
# ---------------------------------------------------------------------------


@given(
    commit_time=st.floats(min_value=0.0, max_value=1e8),
    audit_start=st.floats(min_value=0.0, max_value=1e8),
)
def test_prop_lag_always_non_negative(
    commit_time: float, audit_start: float
) -> None:
    """Reviewer lag must never be negative regardless of clock timestamps."""
    lag = pure_calculate_lag(commit_time, audit_start)
    assert lag >= 0.0
    if audit_start >= commit_time:
        assert abs(lag - (audit_start - commit_time)) < 1e-6
    else:
        assert lag == 0.0


@given(
    sync_dur=st.floats(min_value=0.01, max_value=1e4),
    async_dur=st.floats(min_value=0.01, max_value=1e4),
)
def test_prop_speedup_calculation(
    sync_dur: float, async_dur: float
) -> None:
    """Speedup calculation preserves ratio invariants."""
    sync_m = {"duration_sec": sync_dur}
    async_m = {"duration_sec": async_dur}
    speedup = pure_compute_speedup(sync_m, async_m)
    expected = round(sync_dur / async_dur, 2)
    assert speedup == expected
    assert speedup >= 0.0


@given(
    subteams=st.lists(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=4
        ),
        min_size=1,
        max_size=4,
        unique=True,
    ),
    increments=st.integers(min_value=1, max_value=10),
)
def test_prop_subteam_ordering_strictly_monotonic(
    subteams: List[str], increments: int
) -> None:
    """Sequential events per subteam must pass ordering verification."""
    events: List[Dict[str, Any]] = []
    for st_name in subteams:
        for idx in range(increments):
            events.append({"subteam": st_name, "idx": idx})
    assert pure_verify_subteam_ordering(events) is True

    # Perturbing order should violate monotonicity if increments > 1
    if increments > 1:
        bad_events = list(events)
        # Swap first two elements of first subteam
        bad_events[0], bad_events[1] = bad_events[1], bad_events[0]
        assert pure_verify_subteam_ordering(bad_events) is False


@given(
    shas=st.lists(
        st.text(alphabet="0123456789abcdef", min_size=8, max_size=8),
        min_size=1,
        max_size=10,
        unique=True,
    )
)
def test_prop_audit_completeness_invariant(shas: List[str]) -> None:
    """Audits match commits if and only if SHAs and counts match 1:1."""
    commits = [{"sha": s} for s in shas]
    audits = [{"sha": s} for s in shas]
    assert pure_verify_audit_completeness(commits, audits) is True

    # Dropping one audit must fail completeness
    if len(shas) > 1:
        assert pure_verify_audit_completeness(commits, audits[:-1]) is False


@given(
    num_subteams=st.integers(min_value=1, max_value=10),
    increments=st.integers(min_value=1, max_value=20),
    work_sec=st.floats(min_value=0.001, max_value=100.0),
    review_sec=st.floats(min_value=0.001, max_value=100.0),
    serialize_sync=st.booleans(),
)
def test_prop_theoretical_makespan_inequality(
    num_subteams: int,
    increments: int,
    work_sec: float,
    review_sec: float,
    serialize_sync: bool,
) -> None:
    """Theoretical async makespan is always <= sync makespan."""
    sync_ms, async_ms = pure_predict_makespan(
        num_subteams=num_subteams,
        increments=increments,
        work_sec=work_sec,
        review_sec=review_sec,
        serialize_sync=serialize_sync,
    )
    assert async_ms <= sync_ms + 1e-9
    assert async_ms > 0.0
    assert sync_ms > 0.0


# ---------------------------------------------------------------------------
# Real Git-Backed Pipeline Property Tests
# ---------------------------------------------------------------------------


@settings(
    max_examples=3,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    num_subteams=st.integers(min_value=2, max_value=3),
    increments=st.integers(min_value=2, max_value=3),
)
def test_prop_real_git_pipeline_schedule_and_invariants(
    num_subteams: int, increments: int
) -> None:
    """Property test running real git worktrees and verifying all invariants.

    Invariants checked across real git operations:
    1. Zero merge conflicts across disjoint branches.
    2. Audit completeness: 100% of commits audited.
    3. Monotonic commit progression per subteam.
    4. Async makespan < Sync makespan (speedup >= 1.0).
    5. Throughput async > Throughput sync.
    """
    subteams = [f"st{i}" for i in range(num_subteams)]
    cfg = pure_make_config(
        subteams=subteams,
        increments=increments,
        work_latency_sec=0.02,
        review_latency_sec=0.02,
        serialize_sync_teams=True,
    )

    sync_res = run_sync_pipeline(cfg)
    async_res = run_async_pipeline(cfg)

    sync_m = sync_res["metrics"]
    async_m = async_res["metrics"]

    # 1. Zero git conflicts
    assert sync_m["conflict_count"] == 0
    assert async_m["conflict_count"] == 0

    # 2. Audit completeness
    assert pure_verify_audit_completeness(
        sync_res["commits"], sync_res["audits"]
    )
    assert pure_verify_audit_completeness(
        async_res["commits"], async_res["audits"]
    )

    # 3. Monotonic subteam ordering
    assert pure_verify_subteam_ordering(sync_res["commits"])
    assert pure_verify_subteam_ordering(async_res["commits"])

    # 4. Total commit counts match expected: subteams * increments
    expected_commits = num_subteams * increments
    assert sync_m["total_commits"] == expected_commits
    assert async_m["total_commits"] == expected_commits

    # 5. Speedup >= 1.0 (async duration < sync duration)
    speedup = pure_compute_speedup(sync_m, async_m)
    assert speedup >= 1.2
    assert async_m["throughput_cps"] > sync_m["throughput_cps"]
