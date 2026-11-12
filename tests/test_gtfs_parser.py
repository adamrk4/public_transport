"""Tests for GTFS parser."""

import csv
import io
import zipfile
from pathlib import Path

import pytest

from src.gtfs_parser import read_gtfs_zip, validate_gtfs, summary, filter_tel_aviv_routes


@pytest.fixture
def sample_gtfs(tmp_path):
    """Create a minimal valid GTFS zip for testing."""
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("agency.txt", "agency_id,agency_name,agency_url,agency_timezone\n1,TestAgency,http://test.com,Asia/Jerusalem\n")
        zf.writestr("routes.txt", "route_id,agency_id,route_short_name,route_long_name,route_type\nR1,1,10,Test Route,3\n")
        zf.writestr("trips.txt", "route_id,service_id,trip_id,direction_id\nR1,S1,T1,0\nR1,S1,T2,1\n")
        zf.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\nST1,Dizengoff,32.08,34.77\nST2,Rothschild,32.07,34.78\nST3,Haifa Stop,32.80,34.99\n")
        zf.writestr("stop_times.txt", "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,ST1,1\nT1,08:10:00,08:10:00,ST2,2\nT2,09:00:00,09:00:00,ST3,1\n")
        zf.writestr("calendar.txt", "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nS1,1,1,1,1,1,0,0,20260101,20261231\n")
    return zip_path


def test_read_gtfs_zip(sample_gtfs):
    data = read_gtfs_zip(sample_gtfs)
    assert set(data.keys()) == {"agency", "routes", "trips", "stops", "stop_times", "calendar"}
    assert len(data["agency"]) == 1
    assert len(data["routes"]) == 1
    assert len(data["trips"]) == 2
    assert len(data["stops"]) == 3
    assert len(data["stop_times"]) == 3
    assert len(data["calendar"]) == 1


def test_missing_file(tmp_path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("agency.txt", "agency_id\n1\n")
    with pytest.raises(ValueError, match="Missing required GTFS files"):
        read_gtfs_zip(zip_path)


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_gtfs_zip("/nonexistent/file.zip")


def test_validate_clean(sample_gtfs):
    data = read_gtfs_zip(sample_gtfs)
    warnings = validate_gtfs(data)
    assert warnings == []


def test_validate_missing_route(sample_gtfs):
    data = read_gtfs_zip(sample_gtfs)
    data["trips"].append({"trip_id": "T99", "route_id": "MISSING", "service_id": "S1", "direction_id": "0"})
    warnings = validate_gtfs(data)
    assert any("unknown route" in w for w in warnings)


def test_summary(sample_gtfs):
    data = read_gtfs_zip(sample_gtfs)
    s = summary(data)
    assert s == {"agency": 1, "routes": 1, "trips": 2, "stops": 3, "stop_times": 3, "calendar": 1}


def test_filter_tel_aviv(sample_gtfs):
    data = read_gtfs_zip(sample_gtfs)
    ta = filter_tel_aviv_routes(data)
    assert len(ta["stops"]) == 2  # ST1 and ST2 are in TA bbox
    assert len(ta["routes"]) == 1
    # T2 only goes to Haifa, so should be excluded
    assert all(t["trip_id"] != "T2" for t in ta["trips"])
