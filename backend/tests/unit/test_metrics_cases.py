"""Metric functions: spec cases with hand-computed expected values."""

import json
import math
from datetime import date, time

import numpy as np
import pandas as pd
import pytest

from app.services.metrics import by_day, by_horizon, by_hour, evaluation_frame, histogram, horizon_bucket, summary

# 5-point fixture: errors = forecast - actual = [-10, 20, 0, -50, 30]
FORECAST = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0])
ACTUAL = pd.Series([110.0, 180.0, 300.0, 450.0, 470.0])


def test_five_point_fixture_hand_computed() -> None:
    s = summary(FORECAST - ACTUAL, ACTUAL)
    assert s["mae"] == pytest.approx(22.0)  # (10+20+0+50+30)/5
    assert s["rmse"] == pytest.approx(math.sqrt(780.0))  # (100+400+0+2500+900)/5
    assert s["bias"] == pytest.approx(-2.0)  # -10/5


def test_perfect_forecast_is_all_zero() -> None:
    s = summary(ACTUAL - ACTUAL, ACTUAL)
    assert s["mae"] == s["rmse"] == s["bias"] == 0
    assert s["p99"] == 0 and s["mape"] == 0


def test_over_forecast_gives_positive_bias() -> None:
    assert summary(pd.Series([5.0, 5.0]), pd.Series([100.0, 100.0]))["bias"] > 0
    assert summary(pd.Series([-5.0, -5.0]), pd.Series([100.0, 100.0]))["bias"] < 0


def test_percentiles_match_numpy() -> None:
    rng = np.random.default_rng(0)
    errors = pd.Series(rng.normal(300, 2000, 997))
    s = summary(errors, pd.Series(np.full(997, 10_000.0)))
    for key, q in (("p50", 50), ("p90", 90), ("p95", 95), ("p99", 99)):
        assert s[key] == pytest.approx(np.percentile(np.abs(errors), q))


def test_mape_with_zero_actual_is_finite() -> None:
    s = summary(pd.Series([10.0, 20.0, 5.0]), pd.Series([0.0, 100.0, 50.0]))
    assert s["mape"] == pytest.approx(15.0)  # (20/100 + 5/50) / 2 * 100
    assert math.isfinite(s["mape"])


def _ts(*iso: str) -> pd.Series:
    return pd.to_datetime(pd.Series(iso), utc=True)


def test_metrics_use_only_aligned_pairs() -> None:
    forecasts = pd.DataFrame(
        {
            "publish_time": _ts("2026-01-14T09:00Z", "2026-01-14T09:00Z", "2026-01-14T09:00Z"),
            "start_time": _ts("2026-01-15T00:00Z", "2026-01-15T01:00Z", "2026-01-15T02:00Z"),
            "forecast": [100.0, 200.0, 999.0],
        }
    )
    # No actual for 02:00; an actual at 03:00 has no forecast.
    actuals = pd.DataFrame({"start_time": _ts("2026-01-15T00:00Z", "2026-01-15T01:00Z", "2026-01-15T03:00Z"), "actual": [90.0, 230.0, 5.0]})
    df = evaluation_frame(forecasts, actuals, date(2026, 1, 15), date(2026, 1, 15), time(9, 30))
    assert df["error"].tolist() == [10.0, -30.0]
    assert summary(df["error"], df["actual"])["mae"] == pytest.approx(20.0)


def _no_nan(obj: object) -> None:
    json.dumps(obj, allow_nan=False)  # raises ValueError on NaN/inf


def test_empty_inputs_return_explicit_empty_results() -> None:
    forecasts = pd.DataFrame({"publish_time": _ts(), "start_time": _ts(), "forecast": pd.Series([], dtype=float)})
    actuals = pd.DataFrame({"start_time": _ts(), "actual": pd.Series([], dtype=float)})
    df = evaluation_frame(forecasts, actuals, date(2026, 1, 1), date(2026, 1, 31), time(9, 30))
    assert df.empty
    s = summary(df["error"], df["actual"])
    assert s["n"] == 0 and all(v is None for k, v in s.items() if k != "n")
    assert by_hour(df) == [] and by_day(df) == [] and histogram(df["error"]) == []
    assert by_horizon(forecasts, actuals, date(2026, 1, 1), date(2026, 1, 31)) == []
    _no_nan(s)


def test_single_point_has_no_nan() -> None:
    s = summary(pd.Series([3.0]), pd.Series([10.0]))
    _no_nan(s)
    assert s["p99"] == 3.0


@pytest.mark.parametrize(("h", "bucket"), [(0.0, 0), (5.999, 0), (6.0, 6), (11.99, 12 - 6), (12.0, 12), (36.0, 36), (37.5, 36)])
def test_horizon_bucket_boundaries_are_lower_inclusive(h: float, bucket: int) -> None:
    # Buckets are [lo, lo + 6h): a horizon of exactly 12h belongs to 12-18h.
    assert horizon_bucket(pd.Series([h])).tolist() == [bucket]


def _eval_frame(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["start_time", "forecast", "actual"])
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["error"] = df["forecast"] - df["actual"]
    df["delivery_day"] = df["start_time"].dt.tz_convert("Europe/London").dt.date
    return df


def test_by_hour_aggregates_in_london_time() -> None:
    df = _eval_frame(
        [
            ("2026-07-01T23:00Z", 110, 100),  # 00:00 BST -> hour 0
            ("2026-07-02T23:00Z", 70, 100),  # 00:00 BST -> hour 0
            ("2026-07-02T00:00Z", 100, 100),  # 01:00 BST -> hour 1
        ]
    )
    rows = {r["key"]: r for r in by_hour(df)}
    assert set(rows) == {0, 1}
    assert rows[0]["n"] == 2 and rows[0]["mae"] == pytest.approx(20) and rows[0]["bias"] == pytest.approx(-10)
    assert rows[1]["mae"] == 0


def test_by_day_aggregates_per_delivery_day() -> None:
    df = _eval_frame(
        [
            ("2026-01-15T00:00Z", 110, 100),
            ("2026-01-15T12:00Z", 130, 100),
            ("2026-01-16T00:00Z", 50, 100),
        ]
    )
    rows = by_day(df)
    assert [r["key"] for r in rows] == ["2026-01-15", "2026-01-16"]
    assert rows[0]["mae"] == pytest.approx(20) and rows[0]["mean_forecast"] == pytest.approx(120)
    assert rows[1]["bias"] == pytest.approx(-50) and rows[1]["mean_actual"] == pytest.approx(100)
