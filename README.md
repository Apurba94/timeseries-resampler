# timeseries-resampler

**Turn irregular logger, sensor or wearable data into clean regular intervals (every 15 min,
hourly, daily) with mean/min/max/sum/count per interval, per device, with optional gap filling.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

Field sensors, environmental loggers, lab monitors and wearables record at irregular times, with
dropouts and different rates per device. Analyses and figures need aligned intervals. Spreadsheet
pivoting by time is fiddly and error-prone around interval boundaries; this tool is explicit about
them (intervals are left-closed, `[10:00, 10:15)`).

## Features

- Intervals: `30s`, `15min`, `1h`, `1d`, `1w` (weeks start on Monday)
- Aggregations: mean, median, min, max, sum, count, first, last, sd (several at once)
- Per-group resampling (`-g sensor_id`), minimum valid values per interval (`--min-count`)
- Gap filling to make missing intervals explicit
- Timestamp parsing for ISO 8601 (with `Z`/offset/fractions dropped), day-first and US formats,
  epoch seconds, or an explicit `--format`; reports unparseable rows

## Usage

```bash
pip install .
timeseries-resampler logger.csv -t timestamp -i 15min -v temp -v humidity -a mean -a max
timeseries-resampler wearables.csv -t time -i 1h -v steps -a sum -g participant --fill-gaps -o hourly.csv
```

Time zones are not converted: make sure all timestamps share one zone before resampling.

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
