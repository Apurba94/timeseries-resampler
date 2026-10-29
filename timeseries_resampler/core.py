"""Bucket irregular sensor/logger data into regular intervals with aggregation and gap filling."""
import datetime as dt
import re
import statistics

_UNITS = {"s": 1, "sec": 1, "min": 60, "m": 60, "h": 3600, "hour": 3600, "d": 86400, "day": 86400, "w": 604800}
EPOCH = dt.datetime(1970, 1, 5)  # a Monday, so weekly buckets start on Mondays


def parse_interval(text):
    """'15min' -> 900 seconds; '1h', '30s', '2d', '1w'."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([a-z]+)\s*", text.lower())
    if not m or m.group(2) not in _UNITS:
        raise ValueError("bad interval %r (use e.g. 30s, 15min, 1h, 1d, 1w)" % text)
    return float(m.group(1)) * _UNITS[m.group(2)]


FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d",
           "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M:%S")


def parse_time(text, fmt=None):
    t = text.strip()
    if fmt == "epoch" or (fmt is None and re.fullmatch(r"\d{9,11}(\.\d+)?", t)):
        return dt.datetime.fromtimestamp(float(t), dt.timezone.utc).replace(tzinfo=None)
    if fmt:
        return dt.datetime.strptime(t, fmt)
    t = re.sub(r"(\.\d+)?(Z|[+-]\d\d:?\d\d)$", "", t)
    for f in FORMATS:
        try:
            return dt.datetime.strptime(t, f)
        except ValueError:
            pass
    raise ValueError("cannot parse time %r" % text)


def floor_time(t, seconds):
    delta = (t - EPOCH).total_seconds()
    return EPOCH + dt.timedelta(seconds=(delta // seconds) * seconds)


AGGREGATORS = {
    "mean": statistics.fmean, "median": statistics.median, "min": min, "max": max, "sum": sum,
    "count": len, "first": lambda v: v[0], "last": lambda v: v[-1],
    "sd": lambda v: statistics.stdev(v) if len(v) > 1 else 0.0,
}


def resample(records, interval, value_cols, how=("mean",), group_col=None, fill_gaps=False, min_count=1):
    """records: list of (datetime, {col: value_str, ...}). Returns list of output row dicts.

    Each output row: bucket start ('time'), optional group, '<col>_<agg>' for each value column and
    aggregation, and 'n' (records in bucket). Buckets with fewer than min_count valid values are blank.
    With fill_gaps, empty buckets between first and last are emitted with blank values.
    """
    sec = parse_interval(interval) if isinstance(interval, str) else interval
    for h in how:
        if h not in AGGREGATORS:
            raise ValueError("unknown aggregation %r" % h)
    buckets = {}
    for t, row in records:
        g = row.get(group_col, "") if group_col else ""
        b = floor_time(t, sec)
        buckets.setdefault(g, {}).setdefault(b, []).append((t, row))
    out = []
    for g in sorted(buckets):
        times = sorted(buckets[g])
        if fill_gaps and times:
            cur, end, full = times[0], times[-1], []
            while cur <= end:
                full.append(cur)
                cur += dt.timedelta(seconds=sec)
            times = full
        for b in times:
            items = sorted(buckets[g].get(b, []), key=lambda x: x[0])
            row = {"time": b.isoformat(sep=" ")}
            if group_col:
                row[group_col] = g
            row["n"] = len(items)
            for c in value_cols:
                vals = []
                for _, r in items:
                    try:
                        vals.append(float(r.get(c, "")))
                    except ValueError:
                        pass
                for h in how:
                    key = "%s_%s" % (c, h)
                    if len(vals) >= max(min_count, 1):
                        v = AGGREGATORS[h](vals)
                        row[key] = ("%.6g" % v) if isinstance(v, float) else str(v)
                    else:
                        row[key] = "0" if h == "count" else ""
            out.append(row)
    return out
