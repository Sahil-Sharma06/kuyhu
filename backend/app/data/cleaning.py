"""Pure cleaning and data-quality functions for raw Elexon rows (no I/O).

Used by scripts/fetch_data.py when building the snapshot and by the API to report gaps.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

LONDON = "Europe/London"
# GB installed wind capacity is ~30 GW; anything outside [0, MAX_PLAUSIBLE_MW] is a data error.
MAX_PLAUSIBLE_MW = 35_000


def implausible(generation: pd.Series) -> pd.Series:
    """Boolean mask of values that are negative or above MAX_PLAUSIBLE_MW."""
    return (generation < 0) | (generation > MAX_PLAUSIBLE_MW)


def clean_actuals(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """WIND-only, non-null, plausible, one row per start_time (latest publish wins, ties by value).

    Returns (columns start_time, generation) and counts of rows removed per reason.
    """
    df = raw[raw["fuelType"] == "WIND"].copy()
    report = {"non_wind": len(raw) - len(df)}
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    report["missing_value"] = int(df["generation"].isna().sum())
    df = df.dropna(subset=["generation"])
    bad = implausible(df["generation"])
    report["implausible"] = int(bad.sum())
    df = df[~bad]
    # Full sort key makes the choice deterministic regardless of input row order.
    df = df.sort_values(["start_time", "publish_time", "generation"], kind="mergesort")
    before = len(df)
    df = df.drop_duplicates("start_time", keep="last")
    report["duplicates"] = before - len(df)
    return df[["start_time", "generation"]].reset_index(drop=True), report


def clean_forecasts(raw: pd.DataFrame, start: date, end: date) -> tuple[pd.DataFrame, dict[str, int]]:
    """Forecast rows for targets near start..end with horizon >= 0, one row per (publish_time, start_time)."""
    df = raw.copy()
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")
    report = {"missing_value": int(df["generation"].isna().sum())}
    df = df.dropna(subset=["generation"])
    bad = implausible(df["generation"])
    report["implausible"] = int(bad.sum())
    df = df[~bad]
    # Keep targets in the delivery window (a day of margin either side for timezone shifts).
    lo = pd.Timestamp((start - timedelta(days=1)).isoformat(), tz="UTC")
    hi = pd.Timestamp((end + timedelta(days=2)).isoformat(), tz="UTC")
    df = df[(df["start_time"] >= lo) & (df["start_time"] < hi)]
    negative = df["start_time"] < df["publish_time"]
    report["negative_horizon"] = int(negative.sum())
    df = df[~negative]
    df = df.sort_values(["start_time", "publish_time", "generation"], kind="mergesort")
    before = len(df)
    df = df.drop_duplicates(["publish_time", "start_time"], keep="last")
    report["duplicates"] = before - len(df)
    return df[["publish_time", "start_time", "generation"]].reset_index(drop=True), report


def expected_half_hours(start: date, end: date) -> pd.DatetimeIndex:
    """Every half-hour start (UTC) of London delivery days start..end; handles 46/50-period DST days."""
    lo = pd.Timestamp(start.isoformat()).tz_localize(LONDON)
    hi = pd.Timestamp((end + timedelta(days=1)).isoformat()).tz_localize(LONDON)
    return pd.date_range(lo, hi, freq="30min", inclusive="left").tz_convert("UTC")


def missing_half_hours(start_times: pd.Series, start: date, end: date) -> list[pd.Timestamp]:
    """Expected half-hours with no actual."""
    return list(expected_half_hours(start, end).difference(pd.DatetimeIndex(start_times)))


def to_utc_iso(ts: pd.Series) -> pd.Series:
    """Serialise UTC timestamps as '2026-01-01T00:00:00Z'."""
    return ts.dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
