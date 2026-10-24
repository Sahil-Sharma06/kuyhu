"""OPTIONAL integration test against the live Elexon API.

Skipped by default (deselected by the `integration` marker). Run with:
    pytest -m integration
"""

from datetime import date

import pandas as pd
import pytest
import requests
from fetch_data import get

from app.data.loader import load_actuals, load_forecasts

pytestmark = pytest.mark.integration


def test_snapshot_matches_live_elexon_for_sample_values() -> None:
    with requests.Session() as s:
        live_actuals = pd.DataFrame(
            get(s, "FUELHH", {"settlementDateFrom": "2026-01-15", "settlementDateTo": "2026-01-15", "fuelType": "WIND"})
        )
        live_fc = pd.DataFrame(
            get(s, "WINDFOR", {"publishDateTimeFrom": "2026-01-14T09:30:00Z", "publishDateTimeTo": "2026-01-14T09:30:00Z"})
        )

    snap = load_actuals().set_index("start_time")["actual"]
    for row in live_actuals.head(5).itertuples():
        assert snap[pd.Timestamp(row.startTime)] == row.generation

    f = load_forecasts()
    snap_fc = f[f["publish_time"] == pd.Timestamp("2026-01-14T09:30Z")].set_index("start_time")["forecast"]
    live_fc = live_fc[pd.to_datetime(live_fc["startTime"]).dt.date >= date(2026, 1, 15)]
    for row in live_fc.head(5).itertuples():
        assert snap_fc[pd.Timestamp(row.startTime)] == row.generation
