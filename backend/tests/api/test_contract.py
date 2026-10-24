"""API contract: schemas, validation errors, empty-data behaviour, CORS, headers and speed."""

import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.api import routes
from app.data.loader import load_actuals, load_forecasts
from app.main import app
from app.models import DecisionDay, GroupStat, HorizonStat, Meta, Metrics

client = TestClient(app)


@pytest.mark.parametrize(
    ("path", "params", "schema"),
    [
        ("/api/meta", {}, Meta),
        ("/api/forecast-vs-actual", {"date": "2026-01-10", "cutoff": "09:30"}, DecisionDay),
        ("/api/metrics", {"start": "2026-01-01", "end": "2026-01-31"}, Metrics),
        ("/api/error-by-hour", {}, list[GroupStat]),
        ("/api/error-by-horizon", {}, list[HorizonStat]),
    ],
)
def test_responses_validate_against_schema(path: str, params: dict, schema: type) -> None:
    resp = client.get(path, params=params)
    assert resp.status_code == 200
    TypeAdapter(schema).validate_python(resp.json(), strict=False)


def test_meta_reports_no_gaps_in_snapshot() -> None:
    assert client.get("/api/meta").json()["missing_half_hours"] == []


@pytest.mark.parametrize(
    ("path", "params", "fragment"),
    [
        ("/api/forecast-vs-actual", {"date": "2026-13-01"}, "date"),
        ("/api/forecast-vs-actual", {"date": "not-a-date"}, "date"),
        ("/api/forecast-vs-actual", {"date": "2026-02-01"}, "outside the supported delivery period"),
        ("/api/forecast-vs-actual", {"date": "2025-12-31"}, "outside the supported delivery period"),
        ("/api/forecast-vs-actual", {"date": "2026-01-10", "cutoff": "9.30"}, "cutoff"),
        ("/api/forecast-vs-actual", {"date": "2026-01-10", "cutoff": "24:00"}, "Invalid cutoff"),
        ("/api/forecast-vs-actual", {}, "date"),
        ("/api/metrics", {"start": "2026-01-20", "end": "2026-01-10"}, "must be on or before end"),
        ("/api/metrics", {"start": "2025-12-01"}, "outside the supported delivery period"),
        ("/api/error-by-hour", {"cutoff": "ab:cd"}, "cutoff"),
        ("/api/error-by-horizon", {"end": "2026-03-01"}, "outside the supported delivery period"),
    ],
)
def test_invalid_input_is_422_with_clear_message(path: str, params: dict, fragment: str) -> None:
    resp = client.get(path, params=params)
    assert resp.status_code == 422
    assert fragment in resp.text


@pytest.fixture
def snapshot_without_jan_10(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all data for London delivery day 2026-01-10 (UTC == London in January)."""
    day = pd.Timestamp("2026-01-10", tz="UTC")
    actuals = load_actuals()
    forecasts = load_forecasts()
    a = actuals[(actuals["start_time"] < day) | (actuals["start_time"] >= day + pd.Timedelta(days=1))]
    f = forecasts[(forecasts["start_time"] < day) | (forecasts["start_time"] >= day + pd.Timedelta(days=1))]
    monkeypatch.setattr(routes, "load_actuals", lambda: a)
    monkeypatch.setattr(routes, "load_forecasts", lambda: f)


@pytest.mark.usefixtures("snapshot_without_jan_10")
def test_day_without_data_returns_explicit_empty_result() -> None:
    resp = client.get("/api/forecast-vs-actual", params={"date": "2026-01-10"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["forecast"] == [] and body["actual"] == []
    assert body["summary"]["hours_covered"] == 0 and body["summary"]["mae_mw"] is None
    assert len(client.get("/api/meta").json()["missing_half_hours"]) == 48
    single = client.get("/api/metrics", params={"start": "2026-01-10", "end": "2026-01-10"}).json()
    assert single["summary"]["n"] == 0 and single["by_day"] == [] and single["horizon_range_h"] is None


def test_different_cutoffs_give_different_forecasts_for_same_day() -> None:
    a = client.get("/api/forecast-vs-actual", params={"date": "2026-01-20", "cutoff": "09:30"}).json()
    b = client.get("/api/forecast-vs-actual", params={"date": "2026-01-20", "cutoff": "03:00"}).json()
    assert {p["publish_time"] for p in a["forecast"]} != {p["publish_time"] for p in b["forecast"]}
    assert [p["forecast"] for p in a["forecast"]] != [p["forecast"] for p in b["forecast"]]


@pytest.mark.parametrize("path", ["/api/nope", "/nope", "/api/metrics/extra"])
def test_unknown_routes_return_json_404(path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "Not Found"}


def test_cors_allows_configured_origin_only() -> None:
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
    preflight = client.options("/api/metrics", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert preflight.status_code == 400


def test_mutating_methods_are_rejected() -> None:
    assert client.post("/api/metrics").status_code == 405


def test_security_headers_present() -> None:
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


@pytest.mark.parametrize("path", ["/api/metrics", "/api/error-by-hour", "/api/error-by-horizon", "/api/forecast-vs-actual?date=2026-01-31"])
def test_month_of_data_responds_quickly(path: str) -> None:
    client.get(path)  # warm the snapshot cache
    t0 = time.perf_counter()
    assert client.get(path).status_code == 200
    assert time.perf_counter() - t0 < 1.0
