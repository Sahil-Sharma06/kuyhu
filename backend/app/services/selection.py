"""Select the latest forecast available at the decision cutoff.

Rule: for a target time T on delivery day D (Europe/London calendar day), the cutoff is
D-1 at `cutoff` local time. The latest available forecast is the row with the maximum
publish_time <= cutoff and start_time - publish_time >= 0.
"""

from __future__ import annotations

from datetime import date, time, timedelta

import pandas as pd

LONDON = "Europe/London"


def parse_cutoff(value: str) -> time:
    """Parse 'HH:MM' into a time; raises ValueError on bad input."""
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def cutoff_utc(delivery_day: date, cutoff: time) -> pd.Timestamp:
    """Decision cutoff for `delivery_day`: D-1 at `cutoff` London time, as UTC (DST aware)."""
    local = pd.Timestamp.combine(delivery_day - timedelta(days=1), cutoff).tz_localize(LONDON)
    return local.tz_convert("UTC")


def delivery_day_of(start_time: pd.Series) -> pd.Series:
    """London calendar day each UTC target time belongs to."""
    return start_time.dt.tz_convert(LONDON).dt.date


def latest_forecasts(forecasts: pd.DataFrame, start: date, end: date, cutoff: time) -> pd.DataFrame:
    """Latest pre-cutoff forecast for every target time on delivery days start..end (inclusive).

    Returns columns: start_time, publish_time, forecast, horizon_h, delivery_day, cutoff_time.
    """
    df = forecasts.copy()
    df["delivery_day"] = delivery_day_of(df["start_time"])
    df = df[(df["delivery_day"] >= start) & (df["delivery_day"] <= end)]
    if df.empty:
        return _empty()
    cutoffs = {d: cutoff_utc(d, cutoff) for d in df["delivery_day"].unique()}
    df["cutoff_time"] = df["delivery_day"].map(cutoffs)
    df["horizon_h"] = (df["start_time"] - df["publish_time"]).dt.total_seconds() / 3600
    df = df[(df["publish_time"] <= df["cutoff_time"]) & (df["horizon_h"] >= 0)]
    if df.empty:
        return _empty()
    idx = df.groupby("start_time")["publish_time"].idxmax()
    out = df.loc[idx].sort_values("start_time").reset_index(drop=True)
    return out[["start_time", "publish_time", "forecast", "horizon_h", "delivery_day", "cutoff_time"]]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=["start_time", "publish_time", "forecast", "horizon_h", "delivery_day", "cutoff_time"])
