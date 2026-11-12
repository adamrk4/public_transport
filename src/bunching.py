"""Bunching metrics: measure how often consecutive buses arrive too close together."""

from collections import defaultdict
from dataclasses import dataclass

from src.headway_analyzer import HeadwayRecord

DEFAULT_BUNCHING_THRESHOLD_MINUTES = 2.0


@dataclass
class BunchingResult:
    stop_id: str
    stop_name: str
    total_arrivals: int
    bunched_arrivals: int
    bunching_ratio: float
    threshold_minutes: float
    avg_headway_min: float
    bunched_headways: list[float]


def compute_bunching(
    headway_records: list[HeadwayRecord],
    threshold_minutes: float = DEFAULT_BUNCHING_THRESHOLD_MINUTES,
) -> list[BunchingResult]:
    """Compute bunching index per stop from headway records.

    Bunching index = share of arrivals where the headway to the previous
    bus is <= threshold_minutes. A higher ratio means worse bunching.
    """
    by_stop: dict[str, list[HeadwayRecord]] = defaultdict(list)
    for r in headway_records:
        by_stop[r.stop_id].append(r)

    results = []
    for stop_id, records in sorted(by_stop.items()):
        headways = [r.headway_minutes for r in records]
        bunched = [h for h in headways if h <= threshold_minutes]
        n = len(headways)
        avg = sum(headways) / n if n else 0

        results.append(BunchingResult(
            stop_id=stop_id,
            stop_name=records[0].stop_name,
            total_arrivals=n,
            bunched_arrivals=len(bunched),
            bunching_ratio=round(len(bunched) / n, 4) if n else 0,
            threshold_minutes=threshold_minutes,
            avg_headway_min=round(avg, 1),
            bunched_headways=bunched,
        ))

    return results


def route_bunching_summary(results: list[BunchingResult]) -> dict:
    """Aggregate bunching across all stops for a route."""
    if not results:
        return {}

    total = sum(r.total_arrivals for r in results)
    bunched = sum(r.bunched_arrivals for r in results)
    ratios = [r.bunching_ratio for r in results]
    worst = max(results, key=lambda r: r.bunching_ratio)

    return {
        "stops_analyzed": len(results),
        "total_arrivals": total,
        "bunched_arrivals": bunched,
        "overall_bunching_ratio": round(bunched / total, 4) if total else 0,
        "avg_bunching_ratio_per_stop": round(sum(ratios) / len(ratios), 4),
        "worst_stop_id": worst.stop_id,
        "worst_stop_name": worst.stop_name,
        "worst_bunching_ratio": worst.bunching_ratio,
        "threshold_minutes": results[0].threshold_minutes,
    }


def format_bunching_table(results: list[BunchingResult]) -> str:
    """Markdown table of bunching per stop, sorted worst-first."""
    sorted_results = sorted(results, key=lambda r: -r.bunching_ratio)
    lines = [
        "| stop_id | stop_name | arrivals | bunched | ratio | avg_headway |",
        "|---------|-----------|----------|---------|-------|-------------|",
    ]
    for r in sorted_results:
        lines.append(
            f"| {r.stop_id} | {r.stop_name[:30]} | {r.total_arrivals} "
            f"| {r.bunched_arrivals} | {r.bunching_ratio:.1%} "
            f"| {r.avg_headway_min} |"
        )
    return "\n".join(lines)
