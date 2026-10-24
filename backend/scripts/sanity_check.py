"""Independent re-computation of headline metrics, without pandas or the app's code.

Reads the raw CSV snapshot with the standard library, applies the cutoff rule with
plain loops and compares MAE / bias / RMSE with the running API's /api/metrics.

Usage: python scripts/sanity_check.py [--api http://localhost:8000] [--cutoff 09:30]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "data"
LONDON = ZoneInfo("Europe/London")


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--cutoff", default="09:30")
    args = p.parse_args()
    hh, mm = map(int, args.cutoff.split(":"))

    with open(DATA / "actuals.csv") as f:
        actual = {ts(r["start_time"]): float(r["generation"]) for r in csv.DictReader(f)}
    with open(DATA / "forecasts.csv") as f:
        forecast_rows = list(csv.DictReader(f))

    best: dict[datetime, tuple[datetime, float]] = {}
    for r in forecast_rows:
        pub, tgt = ts(r["publish_time"]), ts(r["start_time"])
        day = tgt.astimezone(LONDON).date()
        if not (datetime(2026, 1, 1).date() <= day <= datetime(2026, 1, 31).date()):
            continue
        cutoff = datetime.combine(day - timedelta(days=1), datetime.min.time().replace(hour=hh, minute=mm), LONDON).astimezone(UTC)
        if pub <= cutoff and tgt >= pub and (tgt not in best or pub > best[tgt][0]):
            best[tgt] = (pub, float(r["generation"]))

    errors = [f - actual[t] for t, (_, f) in best.items() if t in actual]
    mine = {
        "n": len(errors),
        "mae": sum(map(abs, errors)) / len(errors),
        "bias": sum(errors) / len(errors),
        "rmse": math.sqrt(sum(e * e for e in errors) / len(errors)),
    }
    api = json.load(urllib.request.urlopen(f"{args.api}/api/metrics?cutoff={args.cutoff}"))["summary"]

    per_day = defaultdict(list)
    for t, (pub, _) in best.items():
        per_day[t.astimezone(LONDON).date()].append(pub)
    print(f"days covered: {len(per_day)}, hours per day: {sorted({len(v) for v in per_day.values()})}")
    ok = True
    for k, v in mine.items():
        match = math.isclose(v, api[k], rel_tol=1e-9)
        ok &= match
        print(f"{k:>5}: independent={v:,.3f}  api={api[k]:,.3f}  {'OK' if match else 'MISMATCH'}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
