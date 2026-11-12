"""Tests for report generation."""

from pathlib import Path

from src.report import generate_markdown_report, generate_csv_report, save_csv


SAMPLE_DATA = {
    "agency": [{"agency_id": "1"}],
    "routes": [{"route_id": "R1", "route_short_name": "5", "route_type": "3"}],
    "trips": [
        {"trip_id": "T1", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
        {"trip_id": "T2", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
        {"trip_id": "T3", "route_id": "R1", "service_id": "S1", "direction_id": "0"},
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
        {"trip_id": "T3", "stop_id": "ST1", "arrival_time": "09:00:00", "stop_sequence": "1"},
        {"trip_id": "T3", "stop_id": "ST2", "arrival_time": "09:10:00", "stop_sequence": "2"},
    ],
    "calendar": [{"service_id": "S1"}],
}


def test_markdown_report_contains_sections():
    md = generate_markdown_report(SAMPLE_DATA, "5", "0")
    assert "דוח ביצועי קו 5" in md
    assert "סיכום קו" in md
    assert "Headway לפי תחנה" in md
    assert "Bunching לפי תחנה" in md
    assert "מתודולוגיה" in md
    assert "מגבלות" in md


def test_markdown_report_no_data():
    md = generate_markdown_report(SAMPLE_DATA, "999", "0")
    assert "אין נתונים" in md


def test_markdown_report_time_window():
    md = generate_markdown_report(SAMPLE_DATA, "5", "0", time_window=(8, 9))
    assert "08:00–09:00" in md
    assert "ST1" in md


def test_markdown_report_time_window_empty():
    md = generate_markdown_report(SAMPLE_DATA, "5", "0", time_window=(12, 13))
    assert "אין נתונים" in md


def test_csv_report():
    rows = generate_csv_report(SAMPLE_DATA, "5", "0")
    assert len(rows) == 2
    assert rows[0]["route"] == "5"
    assert "avg_headway_min" in rows[0]
    assert "bunching_ratio" in rows[0]


def test_save_csv(tmp_path):
    rows = generate_csv_report(SAMPLE_DATA, "5", "0")
    path = save_csv(rows, tmp_path / "out.csv")
    assert path.exists()
    content = path.read_text(encoding="utf-8-sig")
    assert "stop_id" in content
    assert "ST1" in content


def test_save_csv_empty(tmp_path):
    path = save_csv([], tmp_path / "empty.csv")
    assert path.exists()
    assert path.read_text() == ""
