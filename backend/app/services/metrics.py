"""Forecast error metrics. Error is always defined as forecast - actual (MW)."""

from __future__ import annotations

from datetime import date, time

import numpy as np
import pandas as pd

from app.services.selection import LONDON, delivery_day_of, latest_forecasts

HORIZON_BUCKET_H = 6
HISTOGRAM_BIN_MW = 500


def summary(errors: pd.Series, actuals: pd.Series) -> dict[str, float | int | None]:
    """Summary accuracy statistics for aligned error and actual series."""
    n = len(errors)
    if n == 0:
        return {k: None for k in ("mae", "rmse", "mape", "bias", "p50", "p90", "p95", "p99", "mae_pct_of_mean_actual")} | {"n": 0}
    abs_err = errors.abs()
    nonzero = actuals > 0  # MAPE is undefined where actual output is zero.
    mape = float((abs_err[nonzero] / actuals[nonzero]).mean() * 100) if nonzero.any() else None
    mean_actual = float(actuals.mean())
    mae = float(abs_err.mean())
    return {
        "n": n,
        "mae": mae,
        "rmse": float(np.sqrt((errors**2).mean())),
        "mape": mape,
        "bias": float(errors.mean()),
        "p50": float(abs_err.quantile(0.50)),
        "p90": float(abs_err.quantile(0.90)),
        "p95": float(abs_err.quantile(0.95)),
        "p99": float(abs_err.quantile(0.99)),
        "mae_pct_of_mean_actual": mae / mean_actual * 100 if mean_actual else None,
    }


def evaluation_frame(forecasts: pd.DataFrame, actuals: pd.DataFrame, start: date, end: date, cutoff: time) -> pd.DataFrame:
    """Latest pre-cutoff forecasts joined to actuals on target time, with error = forecast - actual.

    Forecasts are hourly; each is matched to the actual for the half-hour starting at that time.
    Target times without an actual are dropped.
    """
    latest = latest_forecasts(forecasts, start, end, cutoff)
    df = latest.merge(actuals, on="start_time", how="inner")
    df["error"] = df["forecast"] - df["actual"]
    return df


def by_group(df: pd.DataFrame, key: pd.Series) -> list[dict]:
    """MAE / RMSE / bias / P90 per group of `key`."""
    out = []
    for k, g in df.groupby(key, sort=True):
        s = summary(g["error"], g["actual"])
        out.append({"key": k, "n": s["n"], "mae": s["mae"], "rmse": s["rmse"], "bias": s["bias"], "p90": s["p90"]})
    return out


def by_hour(df: pd.DataFrame) -> list[dict]:
    """Breakdown by London hour of day (0-23)."""
    return by_group(df, df["start_time"].dt.tz_convert(LONDON).dt.hour.rename("hour"))


def by_day(df: pd.DataFrame) -> list[dict]:
    """Breakdown by delivery day, with mean actual and forecast for context."""
    rows = by_group(df, df["delivery_day"])
    means = df.groupby("delivery_day")[["actual", "forecast"]].mean()
    for r in rows:
        r["mean_actual"] = float(means.loc[r["key"], "actual"])
        r["mean_forecast"] = float(means.loc[r["key"], "forecast"])
        r["key"] = r["key"].isoformat()
    return rows


def horizon_bucket(horizon_h: pd.Series) -> pd.Series:
    """Lower edge (hours) of each forecast horizon's bucket."""
    return (horizon_h // HORIZON_BUCKET_H * HORIZON_BUCKET_H).astype(int)


def by_horizon(forecasts: pd.DataFrame, actuals: pd.DataFrame, start: date, end: date) -> list[dict]:
    """Error by forecast horizon across ALL forecast vintages (not only the latest pre-cutoff one).

    This shows how accuracy degrades with lead time, independent of the chosen cutoff.
    """
    df = forecasts.merge(actuals, on="start_time", how="inner")
    df["delivery_day"] = delivery_day_of(df["start_time"])
    df = df[(df["delivery_day"] >= start) & (df["delivery_day"] <= end)]
    df["horizon_h"] = (df["start_time"] - df["publish_time"]).dt.total_seconds() / 3600
    df = df[df["horizon_h"] >= 0]
    df["error"] = df["forecast"] - df["actual"]
    rows = by_group(df, horizon_bucket(df["horizon_h"]).rename("bucket"))
    for r in rows:
        r["label"] = f"{r['key']}-{r['key'] + HORIZON_BUCKET_H}h"
    return rows


def histogram(errors: pd.Series) -> list[dict]:
    """Signed error counts in fixed-width MW bins; `bin` is the bin's lower edge."""
    if errors.empty:
        return []
    bins = (errors // HISTOGRAM_BIN_MW * HISTOGRAM_BIN_MW).astype(int)
    counts = bins.value_counts().sort_index()
    return [{"bin": int(b), "count": int(c)} for b, c in counts.items()]
