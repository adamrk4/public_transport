"""Tests for headway analyzer."""

from src.headway_analyzer import (
    time_to_minutes,
    compute_headways,
    stop_summary,
    format_summary_table,
)


SAMPLE_DATA = {
    "agency": [{"agency_id": "1"}],
    "routes": [
        {"route_id": "R1", "route_short_name": "5", "route_type": "3"},
        {"route_id": "R2", "route_short_name": "10", "route_type": "3"},
    ],
    "trips": [
        {"trip_id": "T1", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
        {"trip_id": "T2", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
        {"trip_id": "T3", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
        {"trip_id": "T4", "route_id": "R1", "service_id": "S1", "direction_id": "1"},
    ],
    "stops": [
        {"stop_id": "ST1", "stop_name": "Stop A"},
        {"stop_id": "ST2", "stop_name": "Stop B"},
    ],
    "stop_times": [
        {"trip_id": "T1", "stop_id": "ST1", "arrival_time": "08:00:00", "stop_sequence": "1"},
        {"trip_id": "T1", "stop_id": "ST2", "arrival_time": "08:10:00", "stop_sequence": "2"},
        {"trip_id": "T2", "stop_id": "ST1", "arrival_time": "08:15:00", "stop_sequence": "1"},
        {"trip_id": "T2", "stop_id": "ST2", "arrival_time": "08:25:00", "stop_sequence": "2"},
        {"trip_id": "T3", "stop_id": "ST1", "arrival_time": "08:45:00", "stop_sequence": "1"},
        {"trip_id": "T3", "stop_id": "ST2", "arrival_time": "08:55:00", "stop_sequence": "2"},
        {"trip_id": "T4", "stop_id": "ST1", "arrival_time": "09:00:00", "stop_sequence": "1"},
    ],
    "calendar": [{"service_id": "S1"}],
}


def test_time_to_minutes():
    assert time_to_minutes("08:00:00") == 480.0
    assert time_to_minutes("25:30:00") == 1530.0
    assert time_to_minutes("00:00:30") == 0.5


def test_compute_headways_basic():
    records = compute_headways(SAMPLE_DATA, route_short_name="5", direction_id="0")
    # ST1: T1@8:00, T2@8:15, T3@8:45 → 2 headways (15min, 30min)
    # ST2: T1@8:10, T2@8:25, T3@8:55 → 2 headways (15min, 30min)
    assert len(records) == 4
    st1_records = [r for r in records if r.stop_id == "ST1"]
    assert len(st1_records) == 2
    assert st1_records[0].headway_minutes == 15.0
    assert st1_records[1].headway_minutes == 30.0


def test_compute_headways_wrong_direction():
    records = compute_headways(SAMPLE_DATA, route_short_name="5", direction_id="1")
    # Only T4 in direction 1, so only 1 arrival per stop → 0 headways
    assert len(records) == 0


def test_compute_headways_unknown_route():
    records = compute_headways(SAMPLE_DATA, route_short_name="999")
    assert records == []


def test_compute_headways_service_filter():
    records = compute_headways(
        SAMPLE_DATA, route_short_name="5", direction_id="0", service_ids={"S1"}
    )
    assert len(records) == 4

    records = compute_headways(
        SAMPLE_DATA, route_short_name="5", direction_id="0", service_ids={"S2"}
    )
    assert records == []


def test_stop_summary():
    records = compute_headways(SAMPLE_DATA, route_short_name="5", direction_id="0")
    s = stop_summary(records)
    assert len(s) == 2
    st1 = next(row for row in s if row["stop_id"] == "ST1")
    assert st1["count"] == 2
    assert st1["avg_headway_min"] == 22.5
    assert st1["min_headway_min"] == 15.0
    assert st1["max_headway_min"] == 30.0


def test_format_summary_table():
    records = compute_headways(SAMPLE_DATA, route_short_name="5", direction_id="0")
    s = stop_summary(records)
    table = format_summary_table(s)
    assert "stop_id" in table
    assert "ST1" in table
    assert "Stop A" in table
