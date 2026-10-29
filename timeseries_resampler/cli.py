"""Command-line interface for timeseries-resampler."""
import argparse
import csv
import sys

from .core import AGGREGATORS, parse_time, resample


def main(argv=None):
    ap = argparse.ArgumentParser(prog="timeseries-resampler", description="Resample timestamped CSV data.")
    ap.add_argument("csvfile")
    ap.add_argument("-t", "--time", required=True, help="timestamp column")
    ap.add_argument("-i", "--interval", required=True, help="e.g. 30s, 15min, 1h, 1d, 1w")
    ap.add_argument("-v", "--value", action="append", required=True, help="value column (repeatable)")
    ap.add_argument("-a", "--agg", action="append", choices=sorted(AGGREGATORS), help="aggregation(s), default mean")
    ap.add_argument("-g", "--group", help="resample separately per value of this column (e.g. sensor id)")
    ap.add_argument("--format", help="strptime format of the timestamps, or 'epoch'")
    ap.add_argument("--fill-gaps", action="store_true", help="emit empty intervals")
    ap.add_argument("--min-count", type=int, default=1)
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)
    records, bad = [], 0
    with open(args.csvfile, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                records.append((parse_time(row[args.time], args.format), row))
            except (ValueError, KeyError):
                bad += 1
    how = args.agg or ["mean"]
    rows = resample(records, args.interval, args.value, how, args.group, args.fill_gaps, args.min_count)
    fields = ["time"] + ([args.group] if args.group else []) + ["n"] + ["%s_%s" % (c, h) for c in args.value for h in how]
    fh = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    if args.output:
        fh.close()
    print("%d records -> %d intervals%s" % (len(records), len(rows), "; %d unparseable timestamps" % bad if bad else ""),
          file=sys.stderr)
    return 0
