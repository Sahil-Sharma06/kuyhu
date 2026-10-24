import math

import pandas as pd
import pytest

from app.services.metrics import histogram, horizon_bucket, summary


def test_summary_known_values() -> None:
    errors = pd.Series([100.0, -100.0, 200.0, -200.0])
    actuals = pd.Series([1000.0, 1000.0, 2000.0, 2000.0])
    s = summary(errors, actuals)
    assert s["n"] == 4
    assert s["mae"] == pytest.approx(150)
    assert s["rmse"] == pytest.approx(math.sqrt((100**2 * 2 + 200**2 * 2) / 4))
    assert s["bias"] == pytest.approx(0)
    assert s["mape"] == pytest.approx(10)
    assert s["mae_pct_of_mean_actual"] == pytest.approx(10)
    assert s["p50"] == pytest.approx(150)


def test_bias_sign_is_forecast_minus_actual() -> None:
    # Over-forecasting gives positive bias.
    assert summary(pd.Series([50.0, 150.0]), pd.Series([1.0, 1.0]))["bias"] == pytest.approx(100)


def test_mape_skips_zero_actuals() -> None:
    s = summary(pd.Series([10.0, 10.0]), pd.Series([0.0, 100.0]))
    assert s["mape"] == pytest.approx(10)


def test_mape_none_when_all_actuals_zero() -> None:
    assert summary(pd.Series([1.0]), pd.Series([0.0]))["mape"] is None


def test_summary_empty() -> None:
    s = summary(pd.Series([], dtype=float), pd.Series([], dtype=float))
    assert s["n"] == 0 and s["mae"] is None


def test_percentiles_are_of_absolute_error() -> None:
    errors = pd.Series([-float(i) for i in range(1, 101)])
    s = summary(errors, pd.Series([1000.0] * 100))
    assert s["p90"] == pytest.approx(90.1)
    assert s["p99"] == pytest.approx(99.01)


def test_horizon_bucket_edges() -> None:
    assert horizon_bucket(pd.Series([0.0, 5.99, 6.0, 26.5])).tolist() == [0, 0, 6, 24]


def test_histogram_bins_negative_errors_downward() -> None:
    assert histogram(pd.Series([-1.0, 0.0, 499.0, 500.0])) == [
        {"bin": -500, "count": 1},
        {"bin": 0, "count": 2},
        {"bin": 500, "count": 1},
    ]
