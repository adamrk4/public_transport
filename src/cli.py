"""CLI for the public transport analysis pipeline."""

import argparse
import sys
from pathlib import Path


def cmd_download(args):
    from src.gtfs_parser import download_gtfs
    dest = Path(args.output)
    print(f"מוריד GTFS אל {dest} ...")
    download_gtfs(dest)
    print(f"הורדה הושלמה: {dest} ({dest.stat().st_size / 1_000_000:.1f} MB)")


def cmd_parse(args):
    from src.gtfs_parser import read_gtfs_zip, filter_tel_aviv_routes, validate_gtfs, summary
    print(f"קורא {args.gtfs_zip} ...")
    data = read_gtfs_zip(args.gtfs_zip)
    if args.tel_aviv:
        print("מסנן לאזור תל אביב ...")
        data = filter_tel_aviv_routes(data)
    warnings = validate_gtfs(data)
    for w in warnings:
        print(f"  אזהרה: {w}")
    s = summary(data)
    for k, v in s.items():
        print(f"  {k}: {v:,}")


def cmd_report(args):
    from src.gtfs_parser import read_gtfs_zip, filter_tel_aviv_routes
    from src.report import generate_markdown_report, generate_csv_report, save_csv

    data = read_gtfs_zip(args.gtfs_zip)
    if args.tel_aviv:
        data = filter_tel_aviv_routes(data)

    tw = None
    if args.time_window:
        parts = args.time_window.split("-")
        tw = (float(parts[0]), float(parts[1]))

    print(f"מפיק דוח לקו {args.route} (כיוון {args.direction}) ...")

    md = generate_markdown_report(
        data, args.route, args.direction,
        bunching_threshold=args.threshold,
        time_window=tw,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tw_suffix = f"_{args.time_window}" if args.time_window else ""
    md_path = out_dir / f"report_{args.route}_d{args.direction}{tw_suffix}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    if args.csv:
        rows = generate_csv_report(
            data, args.route, args.direction,
            bunching_threshold=args.threshold,
            time_window=tw,
        )
        csv_path = out_dir / f"report_{args.route}_d{args.direction}{tw_suffix}.csv"
        save_csv(rows, csv_path)
        print(f"  CSV: {csv_path}")


def cmd_simulate(args):
    from src.gtfs_parser import read_gtfs_zip, filter_tel_aviv_routes
    from src.schedule_simulator import (
        ScheduleModification, run_simulation, format_simulation_report,
    )

    data = read_gtfs_zip(args.gtfs_zip)
    if args.tel_aviv:
        data = filter_tel_aviv_routes(data)

    tw = None
    if args.time_window:
        parts = args.time_window.split("-")
        tw = (float(parts[0]), float(parts[1]))

    mod = ScheduleModification(
        mod_type=args.mod_type,
        route_short_name=args.route,
        direction_id=args.direction,
        count=args.count,
        fraction=args.fraction,
        shift_minutes=args.shift,
        headway_minutes=args.headway,
        time_window=tw,
        label=args.label or args.mod_type,
    )

    print(f"מריץ סימולציה על קו {args.route} — {args.mod_type} ...")
    result = run_simulation(
        data, [mod], args.route, args.direction,
        bunching_threshold=args.threshold,
        time_window=tw,
        label=args.label or args.mod_type,
    )

    report = format_simulation_report(result)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"  דוח נשמר: {out}")
    else:
        print()
        print(report)


def cmd_record(args):
    from src.rt_recorder import record_once
    out_dir = Path(args.output_dir)
    print(f"דוגם מיקומי רכבים בזמן אמת ...")
    count = record_once(out_dir, limit=args.limit)
    print(f"  נשמרו {count} מיקומים באזור ת\"א")


