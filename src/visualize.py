"""Visualizations for headway and bunching analysis."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from src.headway_analyzer import HeadwayRecord, stop_summary
from src.bunching import BunchingResult


plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f9fa",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
})


def plot_headway_distribution(
    headway_records: list[HeadwayRecord],
    route_name: str = "",
    output: str | Path | None = None,
    bins: int = 30,
) -> Path | None:
    """Histogram of headway values across all stops."""
    headways = [r.headway_minutes for r in headway_records]
    if not headways:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(headways, bins=bins, color="#4c72b0", edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Headway (דקות)")
    ax.set_ylabel("מספר מרווחים")
    ax.set_title(f"התפלגות Headway — קו {route_name}" if route_name else "התפלגות Headway")

    avg = sum(headways) / len(headways)
    ax.axvline(avg, color="#c44e52", linestyle="--", linewidth=1.5, label=f"ממוצע: {avg:.1f} דק'")
    ax.legend()

    return _save(fig, output, f"headway_dist_{route_name}")


def plot_headway_by_stop(
    headway_records: list[HeadwayRecord],
    route_name: str = "",
    output: str | Path | None = None,
    top_n: int = 20,
) -> Path | None:
    """Bar chart of average headway per stop (top N by volume)."""
    summary = stop_summary(headway_records)
    if not summary:
        return None

    summary.sort(key=lambda x: -x["count"])
    summary = summary[:top_n]
    summary.reverse()

    labels = [f"{s['stop_name'][:20]}\n({s['stop_id']})" for s in summary]
    avgs = [s["avg_headway_min"] for s in summary]

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.35)))
    bars = ax.barh(labels, avgs, color="#4c72b0", edgecolor="white", linewidth=0.5)
    ax.set_xlabel("ממוצע Headway (דקות)")
    ax.set_title(f"ממוצע Headway לפי תחנה — קו {route_name}" if route_name else "ממוצע Headway לפי תחנה")

    for bar, val in zip(bars, avgs):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", fontsize=8)

    fig.tight_layout()
    return _save(fig, output, f"headway_by_stop_{route_name}")


def plot_bunching_by_stop(
    bunching_results: list[BunchingResult],
    route_name: str = "",
    output: str | Path | None = None,
    top_n: int = 20,
) -> Path | None:
    """Bar chart of bunching ratio per stop (worst first)."""
    if not bunching_results:
        return None

    results = sorted(bunching_results, key=lambda r: -r.bunching_ratio)[:top_n]
    results.reverse()

    labels = [f"{r.stop_name[:20]}\n({r.stop_id})" for r in results]
    ratios = [r.bunching_ratio * 100 for r in results]

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.35)))
    colors = ["#c44e52" if r > 50 else "#dd8452" if r > 30 else "#4c72b0" for r in ratios]
    bars = ax.barh(labels, ratios, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("שיעור Bunching (%)")
    ax.set_title(f"Bunching לפי תחנה — קו {route_name}" if route_name else "Bunching לפי תחנה")
    ax.xaxis.set_major_formatter(ticker.PercentFormatter())

    for bar, val in zip(bars, ratios):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8)

    fig.tight_layout()
    return _save(fig, output, f"bunching_by_stop_{route_name}")


def plot_headway_timeline(
    headway_records: list[HeadwayRecord],
    stop_id: str,
    route_name: str = "",
    output: str | Path | None = None,
) -> Path | None:
    """Scatter plot of headway over time for a specific stop."""
    from src.headway_analyzer import time_to_minutes

    records = [r for r in headway_records if r.stop_id == stop_id]
    if not records:
        return None

    records.sort(key=lambda r: time_to_minutes(r.arrival_time))
    times = [time_to_minutes(r.arrival_time) / 60 for r in records]  # hours
    headways = [r.headway_minutes for r in records]
    stop_name = records[0].stop_name

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(times, headways, s=15, alpha=0.6, color="#4c72b0", edgecolors="none")
    ax.plot(times, headways, alpha=0.3, color="#4c72b0", linewidth=0.8)
    ax.set_xlabel("שעה")
    ax.set_ylabel("Headway (דקות)")
    ax.set_title(f"Headway לאורך היום — {stop_name} ({stop_id}), קו {route_name}")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x):02d}:00"))

    avg = sum(headways) / len(headways)
    ax.axhline(avg, color="#c44e52", linestyle="--", linewidth=1, alpha=0.7, label=f"ממוצע: {avg:.1f}")
    ax.legend()

    fig.tight_layout()
    return _save(fig, output, f"headway_timeline_{stop_id}_{route_name}")


def plot_simulation_comparison(
    before_bunching: list[BunchingResult],
    after_bunching: list[BunchingResult],
    route_name: str = "",
    label: str = "",
    output: str | Path | None = None,
    top_n: int = 15,
) -> Path | None:
    """Side-by-side bunching comparison before/after simulation."""
    if not before_bunching or not after_bunching:
        return None

    before_map = {r.stop_id: r for r in before_bunching}
    after_map = {r.stop_id: r for r in after_bunching}
    common = sorted(set(before_map) & set(after_map),
                    key=lambda sid: -before_map[sid].bunching_ratio)[:top_n]
    common.reverse()

    if not common:
        return None

    labels = [f"{before_map[sid].stop_name[:18]}" for sid in common]
    before_vals = [before_map[sid].bunching_ratio * 100 for sid in common]
    after_vals = [after_map[sid].bunching_ratio * 100 for sid in common]

    import numpy as np
    y = np.arange(len(labels))
    height = 0.35

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.4)))
    ax.barh(y - height / 2, before_vals, height, label="לפני", color="#4c72b0", edgecolor="white")
    ax.barh(y + height / 2, after_vals, height, label="אחרי", color="#55a868", edgecolor="white")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("שיעור Bunching (%)")
    ax.xaxis.set_major_formatter(ticker.PercentFormatter())
    title = f"השוואת Bunching — קו {route_name}"
    if label:
        title += f" ({label})"
    ax.set_title(title)
    ax.legend()

    fig.tight_layout()
    return _save(fig, output, f"sim_compare_{route_name}")


def _save(fig, output, default_name) -> Path:
    if output:
        path = Path(output)
    else:
        path = Path(f"data/processed/charts/{default_name}.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
