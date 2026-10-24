"""Fetch Elexon BMRS wind actuals (FUELHH) and forecasts (WINDFOR) and write a cleaned snapshot.

Usage: python scripts/fetch_data.py [--start 2026-01-01] [--end 2026-01-31]

Writes backend/data/actuals.csv, forecasts.csv (all times UTC, ISO 8601) and quality.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time as clock
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.cleaning import clean_actuals, clean_forecasts, missing_half_hours, to_utc_iso  # noqa: E402

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHUNK_DAYS = 7
# WINDFOR horizons reach ~66h, so a forecast for early-Jan targets can be published ~3 days before.
FORECAST_LOOKBACK_DAYS = 4
TIMEOUT_S = 120
RETRIES = 3
BACKOFF_S = 2.0


class FetchError(RuntimeError):
    """Raised when Elexon cannot be reached or returns an error after retries."""


def get(session: requests.Session, dataset: str, params: dict[str, str]) -> list[dict]:
    """GET a dataset stream, retrying timeouts, connection errors and 5xx responses."""
    url = f"{BASE_URL}/{dataset}/stream"
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, params={**params, "format": "json"}, timeout=TIMEOUT_S)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp.json()
            reason = f"HTTP {resp.status_code}"
        except (requests.Timeout, requests.ConnectionError) as exc:
            reason = type(exc).__name__
        except requests.HTTPError as exc:  # 4xx: retrying will not help
            raise FetchError(f"{dataset} {params}: {exc}") from exc
        if attempt < RETRIES:
            clock.sleep(BACKOFF_S * attempt)
    raise FetchError(f"{dataset} {params}: {reason} after {RETRIES} attempts")


def chunks(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    """Split [start, end) into windows of at most CHUNK_DAYS."""
    out, cur = [], start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def fetch_actuals_raw(session: requests.Session, start: date, end: date) -> pd.DataFrame:
    rows: list[dict] = []
    for a, b in chunks(datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())):
        rows += get(
            session,
            "FUELHH",
            {
                "settlementDateFrom": a.date().isoformat(),
                "settlementDateTo": (b - timedelta(days=1)).date().isoformat(),
                "fuelType": "WIND",
            },
        )
    return pd.DataFrame(rows, columns=["startTime", "publishTime", "fuelType", "generation"])


def fetch_forecasts_raw(session: requests.Session, start: date, end: date) -> pd.DataFrame:
    t0 = datetime.combine(start - timedelta(days=FORECAST_LOOKBACK_DAYS), datetime.min.time(), tzinfo=UTC)
    t1 = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    rows: list[dict] = []
    for a, b in chunks(t0, t1):
        # The API treats both bounds inclusively; subtract a second to avoid duplicating boundary publishes.
        rows += get(
            session, "WINDFOR", {"publishDateTimeFrom": a.strftime(fmt), "publishDateTimeTo": (b - timedelta(seconds=1)).strftime(fmt)}
        )
    return pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])


def build_snapshot(session: requests.Session, start: date, end: date, out_dir: Path) -> dict:
    """Fetch, clean and write the snapshot to out_dir; returns the data-quality report."""
    actuals, a_report = clean_actuals(fetch_actuals_raw(session, start, end))
    forecasts, f_report = clean_forecasts(fetch_forecasts_raw(session, start, end), start, end)
    gaps = missing_half_hours(actuals["start_time"], start, end)
    report = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "actual_rows": len(actuals),
        "forecast_rows": len(forecasts),
        "actuals_removed": a_report,
        "forecasts_removed": f_report,
        "missing_half_hours": [g.strftime("%Y-%m-%dT%H:%M:%SZ") for g in gaps],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for df, name in ((actuals, "actuals.csv"), (forecasts, "forecasts.csv")):
        out = df.copy()
        for col in ("start_time", "publish_time"):
            if col in out:
                out[col] = to_utc_iso(out[col])
        out.to_csv(out_dir / name, index=False, lineterminator="\n")
    (out_dir / "quality.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 1, 31))
    parser.add_argument("--out", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    with requests.Session() as session:
        report = build_snapshot(session, args.start, args.end, args.out)
    print(json.dumps({k: v for k, v in report.items() if k != "missing_half_hours"}, indent=2))
    print(f"missing half-hours: {len(report['missing_half_hours'])}")


if __name__ == "__main__":
    main()
