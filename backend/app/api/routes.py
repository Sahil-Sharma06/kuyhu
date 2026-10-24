"""HTTP routes. All times in responses are ISO 8601 UTC; dates are Europe/London delivery days."""

from __future__ import annotations

from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.data.loader import load_actuals, load_forecasts
from app.models import DecisionDay, GroupStat, HorizonStat, Meta, Metrics
from app.services import metrics
from app.services.decision import decision_day
from app.services.selection import delivery_day_of, parse_cutoff

DEFAULT_CUTOFF = "09:30"

router = APIRouter(prefix="/api")

CutoffParam = Annotated[str, Query(pattern=r"^\d{1,2}:\d{2}$", description="Decision time on D-1, HH:MM Europe/London")]


def data_period() -> tuple[date, date]:
    """First and last delivery day covered by actuals."""
    days = delivery_day_of(load_actuals()["start_time"])
    return days.min(), days.max()


def _cutoff(value: str) -> time:
    try:
        return parse_cutoff(value)
    except ValueError as exc:
        raise HTTPException(422, f"Invalid cutoff '{value}': expected HH:MM") from exc


def _period(start: date | None, end: date | None) -> tuple[date, date]:
    lo, hi = data_period()
    start, end = start or lo, end or hi
    if start > end:
        raise HTTPException(422, "start must be on or before end")
    if end < lo or start > hi:
        raise HTTPException(404, f"No data in range; available {lo}..{hi}")
    return max(start, lo), min(end, hi)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta", response_model=Meta)
def meta() -> dict:
    lo, hi = data_period()
    return {
        "start": lo.isoformat(),
        "end": hi.isoformat(),
        "default_cutoff": DEFAULT_CUTOFF,
        "timezone": "Europe/London",
        "actual_rows": len(load_actuals()),
        "forecast_rows": len(load_forecasts()),
    }


@router.get("/forecast-vs-actual", response_model=DecisionDay)
def forecast_vs_actual(date: date, cutoff: CutoffParam = DEFAULT_CUTOFF) -> dict:
    lo, hi = data_period()
    if not lo <= date <= hi:
        raise HTTPException(404, f"No data for {date}; available {lo}..{hi}")
    return decision_day(load_forecasts(), load_actuals(), date, _cutoff(cutoff), (lo, hi))


@router.get("/metrics", response_model=Metrics)
def get_metrics(start: date | None = None, end: date | None = None, cutoff: CutoffParam = DEFAULT_CUTOFF) -> dict:
    lo, hi = _period(start, end)
    df = metrics.evaluation_frame(load_forecasts(), load_actuals(), lo, hi, _cutoff(cutoff))
    return {
        "start": lo.isoformat(),
        "end": hi.isoformat(),
        "cutoff": cutoff,
        "summary": metrics.summary(df["error"], df["actual"]),
        "by_day": metrics.by_day(df),
        "histogram": metrics.histogram(df["error"]),
        "horizon_range_h": [float(df["horizon_h"].min()), float(df["horizon_h"].max())] if not df.empty else None,
    }


@router.get("/error-by-hour", response_model=list[GroupStat])
def error_by_hour(start: date | None = None, end: date | None = None, cutoff: CutoffParam = DEFAULT_CUTOFF) -> list[dict]:
    lo, hi = _period(start, end)
    return metrics.by_hour(metrics.evaluation_frame(load_forecasts(), load_actuals(), lo, hi, _cutoff(cutoff)))


@router.get("/error-by-horizon", response_model=list[HorizonStat])
def error_by_horizon(start: date | None = None, end: date | None = None) -> list[dict]:
    lo, hi = _period(start, end)
    return metrics.by_horizon(load_forecasts(), load_actuals(), lo, hi)
