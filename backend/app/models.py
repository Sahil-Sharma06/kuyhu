"""Response schemas (also drive the OpenAPI docs at /docs)."""

from __future__ import annotations

from pydantic import BaseModel


class Meta(BaseModel):
    start: str
    end: str
    default_cutoff: str
    timezone: str
    actual_rows: int
    forecast_rows: int


class ForecastPoint(BaseModel):
    time: str
    forecast: float
    lower_bound: float
    publish_time: str
    horizon_h: float


class ActualPoint(BaseModel):
    time: str
    actual: float


class DaySummary(BaseModel):
    latest_publish_time: str | None
    mean_forecast_mw: float | None
    mean_actual_mw: float | None
    mean_lower_bound_mw: float | None
    mae_mw: float | None
    bias_mw: float | None
    hours_covered: int


class DecisionDay(BaseModel):
    date: str
    cutoff_utc: str
    risk_buffer_mw: float
    forecast: list[ForecastPoint]
    actual: list[ActualPoint]
    summary: DaySummary


class Summary(BaseModel):
    n: int
    mae: float | None
    rmse: float | None
    mape: float | None
    bias: float | None
    p50: float | None
    p90: float | None
    p95: float | None
    p99: float | None
    mae_pct_of_mean_actual: float | None


class GroupStat(BaseModel):
    key: int | str
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    p90: float | None


class DayStat(GroupStat):
    mean_actual: float
    mean_forecast: float


class HorizonStat(GroupStat):
    label: str


class HistogramBin(BaseModel):
    bin: int
    count: int


class Metrics(BaseModel):
    start: str
    end: str
    cutoff: str
    summary: Summary
    by_day: list[DayStat]
    histogram: list[HistogramBin]
    horizon_range_h: list[float] | None
