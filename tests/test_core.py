import csv
import datetime as dt
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr

from timeseries_resampler.cli import main
from timeseries_resampler.core import floor_time, parse_interval, parse_time, resample

T = dt.datetime


def recs(*items):
    return [(parse_time(t), dict(v)) for t, v in items]


DATA = recs(("2026-03-01 10:01:00", {"temp": "20", "id": "A"}), ("2026-03-01 10:14:59", {"temp": "22", "id": "A"}),
            ("2026-03-01 10:15:00", {"temp": "30", "id": "A"}), ("2026-03-01 10:50:00", {"temp": "x", "id": "A"}),
            ("2026-03-01 10:05:00", {"temp": "5", "id": "B"}))


class ParseTests(unittest.TestCase):
    def test_interval(self):
        self.assertEqual([parse_interval(x) for x in ("30s", "15min", "1h", "2d", "1w")],
                         [30, 900, 3600, 172800, 604800])
        with self.assertRaises(ValueError):
            parse_interval("5 parsecs")

    def test_time_formats(self):
        self.assertEqual(parse_time("2026-03-01T10:00:00Z"), T(2026, 3, 1, 10))
        self.assertEqual(parse_time("2026-03-01 10:00:00.123+02:00"), T(2026, 3, 1, 10))
        self.assertEqual(parse_time("01/03/2026 10:30"), T(2026, 3, 1, 10, 30))
        with self.assertRaises(ValueError):
            parse_time("yesterday")

    def test_floor(self):
        self.assertEqual(floor_time(T(2026, 3, 1, 10, 14, 59), 900), T(2026, 3, 1, 10, 0))
        self.assertEqual(floor_time(T(2026, 3, 4, 12), 604800).weekday(), 0)   # weekly buckets start Monday


class ResampleTests(unittest.TestCase):
    def test_mean_and_count(self):
        rows = resample([r for r in DATA if r[1]["id"] == "A"], "15min", ["temp"], ("mean", "count"))
        self.assertEqual([(r["time"][11:16], r["temp_mean"], r["temp_count"]) for r in rows],
                         [("10:00", "21", "2"), ("10:15", "30", "1"), ("10:45", "", "0")])

    def test_groups_and_gap_filling(self):
        rows = resample(DATA, "15min", ["temp"], ("max",), group_col="id", fill_gaps=True)
        a = [r for r in rows if r["id"] == "A"]
        self.assertEqual([r["time"][11:16] for r in a], ["10:00", "10:15", "10:30", "10:45"])
        self.assertEqual(a[2]["n"], 0)
        self.assertEqual([r["temp_max"] for r in rows if r["id"] == "B"], ["5"])

    def test_min_count_and_bad_agg(self):
        rows = resample(DATA[:3], "1h", ["temp"], ("mean",), min_count=4)
        self.assertEqual(rows[0]["temp_mean"], "")
        with self.assertRaises(ValueError):
            resample(DATA, "1h", ["temp"], ("mode",))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "s.csv"), os.path.join(d, "o.csv")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("ts,t\n2026-03-01 10:00,1\n2026-03-01 10:30,3\n2026-03-01 11:10,10\nbad,0\n")
            with redirect_stderr(io.StringIO()) as err:
                main([src, "-t", "ts", "-i", "1h", "-v", "t", "-a", "mean", "-a", "sum", "-o", out])
            self.assertIn("1 unparseable", err.getvalue())
            with open(out, encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual([(r["t_mean"], r["t_sum"]) for r in rows], [("2", "4"), ("10", "10")])


if __name__ == "__main__":
    unittest.main()
