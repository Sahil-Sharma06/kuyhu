"""Load the bundled CSV snapshot written by scripts/fetch_data.py."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@lru_cache(maxsize=1)
def load_actuals() -> pd.DataFrame:
    """Half-hourly wind outturn: columns start_time (UTC), actual (MW)."""
    df = pd.read_csv(DATA_DIR / "actuals.csv")
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    return df.rename(columns={"generation": "actual"})


@lru_cache(maxsize=1)
def load_forecasts() -> pd.DataFrame:
    """All forecast vintages: columns publish_time, start_time (UTC), forecast (MW)."""
    df = pd.read_csv(DATA_DIR / "forecasts.csv")
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    return df.rename(columns={"generation": "forecast"})
