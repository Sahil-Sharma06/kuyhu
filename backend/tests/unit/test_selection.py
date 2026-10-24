from datetime import date, time

import pandas as pd
import pytest

from app.services.selection import cutoff_utc, latest_forecasts, parse_cutoff

T = pd.Timestamp


def frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["publish_time", "start_time", "forecast"])
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    return df


JAN15 = date(2026, 1, 15)
CUT = time(9, 30)


def test_cutoff_is_previous_day_local_time_in_winter() -> None:
    assert cutoff_utc(JAN15, CUT) == T("2026-01-14T09:30Z")


def test_cutoff_respects_bst() -> None:
    # In summer London is UTC+1, so 09:30 local is 08:30 UTC.
    assert cutoff_utc(date(2026, 7, 1), CUT) == T("2026-06-30T08:30Z")


def test_picks_max_publish_time_before_cutoff() -> None:
    df = frame(
        [
            ("2026-01-14T04:30Z", "2026-01-15T12:00Z", 100),
            ("2026-01-14T07:30Z", "2026-01-15T12:00Z", 200),
            ("2026-01-14T11:30Z", "2026-01-15T12:00Z", 999),  # after cutoff: must be ignored
        ]
    )
    out = latest_forecasts(df, JAN15, JAN15, CUT)
    assert out["forecast"].tolist() == [200]
    assert out["publish_time"].iloc[0] == T("2026-01-14T07:30Z")
    assert out["horizon_h"].iloc[0] == pytest.approx(28.5)


def test_publish_exactly_at_cutoff_is_included_and_one_second_after_is_not() -> None:
    df = frame(
        [
            ("2026-01-14T09:30:00Z", "2026-01-15T12:00Z", 1),
            ("2026-01-14T09:30:01Z", "2026-01-15T12:00Z", 2),
        ]
    )
    assert latest_forecasts(df, JAN15, JAN15, CUT)["forecast"].tolist() == [1]


def test_target_without_any_pre_cutoff_forecast_is_omitted() -> None:
    df = frame([("2026-01-14T11:30Z", "2026-01-15T12:00Z", 5)])
    assert latest_forecasts(df, JAN15, JAN15, CUT).empty


def test_negative_horizon_is_excluded() -> None:
    # A late cutoff (23:59 on D-1) lets a forecast published after target times be considered;
    # rows whose target precedes their publish time must still be dropped.
    df = frame(
        [
            ("2026-01-15T05:00Z", "2026-01-15T01:00Z", 7),
            ("2026-01-14T09:00Z", "2026-01-15T01:00Z", 3),
        ]
    )
    out = latest_forecasts(df, JAN15, JAN15, time(23, 59))
    assert out["forecast"].tolist() == [3]
    assert (out["horizon_h"] >= 0).all()


def test_each_delivery_day_uses_its_own_cutoff() -> None:
    df = frame(
        [
            ("2026-01-14T09:30Z", "2026-01-15T12:00Z", 1),
            ("2026-01-15T09:30Z", "2026-01-15T12:00Z", 2),  # same target, published on D itself
            ("2026-01-15T09:30Z", "2026-01-16T12:00Z", 3),
        ]
    )
    out = latest_forecasts(df, JAN15, date(2026, 1, 16), CUT)
    assert out["forecast"].tolist() == [1, 3]


def test_delivery_day_uses_london_calendar_in_summer() -> None:
    # 2026-07-01T23:00Z is 00:00 BST on 2 July, so it belongs to delivery day 2 July.
    df = frame([("2026-07-01T08:00Z", "2026-07-01T23:00Z", 4)])
    assert latest_forecasts(df, date(2026, 7, 1), date(2026, 7, 1), CUT).empty
    out = latest_forecasts(df, date(2026, 7, 2), date(2026, 7, 2), CUT)
    assert out["delivery_day"].tolist() == [date(2026, 7, 2)]


@pytest.mark.parametrize("bad", ["930", "25:00", "09:61", "ab:cd"])
def test_parse_cutoff_rejects_bad_values(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_cutoff(bad)
