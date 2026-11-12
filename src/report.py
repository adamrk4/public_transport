"""Generate markdown and CSV reports combining headway and bunching analysis."""

import csv
from datetime import datetime, timezone
from pathlib import Path

from src.headway_analyzer import compute_headways, stop_summary, HeadwayRecord
from src.bunching import compute_bunching, route_bunching_summary, BunchingResult


def generate_markdown_report(
    data: dict[str, list[dict]],
    route_short_name: str,
    direction_id: str = "0",
    bunching_threshold: float = 2.0,
    service_ids: set[str] | None = None,
    time_window: tuple[float, float] | None = None,
) -> str:
    """Generate a full markdown report for a route.

    time_window: optional (start_hour, end_hour) to filter, e.g. (7, 10) for morning peak.
    """
    headways = compute_headways(
        data, route_short_name, direction_id, service_ids
    )

    if time_window:
        start_min = time_window[0] * 60
        end_min = time_window[1] * 60
        headways = [
            r for r in headways
            if start_min <= _arrival_minutes(r.arrival_time) < end_min
        ]

    if not headways:
        return f"# דוח קו {route_short_name}\n\nאין נתונים לתנאים שנבחרו.\n"

    hw_summary = stop_summary(headways)
    bunching_results = compute_bunching(headways, bunching_threshold)
    bunching_agg = route_bunching_summary(bunching_results)

    tw_label = _time_window_label(time_window)
    dir_label = "הלוך" if direction_id == "0" else "חזור"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# דוח ביצועי קו {route_short_name}",
        "",
        f"**תאריך הפקה:** {now}",
        f"**כיוון:** {dir_label} (direction_id={direction_id})",
        f"**חלון זמן:** {tw_label}",
        f"**סף bunching:** {bunching_threshold} דקות",
        "",
        "---",
        "",
        "## סיכום קו",
        "",
        f"- תחנות מנותחות: {bunching_agg['stops_analyzed']}",
        f"- הגעות (מרווחים): {bunching_agg['total_arrivals']}",
        f"- הגעות bunched: {bunching_agg['bunched_arrivals']} ({bunching_agg['overall_bunching_ratio']:.1%})",
        f"- תחנה עם bunching גבוה ביותר: {bunching_agg['worst_stop_name']} ({bunching_agg['worst_stop_id']}) — {bunching_agg['worst_bunching_ratio']:.1%}",
        "",
        "---",
        "",
        "## Headway לפי תחנה (טופ 10 לפי נפח)",
        "",
        _headway_table(hw_summary, top_n=10),
        "",
        "---",
        "",
        "## Bunching לפי תחנה (טופ 10 — הגרועים ביותר)",
        "",
        _bunching_table(bunching_results, top_n=10),
        "",
        "---",
        "",
        "## מתודולוגיה",
        "",
        "- **מקור נתונים:** GTFS סטטי של משרד התחבורה הישראלי",
        f"  - URL: `https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip`",
        "- **אזור:** תל אביב (bbox 32.0–32.15°N, 34.74–34.85°E)",
        "- **Headway:** מרווח זמן בדקות בין הגעות עוקבות של אותו קו באותה תחנה",
        f"- **Bunching index:** שיעור ההגעות עם headway ≤ {bunching_threshold} דקות",
        "- **חישוב:** מבוסס על לוח זמנים מתוכנן (arrival_time ב-stop_times.txt), לא על נתוני בפועל",
        "",
        "## מגבלות",
        "",
        "- הנתונים מבוססים על לוח זמנים מתוכנן — אין השוואה לביצוע בפועל",
        "- סינון גיאוגרפי לפי bounding box, לא לפי שיוך מדויק לעיר",
        "- קווים תדירים (headway מתוכנן < סף) יראו bunching מתוכנן גבוה — זה לא בהכרח בעיה תפעולית",
        "- service_id לא סונן אלא אם צוין — מערב ימי חול, שבת, וחג",
        "",
    ]
    return "\n".join(lines)


def generate_csv_report(
    data: dict[str, list[dict]],
    route_short_name: str,
    direction_id: str = "0",
    bunching_threshold: float = 2.0,
    service_ids: set[str] | None = None,
    time_window: tuple[float, float] | None = None,
) -> list[dict]:
    """Return rows for CSV export."""
    headways = compute_headways(data, route_short_name, direction_id, service_ids)

    if time_window:
        start_min = time_window[0] * 60
        end_min = time_window[1] * 60
        headways = [
            r for r in headways
            if start_min <= _arrival_minutes(r.arrival_time) < end_min
        ]

    hw_summary = stop_summary(headways)
    bunching_results = compute_bunching(headways, bunching_threshold)
    bunching_map = {r.stop_id: r for r in bunching_results}

    rows = []
    for hw in hw_summary:
        b = bunching_map.get(hw["stop_id"])
        rows.append({
            "route": route_short_name,
            "direction_id": direction_id,
            "stop_id": hw["stop_id"],
            "stop_name": hw["stop_name"],
            "arrival_count": hw["count"],
            "avg_headway_min": hw["avg_headway_min"],
            "min_headway_min": hw["min_headway_min"],
            "max_headway_min": hw["max_headway_min"],
            "std_headway_min": hw["std_headway_min"],
            "bunching_threshold_min": bunching_threshold,
            "bunched_count": b.bunched_arrivals if b else 0,
            "bunching_ratio": b.bunching_ratio if b else 0,
        })
    return rows


def save_csv(rows: list[dict], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return path
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def _arrival_minutes(t: str) -> float:
    parts = t.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60


def _time_window_label(tw: tuple[float, float] | None) -> str:
    if not tw:
        return "כל היום"
    return f"{int(tw[0]):02d}:00–{int(tw[1]):02d}:00"


def _headway_table(hw_summary: list[dict], top_n: int = 10) -> str:
    sorted_hw = sorted(hw_summary, key=lambda x: -x["count"])[:top_n]
    lines = [
        "| תחנה | שם | מרווחים | ממוצע | מינימום | מקסימום | סטיית תקן |",
        "|------|-----|---------|-------|---------|---------|-----------|",
    ]
    for row in sorted_hw:
        lines.append(
            f"| {row['stop_id']} | {row['stop_name'][:25]} "
            f"| {row['count']} | {row['avg_headway_min']} "
            f"| {row['min_headway_min']} | {row['max_headway_min']} "
            f"| {row['std_headway_min']} |"
        )
    return "\n".join(lines)


def _bunching_table(results: list[BunchingResult], top_n: int = 10) -> str:
    sorted_r = sorted(results, key=lambda r: -r.bunching_ratio)[:top_n]
    lines = [
        "| תחנה | שם | הגעות | bunched | שיעור | ממוצע headway |",
        "|------|-----|-------|---------|-------|---------------|",
    ]
    for r in sorted_r:
        lines.append(
            f"| {r.stop_id} | {r.stop_name[:25]} "
            f"| {r.total_arrivals} | {r.bunched_arrivals} "
            f"| {r.bunching_ratio:.1%} | {r.avg_headway_min} |"
        )
    return "\n".join(lines)
