"""Tests for bunching metrics."""

from src.headway_analyzer import HeadwayRecord
from src.bunching import (
    compute_bunching,
    route_bunching_summary,
    format_bunching_table,
    DEFAULT_BUNCHING_THRESHOLD_MINUTES,
)


def _make_records() -> list[HeadwayRecord]:
    """Headways: ST1 has [1, 5, 10, 2], ST2 has [3, 8]."""
    return [
        HeadwayRecord("ST1", "Stop A", "T2", "T1", "08:01:00", "08:00:00", 1.0, None),
        HeadwayRecord("ST1", "Stop A", "T3", "T2", "08:06:00", "08:01:00", 5.0, None),
        HeadwayRecord("ST1", "Stop A", "T4", "T3", "08:16:00", "08:06:00", 10.0, None),
        HeadwayRecord("ST1", "Stop A", "T5", "T4", "08:18:00", "08:16:00", 2.0, None),
        HeadwayRecord("ST2", "Stop B", "T2", "T1", "08:03:00", "08:00:00", 3.0, None),
        HeadwayRecord("ST2", "Stop B", "T3", "T2", "08:11:00", "08:03:00", 8.0, None),
    ]


def test_compute_bunching_default_threshold():
    results = compute_bunching(_make_records())
    assert len(results) == 2
    st1 = next(r for r in results if r.stop_id == "ST1")
    # headways [1, 5, 10, 2], threshold 2.0 → bunched = [1, 2] → ratio 2/4
    assert st1.bunched_arrivals == 2
    assert st1.total_arrivals == 4
    assert st1.bunching_ratio == 0.5

    st2 = next(r for r in results if r.stop_id == "ST2")
    # headways [3, 8], threshold 2.0 → bunched = [] → ratio 0/2
    assert st2.bunched_arrivals == 0
    assert st2.bunching_ratio == 0.0


def test_compute_bunching_custom_threshold():
    results = compute_bunching(_make_records(), threshold_minutes=5.0)
    st1 = next(r for r in results if r.stop_id == "ST1")
    # headways [1, 5, 10, 2], threshold 5.0 → bunched = [1, 5, 2] → ratio 3/4
    assert st1.bunched_arrivals == 3

    st2 = next(r for r in results if r.stop_id == "ST2")
    # headways [3, 8], threshold 5.0 → bunched = [3] → ratio 1/2
    assert st2.bunched_arrivals == 1


def test_compute_bunching_empty():
    assert compute_bunching([]) == []


def test_route_bunching_summary():
    results = compute_bunching(_make_records())
    summary = route_bunching_summary(results)
    assert summary["stops_analyzed"] == 2
    assert summary["total_arrivals"] == 6
    assert summary["bunched_arrivals"] == 2
    assert summary["worst_stop_id"] == "ST1"
    assert summary["threshold_minutes"] == DEFAULT_BUNCHING_THRESHOLD_MINUTES


def test_route_bunching_summary_empty():
    assert route_bunching_summary([]) == {}


def test_format_bunching_table():
    results = compute_bunching(_make_records())
    table = format_bunching_table(results)
    assert "ST1" in table
    assert "Stop A" in table
    assert "50.0%" in table
