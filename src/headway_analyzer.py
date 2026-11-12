"""Compute headways from GTFS static stop_times for a given line and stop."""

from collections import defaultdict
from dataclasses import dataclass


@dataclass
class HeadwayRecord:
    stop_id: str
    stop_name: str
    trip_id: str
    prev_trip_id: str
    arrival_time: str
    prev_arrival_time: str
    headway_minutes: float
    scheduled_headway_minutes: float | None


def time_to_minutes(t: str) -> float:
    """Convert HH:MM:SS (may exceed 24h) to minutes since midnight."""
    parts = t.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60


def compute_headways(
    data: dict[str, list[dict]],
    route_short_name: str,
    direction_id: str = "0",
    service_ids: set[str] | None = None,
) -> list[HeadwayRecord]:
    """Compute headways per stop for a given route and direction.

    Returns a list of HeadwayRecord sorted by stop then time.
    """
    route_ids = {
        r["route_id"]
        for r in data["routes"]
        if r.get("route_short_name") == route_short_name
    }
    if not route_ids:
        return []

    trip_ids = set()
    for trip in data["trips"]:
        if trip["route_id"] not in route_ids:
            continue
        if trip.get("direction_id", "0") != direction_id:
            continue
        if service_ids and trip.get("service_id") not in service_ids:
            continue
        trip_ids.add(trip["trip_id"])

    if not trip_ids:
        return []

    stop_names = {s["stop_id"]: s.get("stop_name", "") for s in data["stops"]}

    # Group arrivals by stop_id
    arrivals_by_stop: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for st in data["stop_times"]:
        if st["trip_id"] not in trip_ids:
            continue
        arrival = st.get("arrival_time", "")
        if not arrival:
            continue
        minutes = time_to_minutes(arrival)
        arrivals_by_stop[st["stop_id"]].append((minutes, st["trip_id"], arrival))

    records = []
    for stop_id, arrivals in arrivals_by_stop.items():
        arrivals.sort()
        for i in range(1, len(arrivals)):
            prev_min, prev_trip, prev_time = arrivals[i - 1]
            curr_min, curr_trip, curr_time = arrivals[i]
            headway = curr_min - prev_min
            records.append(HeadwayRecord(
                stop_id=stop_id,
                stop_name=stop_names.get(stop_id, ""),
                trip_id=curr_trip,
                prev_trip_id=prev_trip,
                arrival_time=curr_time,
                prev_arrival_time=prev_time,
                headway_minutes=round(headway, 2),
                scheduled_headway_minutes=None,
            ))

    records.sort(key=lambda r: (r.stop_id, time_to_minutes(r.arrival_time)))
    return records


def stop_summary(records: list[HeadwayRecord]) -> list[dict]:
    """Aggregate headway stats per stop."""
    by_stop: dict[str, list[float]] = defaultdict(list)
    names: dict[str, str] = {}
    for r in records:
        by_stop[r.stop_id].append(r.headway_minutes)
        names[r.stop_id] = r.stop_name

    summary = []
    for stop_id, headways in sorted(by_stop.items()):
        n = len(headways)
        avg = sum(headways) / n
        mn = min(headways)
        mx = max(headways)
        std = (sum((h - avg) ** 2 for h in headways) / n) ** 0.5
        summary.append({
            "stop_id": stop_id,
            "stop_name": names[stop_id],
            "count": n,
            "avg_headway_min": round(avg, 1),
            "min_headway_min": round(mn, 1),
            "max_headway_min": round(mx, 1),
            "std_headway_min": round(std, 1),
        })

    return summary


def format_summary_table(summary: list[dict]) -> str:
    """Return a markdown table of the stop summary."""
    lines = [
        "| stop_id | stop_name | count | avg | min | max | std |",
        "|---------|-----------|-------|-----|-----|-----|-----|",
    ]
    for row in summary:
        lines.append(
            f"| {row['stop_id']} | {row['stop_name'][:30]} | {row['count']} "
            f"| {row['avg_headway_min']} | {row['min_headway_min']} "
            f"| {row['max_headway_min']} | {row['std_headway_min']} |"
        )
    return "\n".join(lines)
