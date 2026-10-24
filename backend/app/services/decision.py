"""Decision view for one delivery day: latest forecast, actual and a risk-adjusted lower bound."""

from __future__ import annotations

from datetime import date, time

import pandas as pd

from app.services.metrics import evaluation_frame
from app.services.selection import cutoff_utc, delivery_day_of, latest_forecasts

RISK_QUANTILE = 0.90


def over_forecast_quantile(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, start: date, end: date, cutoff: time, exclude: date
) -> float | None:
    """Empirical P90 of signed error (forecast - actual) over start..end, leaving out `exclude`.

    Excluding the chosen day avoids using that day's own outcome to size its buffer.
    """
    df = evaluation_frame(forecasts, actuals, start, end, cutoff)
    df = df[df["delivery_day"] != exclude]
    return float(df["error"].quantile(RISK_QUANTILE)) if not df.empty else None


def decision_day(forecasts: pd.DataFrame, actuals: pd.DataFrame, day: date, cutoff: time, period: tuple[date, date]) -> dict:
    latest = latest_forecasts(forecasts, day, day, cutoff)
    p90 = over_forecast_quantile(forecasts, actuals, *period, cutoff, exclude=day)
    buffer = max(p90 or 0.0, 0.0)
    day_actuals = actuals[delivery_day_of(actuals["start_time"]) == day]

    forecast_points = [
        {
            "time": r.start_time.isoformat(),
            "forecast": float(r.forecast),
            "lower_bound": float(r.forecast) - buffer,
            "publish_time": r.publish_time.isoformat(),
            "horizon_h": float(r.horizon_h),
        }
        for r in latest.itertuples()
    ]
    actual_points = [{"time": r.start_time.isoformat(), "actual": float(r.actual)} for r in day_actuals.itertuples()]

    joined = latest.merge(actuals, on="start_time", how="inner")
    err = joined["forecast"] - joined["actual"]
    return {
        "date": day.isoformat(),
        "cutoff_utc": cutoff_utc(day, cutoff).isoformat(),
        "risk_buffer_mw": buffer,
        "forecast": forecast_points,
        "actual": actual_points,
        "summary": {
            "latest_publish_time": latest["publish_time"].max().isoformat() if not latest.empty else None,
            "mean_forecast_mw": float(latest["forecast"].mean()) if not latest.empty else None,
            "mean_actual_mw": float(joined["actual"].mean()) if not joined.empty else None,
            "mean_lower_bound_mw": float(latest["forecast"].mean()) - buffer if not latest.empty else None,
            "mae_mw": float(err.abs().mean()) if not err.empty else None,
            "bias_mw": float(err.mean()) if not err.empty else None,
            "hours_covered": len(latest),
        },
    }
