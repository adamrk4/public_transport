"""Simulate schedule changes and compare headway/bunching metrics before vs. after.

Modifications are applied to the GTFS data dict (in-memory copy) and the
existing headway + bunching pipeline re-runs on the modified data to produce
a before/after comparison.
"""

from copy import deepcopy
from dataclasses import dataclass, field

from src.headway_analyzer import compute_headways, stop_summary, time_to_minutes
from src.bunching import compute_bunching, route_bunching_summary


@dataclass
class ScheduleModification:
    """A single modification to apply to the schedule.

    mod_type:
        "add_trips"    — inject new trips at even intervals within a time window.
                         Requires: count, time_window.
        "remove_trips" — remove a fraction of trips (evenly spaced removals).
                         Requires: fraction (0–1).
        "shift_times"  — shift all arrival/departure times by a fixed offset.
                         Requires: shift_minutes.
        "set_headway"  — replace trips in a time window with evenly-spaced ones
                         at the given headway.  Requires: headway_minutes, time_window.

    route_short_name, direction_id: scope the modification.
    time_window: (start_hour, end_hour) — applies only for add_trips / set_headway.
    """
    mod_type: str
    route_short_name: str
    direction_id: str = "0"
    count: int = 0
    fraction: float = 0.0
    shift_minutes: float = 0.0
    headway_minutes: float = 0.0
    time_window: tuple[float, float] | None = None
    label: str = ""


@dataclass
class SimulationResult:
    label: str
    route_short_name: str
    direction_id: str
    modifications: list[ScheduleModification]
    before: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)


def _route_and_trip_ids(data, route_short_name, direction_id):
    route_ids = {
        r["route_id"]
        for r in data["routes"]
        if r.get("route_short_name") == route_short_name
    }
    trip_ids = {
        t["trip_id"]
        for t in data["trips"]
        if t["route_id"] in route_ids
        and t.get("direction_id", "0") == direction_id
    }
    return route_ids, trip_ids


def _trips_stop_sequence(data, trip_ids):
    """For each trip, return sorted list of (stop_id, arrival_time, departure_time, stop_sequence)."""
    by_trip = {}
    for st in data["stop_times"]:
        if st["trip_id"] not in trip_ids:
            continue
        by_trip.setdefault(st["trip_id"], []).append(st)
    for tid in by_trip:
        by_trip[tid].sort(key=lambda s: int(s.get("stop_sequence", 0)))
    return by_trip


