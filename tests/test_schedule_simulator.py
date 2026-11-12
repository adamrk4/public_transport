"""Tests for the schedule simulator."""

import pytest
from src.schedule_simulator import (
    ScheduleModification,
    apply_modification,
    run_simulation,
    format_simulation_report,
    _minutes_to_time,
)
from src.headway_analyzer import time_to_minutes


def _make_data(trip_times=None):
    """Create minimal GTFS-like data dict for testing.

    trip_times: list of (trip_id, [(stop_id, arrival_time)]) tuples.
    Defaults to 4 trips on route "10" direction "0" with 3 stops each.
    """
    if trip_times is None:
        trip_times = [
            ("t1", [("s1", "07:00:00"), ("s2", "07:05:00"), ("s3", "07:10:00")]),
            ("t2", [("s1", "07:15:00"), ("s2", "07:20:00"), ("s3", "07:25:00")]),
            ("t3", [("s1", "07:30:00"), ("s2", "07:35:00"), ("s3", "07:40:00")]),
            ("t4", [("s1", "07:45:00"), ("s2", "07:50:00"), ("s3", "07:55:00")]),
        ]

    routes = [{"route_id": "r10", "route_short_name": "10"}]
    trips = [
        {"trip_id": tid, "route_id": "r10", "direction_id": "0", "service_id": "wd"}
        for tid, _ in trip_times
    ]
    stops = [
        {"stop_id": "s1", "stop_name": "First"},
        {"stop_id": "s2", "stop_name": "Second"},
        {"stop_id": "s3", "stop_name": "Third"},
    ]
    stop_times = []
    for tid, st_list in trip_times:
        for seq, (sid, arr) in enumerate(st_list):
            stop_times.append({
                "trip_id": tid,
                "stop_id": sid,
                "arrival_time": arr,
                "departure_time": arr,
                "stop_sequence": str(seq),
            })

    return {
        "routes": routes,
        "trips": trips,
        "stops": stops,
        "stop_times": stop_times,
        "calendar": [{"service_id": "wd"}],
    }


def test_minutes_to_time_roundtrip():
    for t in ("07:00:00", "12:30:00", "25:05:00"):
        assert _minutes_to_time(time_to_minutes(t)) == t


def test_remove_trips():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="remove_trips",
        route_short_name="10",
        fraction=0.5,
    )
    result = apply_modification(data, mod)
    remaining_trips = {t["trip_id"] for t in result["trips"]}
    assert len(remaining_trips) < 4
    assert len(remaining_trips) >= 2

    for st in result["stop_times"]:
        assert st["trip_id"] in remaining_trips


def test_shift_times():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="shift_times",
        route_short_name="10",
        shift_minutes=10,
    )
    result = apply_modification(data, mod)

    original_first = time_to_minutes("07:00:00")
    shifted = None
    for st in result["stop_times"]:
        if st["trip_id"] == "t1" and st["stop_id"] == "s1":
            shifted = time_to_minutes(st["arrival_time"])
            break

    assert shifted is not None
    assert abs(shifted - (original_first + 10)) < 0.01


def test_add_trips():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="add_trips",
        route_short_name="10",
        count=3,
        time_window=(7, 8),
    )
    result = apply_modification(data, mod)
    trip_ids = {t["trip_id"] for t in result["trips"]}
    assert len(trip_ids) == 4 + 3

    sim_trips = [tid for tid in trip_ids if tid.startswith("sim_")]
    assert len(sim_trips) == 3


def test_set_headway():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="set_headway",
        route_short_name="10",
        headway_minutes=10,
        time_window=(7, 8),
    )
    result = apply_modification(data, mod)
    sim_trips = [t for t in result["trips"] if t["trip_id"].startswith("sim_hw_")]
    assert len(sim_trips) == 6  # 60 min / 10 min = 6 trips


def test_run_simulation():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="add_trips",
        route_short_name="10",
        count=4,
        time_window=(7, 8),
    )
    result = run_simulation(
        data,
        modifications=[mod],
        route_short_name="10",
        label="add 4 trips",
    )
    assert result.label == "add 4 trips"
    assert result.before
    assert result.after
    assert result.delta


def test_format_report():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="add_trips",
        route_short_name="10",
        count=2,
        time_window=(7, 8),
    )
    result = run_simulation(data, [mod], "10", label="test")
    report = format_simulation_report(result)
    assert "סימולציה" in report
    assert "לפני" in report
    assert "אחרי" in report


def test_unknown_mod_type():
    data = _make_data()
    mod = ScheduleModification(mod_type="unknown", route_short_name="10")
    with pytest.raises(ValueError, match="Unknown mod_type"):
        apply_modification(data, mod)


def test_no_matching_route():
    data = _make_data()
    mod = ScheduleModification(
        mod_type="remove_trips",
        route_short_name="999",
        fraction=0.5,
    )
    result = apply_modification(data, mod)
    assert len(result["trips"]) == 4
