"""Record real-time SIRI vehicle locations from Open Bus Stride API."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://open-bus-stride-api.hasadna.org.il"

TEL_AVIV_BBOX = {
    "lat_min": 32.0,
    "lat_max": 32.15,
    "lon_min": 34.74,
    "lon_max": 34.85,
}


def fetch_vehicle_locations(
    limit: int = 100,
    recorded_at_time_from: str | None = None,
    recorded_at_time_to: str | None = None,
) -> list[dict]:
    params = {
        "limit": limit,
        "order_by": "recorded_at_time desc",
    }
    if recorded_at_time_from:
        params["recorded_at_time_from"] = recorded_at_time_from
    if recorded_at_time_to:
        params["recorded_at_time_to"] = recorded_at_time_to

    resp = requests.get(
        f"{API_BASE}/siri_vehicle_locations/list",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def filter_tel_aviv(locations: list[dict]) -> list[dict]:
    bbox = TEL_AVIV_BBOX
    return [
        loc for loc in locations
        if (loc.get("lat") and loc.get("lon")
            and bbox["lat_min"] <= loc["lat"] <= bbox["lat_max"]
            and bbox["lon_min"] <= loc["lon"] <= bbox["lon_max"])
    ]


def save_snapshot(locations: list[dict], output_dir: str | Path) -> Path | None:
    if not locations:
        return None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"siri_locations_{ts}.jsonl"

    with open(path, "w") as f:
        for loc in locations:
            f.write(json.dumps(loc, default=str) + "\n")

    return path


def record_once(output_dir: str | Path, limit: int = 500) -> dict:
    """Fetch one snapshot, filter to Tel Aviv, save. Return stats."""
    try:
        locations = fetch_vehicle_locations(limit=limit)
        ta_locations = filter_tel_aviv(locations)
        path = save_snapshot(ta_locations, output_dir)
        stats = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fetched": len(locations),
            "tel_aviv": len(ta_locations),
            "saved_to": str(path) if path else None,
            "error": None,
        }
        logger.info("Recorded %d/%d locations", len(ta_locations), len(locations))
        return stats
    except Exception as e:
        logger.error("Recording failed: %s", e)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fetched": 0,
            "tel_aviv": 0,
            "saved_to": None,
            "error": str(e),
        }


def record_loop(
    output_dir: str | Path,
    interval_seconds: int = 60,
    max_iterations: int | None = None,
    limit: int = 500,
) -> list[dict]:
    """Poll at interval. Returns list of stats per iteration."""
    log = []
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        stats = record_once(output_dir, limit=limit)
        log.append(stats)
        iteration += 1
        if max_iterations and iteration >= max_iterations:
            break
        time.sleep(interval_seconds)
    return log


def save_log(log: list[dict], output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"recording_log_{ts}.json"
    with open(path, "w") as f:
        json.dump(log, f, indent=2, default=str)
    return path
