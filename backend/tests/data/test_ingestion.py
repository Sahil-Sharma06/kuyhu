"""Ingestion script with a fake HTTP session: no network access."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import fetch_data
import pytest
import requests
from fetch_data import FetchError, build_snapshot, chunks, get


class FakeResponse:
    def __init__(self, status: int, payload: list[dict] | None = None) -> None:
        self.status_code = status
        self._payload = payload or []

    def json(self) -> list[dict]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


class FakeSession:
    """Serves synthetic FUELHH / WINDFOR rows for whatever window is requested, or scripted failures."""

    def __init__(self, script: list[FakeResponse | Exception] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: float) -> FakeResponse:
        self.calls.append((url.split("/")[-2], params))
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return FakeResponse(200, self._rows(url, params))

    @staticmethod
    def _rows(url: str, params: dict) -> list[dict]:
        if "FUELHH" in url:
            d0 = date.fromisoformat(params["settlementDateFrom"])
            d1 = date.fromisoformat(params["settlementDateTo"])
            t = datetime(d0.year, d0.month, d0.day)
            rows = []
            while t.date() <= d1:
                iso = t.strftime("%Y-%m-%dT%H:%M:%SZ")
                rows.append({"startTime": iso, "publishTime": iso, "fuelType": "WIND", "generation": 1000 + t.hour})
                rows.append({"startTime": iso, "publishTime": iso, "fuelType": "CCGT", "generation": 5})
                t += timedelta(minutes=30)
            return rows
        p0 = datetime.strptime(params["publishDateTimeFrom"], "%Y-%m-%dT%H:%M:%SZ")
        p1 = datetime.strptime(params["publishDateTimeTo"], "%Y-%m-%dT%H:%M:%SZ")
        rows, pub = [], p0.replace(minute=30)
        while pub <= p1:
            for h in range(-2, 40):
                start = pub.replace(minute=0) + timedelta(hours=h)
                rows.append(
                    {
                        "publishTime": pub.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "generation": 900 + h,
                    }
                )
            pub += timedelta(hours=6)
        return rows


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch_data.clock, "sleep", lambda _s: None)


def test_chunks_cover_range_contiguously_within_limit() -> None:
    start, end = datetime(2025, 12, 28), datetime(2026, 2, 1)
    windows = chunks(start, end)
    assert windows[0][0] == start and windows[-1][1] == end
    assert all(a[1] == b[0] for a, b in zip(windows, windows[1:], strict=False))
    assert all(b - a <= timedelta(days=fetch_data.CHUNK_DAYS) for a, b in windows)


def test_requests_are_chunked_and_windows_do_not_overlap(tmp_path: Path) -> None:
    session = FakeSession()
    build_snapshot(session, date(2026, 1, 1), date(2026, 1, 31), tmp_path)
    fuel = [p for ds, p in session.calls if ds == "FUELHH"]
    wind = [p for ds, p in session.calls if ds == "WINDFOR"]
    assert len(fuel) == 5 and len(wind) == 5  # 31 days and 35 days in 7-day chunks
    assert fuel[0]["settlementDateFrom"] == "2026-01-01" and fuel[-1]["settlementDateTo"] == "2026-01-31"
    for a, b in zip(fuel, fuel[1:], strict=False):
        assert date.fromisoformat(b["settlementDateFrom"]) == date.fromisoformat(a["settlementDateTo"]) + timedelta(days=1)
    assert wind[0]["publishDateTimeFrom"] == "2025-12-28T00:00:00Z"  # 4-day lookback for late-Dec publishes
    for a, b in zip(wind, wind[1:], strict=False):
        assert a["publishDateTimeTo"] < b["publishDateTimeFrom"]
    assert all(p["fuelType"] == "WIND" and p["format"] == "json" for p in fuel)


def test_ingestion_is_idempotent(tmp_path: Path) -> None:
    out1, out2 = tmp_path / "a", tmp_path / "b"
    r1 = build_snapshot(FakeSession(), date(2026, 1, 1), date(2026, 1, 31), out1)
    r2 = build_snapshot(FakeSession(), date(2026, 1, 1), date(2026, 1, 31), out2)
    assert r1 == r2
    for name in ("actuals.csv", "forecasts.csv", "quality.json"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes()
    # Re-running into the same directory leaves it byte-identical.
    before = {p.name: p.read_bytes() for p in out1.iterdir()}
    build_snapshot(FakeSession(), date(2026, 1, 1), date(2026, 1, 31), out1)
    assert before == {p.name: p.read_bytes() for p in out1.iterdir()}


def test_snapshot_output_is_cleaned(tmp_path: Path) -> None:
    report = build_snapshot(FakeSession(), date(2026, 1, 1), date(2026, 1, 2), tmp_path)
    assert report["actual_rows"] == 96 and report["missing_half_hours"] == []
    assert report["actuals_removed"]["non_wind"] == 96
    assert report["forecasts_removed"]["negative_horizon"] > 0
    first = (tmp_path / "actuals.csv").read_text().splitlines()[:2]
    assert first == ["start_time,generation", "2026-01-01T00:00:00Z,1000"]


def test_retries_timeouts_then_succeeds() -> None:
    session = FakeSession([requests.Timeout(), requests.ConnectionError(), FakeResponse(200, [{"x": 1}])])
    assert get(session, "FUELHH", {}) == [{"x": 1}]
    assert len(session.calls) == 3


def test_server_errors_exhaust_retries_with_clear_error() -> None:
    session = FakeSession([FakeResponse(503)] * fetch_data.RETRIES)
    with pytest.raises(FetchError, match=r"HTTP 503 after 3 attempts"):
        get(session, "WINDFOR", {"publishDateTimeFrom": "x"})
    assert len(session.calls) == fetch_data.RETRIES


def test_persistent_timeouts_raise_fetch_error() -> None:
    session = FakeSession([requests.Timeout()] * fetch_data.RETRIES)
    with pytest.raises(FetchError, match="Timeout"):
        get(session, "FUELHH", {})


def test_client_errors_fail_fast_without_retry() -> None:
    session = FakeSession([FakeResponse(400)])
    with pytest.raises(FetchError, match="400"):
        get(session, "FUELHH", {"settlementDateFrom": "bad"})
    assert len(session.calls) == 1
