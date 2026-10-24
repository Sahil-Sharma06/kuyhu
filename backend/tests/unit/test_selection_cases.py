"""Latest-forecast selection: spec cases on tiny hand-built fixtures."""

from datetime import date, time

import pandas as pd
import pytest

from app.services.selection import cutoff_utc, latest_forecasts

T = pd.Timestamp
JAN15 = date(2026, 1, 15)
CUT = time(9, 30)


def frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["publish_time", "start_time", "forecast"])
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    return df


def test_newer_forecast_after_cutoff_is_ignored_even_though_it_is_the_latest() -> None:
    df = frame(
        [
            ("2026-01-14T02:30Z", "2026-01-15T06:00Z", 10),
            ("2026-01-14T09:31Z", "2026-01-15T06:00Z", 20),
            ("2026-01-14T23:30Z", "2026-01-15T06:00Z", 30),
        ]
    )
    assert latest_forecasts(df, JAN15, JAN15, CUT)["forecast"].tolist() == [10]


def test_exactly_one_row_per_start_time() -> None:
    targets = ["2026-01-15T00:00Z", "2026-01-15T01:00Z", "2026-01-15T02:00Z"]
    pubs = ["2026-01-13T09:30Z", "2026-01-14T04:30Z", "2026-01-14T07:30Z", "2026-01-14T09:30Z"]
    df = frame([(p, t, i) for i, (p, t) in enumerate((p, t) for p in pubs for t in targets)])
    out = latest_forecasts(df, JAN15, JAN15, CUT)
    assert out["start_time"].is_unique
    assert len(out) == len(targets)
    assert (out["publish_time"] == T("2026-01-14T09:30Z")).all()


def test_missing_target_is_not_filled_from_a_later_forecast() -> None:
    df = frame(
        [
            ("2026-01-14T07:30Z", "2026-01-15T00:00Z", 1),
            ("2026-01-14T11:30Z", "2026-01-15T01:00Z", 2),  # only forecast for 01:00 is post-cutoff
        ]
    )
    out = latest_forecasts(df, JAN15, JAN15, CUT)
    assert out["start_time"].tolist() == [T("2026-01-15T00:00Z")]


@pytest.mark.parametrize(
    ("day", "cutoff", "expected"),
    [
        (date(2026, 1, 15), time(9, 30), "2026-01-14T09:30Z"),  # GMT
        (date(2026, 1, 15), time(17, 45), "2026-01-14T17:45Z"),  # custom time
        (date(2026, 1, 1), time(0, 0), "2025-12-31T00:00Z"),  # crosses the year boundary
        (date(2026, 3, 30), time(9, 30), "2026-03-29T08:30Z"),  # D-1 is the first BST day
        (date(2026, 10, 26), time(9, 30), "2026-10-25T09:30Z"),  # D-1 is the return to GMT
    ],
)
def test_cutoff_for_d_minus_1_in_london(day: date, cutoff: time, expected: str) -> None:
    assert cutoff_utc(day, cutoff) == T(expected)


def test_custom_cutoff_changes_selection() -> None:
    df = frame(
        [
            ("2026-01-14T07:30Z", "2026-01-15T12:00Z", 1),
            ("2026-01-14T15:30Z", "2026-01-15T12:00Z", 2),
        ]
    )
    assert latest_forecasts(df, JAN15, JAN15, time(9, 30))["forecast"].tolist() == [1]
    assert latest_forecasts(df, JAN15, JAN15, time(16, 0))["forecast"].tolist() == [2]


def test_only_negative_horizon_rows_yield_nothing() -> None:
    df = frame([("2026-01-15T12:00Z", "2026-01-15T00:00Z", 9)])
    assert latest_forecasts(df, JAN15, JAN15, time(23, 59)).empty
