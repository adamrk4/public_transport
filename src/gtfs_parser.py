"""Parse GTFS static feed from a zip file."""

import csv
import io
import zipfile
from pathlib import Path


GTFS_URL = "https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip"

REQUIRED_FILES = [
    "agency.txt",
    "routes.txt",
    "trips.txt",
    "stops.txt",
    "stop_times.txt",
    "calendar.txt",
]


def read_gtfs_zip(zip_path: str | Path) -> dict[str, list[dict]]:
    zip_path = Path(zip_path)
    if not zip_path.exists():
        raise FileNotFoundError(f"GTFS zip not found: {zip_path}")

    data = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        available = set(zf.namelist())
        missing = [f for f in REQUIRED_FILES if f not in available]
        if missing:
            raise ValueError(f"Missing required GTFS files: {missing}")

        for filename in REQUIRED_FILES:
            with zf.open(filename) as f:
                text = io.TextIOWrapper(f, encoding="utf-8-sig")
                reader = csv.DictReader(text)
                data[filename.replace(".txt", "")] = list(reader)

    return data


def filter_tel_aviv_routes(data: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Filter to routes that serve Tel Aviv area stops."""
    ta_stop_ids = set()
    for stop in data["stops"]:
        lat = float(stop.get("stop_lat", 0))
        lon = float(stop.get("stop_lon", 0))
        if 32.0 <= lat <= 32.15 and 34.74 <= lon <= 34.85:
            ta_stop_ids.add(stop["stop_id"])

    ta_trip_ids = set()
    for st in data["stop_times"]:
        if st["stop_id"] in ta_stop_ids:
            ta_trip_ids.add(st["trip_id"])

    ta_route_ids = set()
    for trip in data["trips"]:
        if trip["trip_id"] in ta_trip_ids:
            ta_route_ids.add(trip["route_id"])

    filtered = {}
    filtered["agency"] = data["agency"]
    filtered["routes"] = [r for r in data["routes"] if r["route_id"] in ta_route_ids]
    filtered["trips"] = [t for t in data["trips"] if t["trip_id"] in ta_trip_ids]
    filtered["stops"] = [s for s in data["stops"] if s["stop_id"] in ta_stop_ids]
    filtered["stop_times"] = [
        st for st in data["stop_times"] if st["trip_id"] in ta_trip_ids
    ]
    filtered["calendar"] = data["calendar"]

    return filtered


def validate_gtfs(data: dict[str, list[dict]]) -> list[str]:
    """Return a list of validation warnings."""
    warnings = []

    if not data.get("agency"):
        warnings.append("No agencies found")
    if not data.get("routes"):
        warnings.append("No routes found")
    if not data.get("trips"):
        warnings.append("No trips found")
    if not data.get("stops"):
        warnings.append("No stops found")
    if not data.get("stop_times"):
        warnings.append("No stop_times found")
    if not data.get("calendar"):
        warnings.append("No calendar entries found")

    route_ids = {r["route_id"] for r in data.get("routes", [])}
    for trip in data.get("trips", []):
        if trip["route_id"] not in route_ids:
            warnings.append(f"Trip {trip['trip_id']} references unknown route {trip['route_id']}")
            break

    stop_ids = {s["stop_id"] for s in data.get("stops", [])}
    for st in data.get("stop_times", []):
        if st["stop_id"] not in stop_ids:
            warnings.append(f"stop_time references unknown stop {st['stop_id']}")
            break

    return warnings


def summary(data: dict[str, list[dict]]) -> dict[str, int]:
    return {key: len(rows) for key, rows in data.items()}


def download_gtfs(dest: str | Path) -> Path:
    import requests

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(GTFS_URL, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest
