"""Fetch Elexon BMRS wind actuals (FUELHH) and forecasts (WINDFOR) and write a cleaned snapshot.

Usage: python scripts/fetch_data.py [--start 2026-01-01] [--end 2026-01-31]

Writes backend/data/actuals.csv and backend/data/forecasts.csv (all times UTC, ISO 8601).
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHUNK_DAYS = 7
# WINDFOR horizons reach ~66h, so a forecast for early-Jan targets can be published ~3 days before.
FORECAST_LOOKBACK_DAYS = 4
TIMEOUT_S = 120


def _get(dataset: str, params: dict[str, str]) -> list[dict]:
    resp = requests.get(f"{BASE_URL}/{dataset}/stream", params={**params, "format": "json"}, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()


def _chunks(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    out, cur = [], start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    rows: list[dict] = []
    for a, b in _chunks(datetime.combine(start, datetime.min.time()), datetime.combine(end + timedelta(days=1), datetime.min.time())):
        rows += _get(
            "FUELHH",
            {
                "settlementDateFrom": a.date().isoformat(),
                "settlementDateTo": (b - timedelta(days=1)).date().isoformat(),
                "fuelType": "WIND",
            },
        )
    return clean_actuals(pd.DataFrame(rows))


def fetch_forecasts(start: date, end: date) -> pd.DataFrame:
    t0 = datetime.combine(start - timedelta(days=FORECAST_LOOKBACK_DAYS), datetime.min.time(), tzinfo=UTC)
    t1 = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    rows: list[dict] = []
    for a, b in _chunks(t0, t1):
        # The API treats both bounds inclusively; subtract a second to avoid duplicating boundary publishes.
        rows += _get("WINDFOR", {"publishDateTimeFrom": a.strftime(fmt), "publishDateTimeTo": (b - timedelta(seconds=1)).strftime(fmt)})
    return clean_forecasts(pd.DataFrame(rows), start, end)


def clean_actuals(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["fuelType"] == "WIND"].copy()
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["generation"])
    # Keep the most recently published value if a settlement period appears twice.
    df = df.sort_values("publish_time").drop_duplicates("start_time", keep="last")
    return df[["start_time", "generation"]].sort_values("start_time").reset_index(drop=True)


def clean_forecasts(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    df = df.copy()
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["generation"])
    # Keep only targets in the delivery window (with a day of margin for timezone shifts) and non-negative horizons.
    lo = pd.Timestamp(start.isoformat(), tz="UTC") - pd.Timedelta(days=1)
    hi = pd.Timestamp(end.isoformat(), tz="UTC") + pd.Timedelta(days=2)
    df = df[(df["start_time"] >= lo) & (df["start_time"] < hi) & (df["start_time"] >= df["publish_time"])]
    df = df.drop_duplicates(["publish_time", "start_time"], keep="last")
    return df[["publish_time", "start_time", "generation"]].sort_values(["start_time", "publish_time"]).reset_index(drop=True)


def _write(df: pd.DataFrame, name: str) -> None:
    out = df.copy()
    for col in ("start_time", "publish_time"):
        if col in out:
            out[col] = out[col].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(DATA_DIR / name, index=False)
    print(f"wrote {name}: {len(out)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 1, 31))
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write(fetch_actuals(args.start, args.end), "actuals.csv")
    _write(fetch_forecasts(args.start, args.end), "forecasts.csv")


if __name__ == "__main__":
    main()