def _minutes_to_time(m: float) -> str:
    h = int(m // 60)
    rest = m - h * 60
    mins = int(rest)
    secs = int(round((rest - mins) * 60))
    return f"{h:02d}:{mins:02d}:{secs:02d}"


def apply_modification(data: dict, mod: ScheduleModification) -> dict:
    """Return a modified copy of data with the given modification applied."""
    data = deepcopy(data)
    route_ids, trip_ids = _route_and_trip_ids(data, mod.route_short_name, mod.direction_id)

    if not trip_ids:
        return data

    if mod.mod_type == "remove_trips":
        return _apply_remove_trips(data, trip_ids, mod.fraction)
    elif mod.mod_type == "shift_times":
        return _apply_shift_times(data, trip_ids, mod.shift_minutes)
    elif mod.mod_type == "add_trips":
        return _apply_add_trips(data, route_ids, trip_ids, mod)
    elif mod.mod_type == "set_headway":
        return _apply_set_headway(data, route_ids, trip_ids, mod)
    else:
        raise ValueError(f"Unknown mod_type: {mod.mod_type}")


def _apply_remove_trips(data, trip_ids, fraction):
    sorted_ids = sorted(trip_ids)
    n_remove = max(1, int(len(sorted_ids) * fraction))
    step = max(1, len(sorted_ids) // n_remove)
    to_remove = set(sorted_ids[i] for i in range(0, min(len(sorted_ids), n_remove * step), step))

    data["trips"] = [t for t in data["trips"] if t["trip_id"] not in to_remove]
    data["stop_times"] = [s for s in data["stop_times"] if s["trip_id"] not in to_remove]
    return data


def _apply_shift_times(data, trip_ids, shift_minutes):
    for st in data["stop_times"]:
        if st["trip_id"] not in trip_ids:
            continue
        for field_name in ("arrival_time", "departure_time"):
            t = st.get(field_name)
            if t:
                st[field_name] = _minutes_to_time(time_to_minutes(t) + shift_minutes)
    return data


def _apply_add_trips(data, route_ids, trip_ids, mod):
    if not mod.time_window or mod.count <= 0:
        return data

    trips_data = _trips_stop_sequence(data, trip_ids)
    if not trips_data:
        return data

    template_trip_id = next(iter(trips_data))
    template_stops = trips_data[template_trip_id]
    template_trip = next(t for t in data["trips"] if t["trip_id"] == template_trip_id)

    start_min = mod.time_window[0] * 60
    end_min = mod.time_window[1] * 60
    interval = (end_min - start_min) / (mod.count + 1)

    first_arrival_min = time_to_minutes(template_stops[0].get("arrival_time", "06:00:00"))

    for i in range(1, mod.count + 1):
        new_start = start_min + interval * i
        offset = new_start - first_arrival_min
        new_trip_id = f"sim_{mod.route_short_name}_{mod.direction_id}_{i}"

        new_trip = dict(template_trip)
        new_trip["trip_id"] = new_trip_id
        data["trips"].append(new_trip)

        for st in template_stops:
            new_st = dict(st)
            new_st["trip_id"] = new_trip_id
            for fn in ("arrival_time", "departure_time"):
                t = st.get(fn)
                if t:
                    new_st[fn] = _minutes_to_time(time_to_minutes(t) + offset)
            data["stop_times"].append(new_st)

    return data


def _apply_set_headway(data, route_ids, trip_ids, mod):
    if not mod.time_window or mod.headway_minutes <= 0:
        return data

    start_min = mod.time_window[0] * 60
    end_min = mod.time_window[1] * 60

    trips_data = _trips_stop_sequence(data, trip_ids)
    if not trips_data:
        return data

    # Remove existing trips in the time window
    trips_in_window = set()
    for tid, stops in trips_data.items():
        first_arr = time_to_minutes(stops[0].get("arrival_time", ""))
        if start_min <= first_arr < end_min:
            trips_in_window.add(tid)

    data["trips"] = [t for t in data["trips"]
                     if t["trip_id"] not in trips_in_window or t["trip_id"] not in trip_ids]
    data["stop_times"] = [s for s in data["stop_times"]
                          if s["trip_id"] not in trips_in_window]

    # Pick a template from outside the window, or use the original data
    remaining_tids = {t["trip_id"] for t in data["trips"]} & trip_ids
    if remaining_tids:
        template_tid = next(iter(remaining_tids))
        template_stops = trips_data[template_tid]
        template_trip = next(t for t in data["trips"] if t["trip_id"] == template_tid)
    else:
        template_tid = next(iter(trips_data))
        template_stops = trips_data[template_tid]
        template_trip = {"trip_id": template_tid, "route_id": next(iter(route_ids)),
                         "direction_id": mod.direction_id, "service_id": "wd"}
    first_arrival_min = time_to_minutes(template_stops[0].get("arrival_time", "06:00:00"))

    # Add evenly-spaced trips
    t = start_min
    idx = 0
    while t < end_min:
        new_tid = f"sim_hw_{mod.route_short_name}_{mod.direction_id}_{idx}"
        offset = t - first_arrival_min

        new_trip = dict(template_trip)
        new_trip["trip_id"] = new_tid
        data["trips"].append(new_trip)

        for st in template_stops:
            new_st = dict(st)
            new_st["trip_id"] = new_tid
            for fn in ("arrival_time", "departure_time"):
                tv = st.get(fn)
                if tv:
                    new_st[fn] = _minutes_to_time(time_to_minutes(tv) + offset)
            data["stop_times"].append(new_st)

        t += mod.headway_minutes
        idx += 1

    return data


def run_simulation(
    data: dict,
    modifications: list[ScheduleModification],
    route_short_name: str,
    direction_id: str = "0",
    bunching_threshold: float = 2.0,
    time_window: tuple[float, float] | None = None,
    label: str = "",
) -> SimulationResult:
    """Run before/after analysis with the given modifications."""

    def _analyze(d):
        headways = compute_headways(d, route_short_name, direction_id)
        if time_window:
            s, e = time_window[0] * 60, time_window[1] * 60
            headways = [r for r in headways
                        if s <= time_to_minutes(r.arrival_time) < e]
        summary = stop_summary(headways)
        bunching = compute_bunching(headways, bunching_threshold)
        agg = route_bunching_summary(bunching)
        return {
            "headway_records": len(headways),
            "stop_summary": summary,
            "bunching_results": bunching,
            "bunching_agg": agg,
        }

    before = _analyze(data)

    modified = data
    for mod in modifications:
        modified = apply_modification(modified, mod)

    after = _analyze(modified)

    delta = _compute_delta(before["bunching_agg"], after["bunching_agg"])

    return SimulationResult(
        label=label or "simulation",
        route_short_name=route_short_name,
        direction_id=direction_id,
        modifications=modifications,
        before=before["bunching_agg"],
        after=after["bunching_agg"],
        delta=delta,
    )


def _compute_delta(before: dict, after: dict) -> dict:
    if not before or not after:
        return {}
    return {
        "headway_records_before": before.get("total_arrivals", 0),
        "headway_records_after": after.get("total_arrivals", 0),
        "bunching_ratio_before": before.get("overall_bunching_ratio", 0),
        "bunching_ratio_after": after.get("overall_bunching_ratio", 0),
        "bunching_ratio_change": round(
            after.get("overall_bunching_ratio", 0) - before.get("overall_bunching_ratio", 0), 4
        ),
        "bunching_ratio_change_pct": _pct_change(
            before.get("overall_bunching_ratio", 0),
            after.get("overall_bunching_ratio", 0),
        ),
    }


def _pct_change(old, new):
    if old == 0:
        return None
    return round((new - old) / old * 100, 1)


def format_simulation_report(result: SimulationResult) -> str:
    """Markdown report of the simulation results."""
    dir_label = "הלוך" if result.direction_id == "0" else "חזור"
    lines = [
        f"# סימולציה: {result.label}",
        "",
        f"**קו:** {result.route_short_name} ({dir_label})",
        f"**שינויים:**",
    ]
    for mod in result.modifications:
        lines.append(f"  - {_mod_description(mod)}")

    lines += [
        "",
        "## השוואה לפני/אחרי",
        "",
        "| מדד | לפני | אחרי | שינוי |",
        "|-----|------|-------|-------|",
    ]

    b = result.before
    a = result.after
    d = result.delta

    if b and a:
        lines.append(
            f"| תחנות מנותחות | {b.get('stops_analyzed', '-')} "
            f"| {a.get('stops_analyzed', '-')} | |"
        )
        lines.append(
            f"| הגעות (מרווחים) | {b.get('total_arrivals', '-')} "
            f"| {a.get('total_arrivals', '-')} | |"
        )
        br = d.get("bunching_ratio_before", 0)
        ar = d.get("bunching_ratio_after", 0)
        chg = d.get("bunching_ratio_change_pct")
        chg_str = f"{chg:+.1f}%" if chg is not None else "—"
        lines.append(
            f"| Bunching ratio | {br:.1%} | {ar:.1%} | {chg_str} |"
        )

        if b.get("worst_stop_name"):
            lines.append(
                f"| תחנה גרועה ביותר (לפני) | {b['worst_stop_name']} ({b['worst_bunching_ratio']:.1%}) | | |"
            )
        if a.get("worst_stop_name"):
            lines.append(
                f"| תחנה גרועה ביותר (אחרי) | | {a['worst_stop_name']} ({a['worst_bunching_ratio']:.1%}) | |"
            )

    lines += [
        "",
        "## הנחות ומגבלות",
        "",
        "- הסימולציה מבוססת על שינוי לוח זמנים מתוכנן בלבד",
        "- נסיעות חדשות משתמשות בתבנית (רצף תחנות וזמני מעבר) של נסיעה קיימת",
        "- אין מודל לביקוש נוסעים או לעיכובי תנועה",
        "- שינוי ב-headway מתוכנן ישפיע על מדד bunching כי הסף נשאר קבוע",
        "",
    ]
    return "\n".join(lines)


def _mod_description(mod: ScheduleModification) -> str:
    tw = ""
    if mod.time_window:
        tw = f" ({int(mod.time_window[0]):02d}:00–{int(mod.time_window[1]):02d}:00)"

    if mod.mod_type == "add_trips":
        return f"הוספת {mod.count} נסיעות{tw}"
    elif mod.mod_type == "remove_trips":
        return f"הסרת {mod.fraction:.0%} מהנסיעות"
    elif mod.mod_type == "shift_times":
        return f"הזזת כל הזמנים ב-{mod.shift_minutes:+.0f} דקות"
    elif mod.mod_type == "set_headway":
        return f"קביעת headway ל-{mod.headway_minutes} דקות{tw}"
    return mod.mod_type
