"""Tests for RT recorder."""

import json
from unittest.mock import patch

import pytest

from src.rt_recorder import (
    filter_tel_aviv,
    save_snapshot,
    record_once,
    TEL_AVIV_BBOX,
)


SAMPLE_LOCATIONS = [
    {"id": 1, "lat": 32.08, "lon": 34.78, "velocity": 30, "bearing": 90},
    {"id": 2, "lat": 32.07, "lon": 34.77, "velocity": 0, "bearing": 180},
    {"id": 3, "lat": 32.80, "lon": 34.99, "velocity": 50, "bearing": 0},  # Haifa
    {"id": 4, "lat": None, "lon": None, "velocity": 0, "bearing": 0},  # no coords
]


def test_filter_tel_aviv():
    result = filter_tel_aviv(SAMPLE_LOCATIONS)
    assert len(result) == 2
    assert all(r["id"] in (1, 2) for r in result)


def test_filter_empty():
    assert filter_tel_aviv([]) == []


def test_save_snapshot(tmp_path):
    locs = SAMPLE_LOCATIONS[:2]
    path = save_snapshot(locs, tmp_path / "snapshots")
    assert path is not None
    assert path.exists()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == 1


def test_save_snapshot_empty(tmp_path):
    path = save_snapshot([], tmp_path / "snapshots")
    assert path is None


@patch("src.rt_recorder.fetch_vehicle_locations")
def test_record_once_success(mock_fetch, tmp_path):
    mock_fetch.return_value = SAMPLE_LOCATIONS
    stats = record_once(tmp_path / "out", limit=100)
    assert stats["fetched"] == 4
    assert stats["tel_aviv"] == 2
    assert stats["error"] is None
    assert stats["saved_to"] is not None


@patch("src.rt_recorder.fetch_vehicle_locations")
def test_record_once_api_error(mock_fetch, tmp_path):
    mock_fetch.side_effect = ConnectionError("timeout")
    stats = record_once(tmp_path / "out", limit=100)
    assert stats["fetched"] == 0
    assert stats["error"] is not None
