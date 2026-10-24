"""Data cleaning on raw Elexon-shaped rows."""

from datetime import date

import pandas as pd

from app.data.cleaning import (
    MAX_PLAUSIBLE_MW,
    clean_actuals,
    clean_forecasts,
    expected_half_hours,
    implausible,
    missing_half_hours,
    to_utc_iso,
)
from app.services.selection import delivery_day_of


def raw_actual(start: str, gen: float, fuel: str = "WIND", pub: str | None = None) -> dict:
    return {"startTime": start, "publishTime": pub or start, "fuelType": fuel, "generation": gen}


def test_duplicate_actuals_deduplicated_deterministically() -> None:
    rows = [
        raw_actual("2026-01-01T00:00:00Z", 100, pub="2026-01-01T00:30:00Z"),
        raw_actual("2026-01-01T00:00:00Z", 120, pub="2026-01-01T01:00:00Z"),  # later publish wins
        raw_actual("2026-01-01T00:30:00Z", 50),
        raw_actual("2026-01-01T00:30:00Z", 40),  # same publish time: tie broken by value
    ]
    results = [clean_actuals(pd.DataFrame(order))[0] for order in (rows, rows[::-1], rows[1::2] + rows[::2])]
    for df in results:
        assert df["generation"].tolist() == [120, 50]
        pd.testing.assert_frame_equal(df, results[0])
    assert clean_actuals(pd.DataFrame(rows))[1]["duplicates"] == 2


def test_non_wind_fuel_types_filtered() -> None:
    df, report = clean_actuals(pd.DataFrame([raw_actual("2026-01-01T00:00:00Z", 1), raw_actual("2026-01-01T00:00:00Z", 999, fuel="CCGT")]))
    assert df["generation"].tolist() == [1]
    assert report["non_wind"] == 1


def test_missing_values_dropped() -> None:
    df, report = clean_actuals(pd.DataFrame([raw_actual("2026-01-01T00:00:00Z", None), raw_actual("2026-01-01T00:30:00Z", 5)]))
    assert len(df) == 1 and report["missing_value"] == 1


def test_implausible_values_flagged_and_removed() -> None:
    assert implausible(pd.Series([-1.0, 0.0, 15_000.0, MAX_PLAUSIBLE_MW, MAX_PLAUSIBLE_MW + 1])).tolist() == [
        True,
        False,
        False,
        False,
        True,
    ]
    df, report = clean_actuals(
        pd.DataFrame(
            [raw_actual("2026-01-01T00:00:00Z", -5), raw_actual("2026-01-01T00:30:00Z", 99_999), raw_actual("2026-01-01T01:00:00Z", 8)]
        )
    )
    assert df["generation"].tolist() == [8] and report["implausible"] == 2


def test_missing_half_hours_detected() -> None:
    expected = expected_half_hours(date(2026, 1, 1), date(2026, 1, 1))
    present = pd.Series(expected.delete([0, 10]))
    gaps = missing_half_hours(present, date(2026, 1, 1), date(2026, 1, 1))
    assert gaps == [pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-01T05:00Z")]


def test_expected_half_hours_handles_dst_days() -> None:
    assert len(expected_half_hours(date(2026, 1, 15), date(2026, 1, 15))) == 48
    assert len(expected_half_hours(date(2026, 3, 29), date(2026, 3, 29))) == 46  # clocks go forward
    assert len(expected_half_hours(date(2026, 10, 25), date(2026, 10, 25))) == 50  # clocks go back


def test_utc_storage_and_london_rendering() -> None:
    df, _ = clean_actuals(pd.DataFrame([raw_actual("2026-07-01T23:00:00Z", 1)]))
    assert str(df["start_time"].dt.tz) == "UTC"
    assert to_utc_iso(df["start_time"]).tolist() == ["2026-07-01T23:00:00Z"]
    # 23:00 UTC in July is 00:00 BST, i.e. the London delivery day 2 July.
    assert delivery_day_of(df["start_time"]).tolist() == [date(2026, 7, 2)]


def test_forecast_cleaning_drops_negative_horizon_and_duplicates() -> None:
    raw = pd.DataFrame(
        [
            {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T09:30:00Z", "generation": 1},
            {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T09:30:00Z", "generation": 1},
            {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-15T02:30:00Z", "generation": 2},
            {"startTime": "2026-03-01T00:00:00Z", "publishTime": "2026-02-28T02:30:00Z", "generation": 3},  # out of window
        ]
    )
    df, report = clean_forecasts(raw, date(2026, 1, 1), date(2026, 1, 31))
    assert df["generation"].tolist() == [1]
    assert report["negative_horizon"] == 1 and report["duplicates"] == 1
