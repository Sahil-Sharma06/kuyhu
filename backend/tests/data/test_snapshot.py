"""Integrity of the committed January 2026 snapshot."""

import json
from datetime import date, time

import pandas as pd

from app.data.cleaning import expected_half_hours, missing_half_hours
from app.data.loader import DATA_DIR, load_actuals, load_forecasts
from app.services.selection import latest_forecasts

JAN = (date(2026, 1, 1), date(2026, 1, 31))
QUALITY = json.loads((DATA_DIR / "quality.json").read_text())


def test_actuals_cover_every_half_hour_of_january_minus_documented_gaps() -> None:
    actuals = load_actuals()
    gaps = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in missing_half_hours(actuals["start_time"], *JAN)]
    print(f"missing half-hours in snapshot: {gaps or 'none'}")
    assert gaps == QUALITY["missing_half_hours"]
    assert len(expected_half_hours(*JAN)) == 48 * 31
    assert len(actuals) == 48 * 31 - len(gaps)


def test_actuals_are_unique_sorted_utc_and_plausible() -> None:
    a = load_actuals()
    assert a["start_time"].is_unique and a["start_time"].is_monotonic_increasing
    assert str(a["start_time"].dt.tz) == "UTC"
    assert a["actual"].between(0, 35_000).all()
    assert (a["start_time"].dt.minute % 30 == 0).all()


def test_forecasts_have_no_negative_horizons_or_duplicates() -> None:
    f = load_forecasts()
    assert (f["start_time"] >= f["publish_time"]).all()
    assert not f.duplicated(["publish_time", "start_time"]).any()
    assert f["forecast"].between(0, 35_000).all()


def test_every_january_target_hour_has_a_forecast_before_the_default_cutoff() -> None:
    latest = latest_forecasts(load_forecasts(), *JAN, time(9, 30))
    hourly = pd.Series(expected_half_hours(*JAN)).loc[lambda s: s.dt.minute == 0]
    assert set(latest["start_time"]) == set(hourly)
    # Late-December publishes are needed for 1 January targets.
    assert latest["publish_time"].min() < pd.Timestamp("2026-01-01", tz="UTC")


def test_quality_report_matches_snapshot() -> None:
    assert QUALITY["actual_rows"] == len(load_actuals())
    assert QUALITY["forecast_rows"] == len(load_forecasts())