def cmd_list_routes(args):
    from src.gtfs_parser import read_gtfs_zip, filter_tel_aviv_routes
    data = read_gtfs_zip(args.gtfs_zip)
    if args.tel_aviv:
        data = filter_tel_aviv_routes(data)

    routes = {}
    for r in data["routes"]:
        name = r.get("route_short_name", "")
        desc = r.get("route_long_name", "")
        if name:
            routes[name] = desc

    for name in sorted(routes, key=lambda x: x.zfill(10)):
        print(f"  {name:>6}  {routes[name][:60]}")
    print(f"\nסה\"כ {len(routes)} קווים")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="public_transport",
        description="כלי לניתוח תחבורה ציבורית — תל אביב",
    )
    sub = parser.add_subparsers(dest="command")

    # download
    p_dl = sub.add_parser("download", help="הורדת קובץ GTFS")
    p_dl.add_argument("-o", "--output", default="data/raw/israel-gtfs.zip")

    # parse
    p_parse = sub.add_parser("parse", help="פרסור ואימות GTFS")
    p_parse.add_argument("gtfs_zip", nargs="?", default="data/raw/israel-gtfs.zip")
    p_parse.add_argument("--tel-aviv", action="store_true", default=True)
    p_parse.add_argument("--no-tel-aviv", dest="tel_aviv", action="store_false")

    # list-routes
    p_lr = sub.add_parser("list-routes", help="הצגת קווים זמינים")
    p_lr.add_argument("gtfs_zip", nargs="?", default="data/raw/israel-gtfs.zip")
    p_lr.add_argument("--tel-aviv", action="store_true", default=True)
    p_lr.add_argument("--no-tel-aviv", dest="tel_aviv", action="store_false")

    # report
    p_rpt = sub.add_parser("report", help="הפקת דוח headway + bunching")
    p_rpt.add_argument("route", help="מספר קו (route_short_name)")
    p_rpt.add_argument("gtfs_zip", nargs="?", default="data/raw/israel-gtfs.zip")
    p_rpt.add_argument("-d", "--direction", default="0", choices=["0", "1"])
    p_rpt.add_argument("-t", "--threshold", type=float, default=2.0,
                       help="סף bunching בדקות (ברירת מחדל: 2)")
    p_rpt.add_argument("-w", "--time-window", help="חלון זמן, למשל 7-10")
    p_rpt.add_argument("-o", "--output-dir", default="data/processed/reports")
    p_rpt.add_argument("--csv", action="store_true", help="גם CSV")
    p_rpt.add_argument("--tel-aviv", action="store_true", default=True)
    p_rpt.add_argument("--no-tel-aviv", dest="tel_aviv", action="store_false")

    # simulate
    p_sim = sub.add_parser("simulate", help="סימולציית שינוי לוח זמנים")
    p_sim.add_argument("route", help="מספר קו")
    p_sim.add_argument("mod_type", choices=["add_trips", "remove_trips", "shift_times", "set_headway"])
    p_sim.add_argument("gtfs_zip", nargs="?", default="data/raw/israel-gtfs.zip")
    p_sim.add_argument("-d", "--direction", default="0", choices=["0", "1"])
    p_sim.add_argument("-t", "--threshold", type=float, default=2.0)
    p_sim.add_argument("-w", "--time-window", help="חלון זמן, למשל 7-10")
    p_sim.add_argument("--count", type=int, default=0, help="מספר נסיעות להוסיף (add_trips)")
    p_sim.add_argument("--fraction", type=float, default=0.0, help="שיעור הסרה (remove_trips)")
    p_sim.add_argument("--shift", type=float, default=0.0, help="דקות הזזה (shift_times)")
    p_sim.add_argument("--headway", type=float, default=0.0, help="headway בדקות (set_headway)")
    p_sim.add_argument("--label", default="", help="שם הסימולציה")
    p_sim.add_argument("-o", "--output", help="קובץ פלט (ברירת מחדל: הדפסה)")
    p_sim.add_argument("--tel-aviv", action="store_true", default=True)
    p_sim.add_argument("--no-tel-aviv", dest="tel_aviv", action="store_false")

    # record
    p_rec = sub.add_parser("record", help="דגימת מיקומי רכבים בזמן אמת")
    p_rec.add_argument("-o", "--output-dir", default="data/raw/rt")
    p_rec.add_argument("--limit", type=int, default=200)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "download": cmd_download,
        "parse": cmd_parse,
        "list-routes": cmd_list_routes,
        "report": cmd_report,
        "simulate": cmd_simulate,
        "record": cmd_record,
    }
    commands[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
