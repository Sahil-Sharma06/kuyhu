"""Endpoint tests against the bundled January 2026 snapshot."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta() -> None:
    body = client.get("/api/meta").json()
    assert body["start"] == "2026-01-01"
    assert body["end"] == "2026-01-31"
    assert body["default_cutoff"] == "09:30"


def test_forecast_vs_actual_never_uses_post_cutoff_forecasts() -> None:
    body = client.get("/api/forecast-vs-actual", params={"date": "2026-01-15", "cutoff": "09:30"}).json()
    assert body["cutoff_utc"] == "2026-01-14T09:30:00+00:00"
    assert len(body["actual"]) == 48
    assert body["forecast"], "expected hourly forecasts"
    assert all(p["publish_time"] <= "2026-01-14T09:30:00+00:00" for p in body["forecast"])
    assert all(p["horizon_h"] >= 0 for p in body["forecast"])
    assert body["risk_buffer_mw"] >= 0
    assert all(p["lower_bound"] == pytest.approx(p["forecast"] - body["risk_buffer_mw"]) for p in body["forecast"])


def test_earlier_cutoff_uses_older_forecast() -> None:
    late = client.get("/api/forecast-vs-actual", params={"date": "2026-01-15", "cutoff": "09:30"}).json()
    early = client.get("/api/forecast-vs-actual", params={"date": "2026-01-15", "cutoff": "05:00"}).json()
    assert early["summary"]["latest_publish_time"] < late["summary"]["latest_publish_time"]


@pytest.mark.parametrize("cutoff", ["930", "25:00", "x"])
def test_bad_cutoff_is_422(cutoff: str) -> None:
    assert client.get("/api/forecast-vs-actual", params={"date": "2026-01-15", "cutoff": cutoff}).status_code == 422


def test_date_out_of_range_is_422() -> None:
    # Spec: dates outside the January 2026 scope are a validation error, not a missing resource.
    assert client.get("/api/forecast-vs-actual", params={"date": "2025-06-01"}).status_code == 422


def test_metrics_shape_and_sanity() -> None:
    body = client.get("/api/metrics").json()
    s = body["summary"]
    assert s["n"] > 600  # ~24 hourly points x 31 days
    assert 0 < s["mae"] <= s["rmse"]
    assert s["p50"] <= s["p90"] <= s["p95"] <= s["p99"]
    assert len(body["by_day"]) == 31
    assert sum(b["count"] for b in body["histogram"]) == s["n"]
    assert body["horizon_range_h"][0] >= 0


def test_metrics_reversed_range_is_422() -> None:
    assert client.get("/api/metrics", params={"start": "2026-01-20", "end": "2026-01-10"}).status_code == 422


def test_error_by_hour_has_24_hours() -> None:
    rows = client.get("/api/error-by-hour").json()
    assert [r["key"] for r in rows] == list(range(24))


def test_error_by_horizon_is_non_negative_and_ordered() -> None:
    rows = client.get("/api/error-by-horizon").json()
    keys = [r["key"] for r in rows]
    assert keys == sorted(keys) and keys[0] >= 0
    assert rows[0]["label"] == f"{keys[0]}-{keys[0] + 6}h"
