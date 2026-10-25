"""Data normalization for FUELHH and WINDFOR datasets.

Handles timestamp normalization, deduplication, resolution alignment
(half-hourly actuals → hourly to match forecasts), and data quality tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from app.schemas.models import DataQualityStats

logger = logging.getLogger(__name__)


def normalize_timestamp(ts_str: str | datetime) -> datetime:
    """Parse and normalize a timestamp to timezone-aware UTC.

    Args:
        ts_str: ISO 8601 timestamp string or datetime object.

    Returns:
        Timezone-aware UTC datetime.
    """
    if isinstance(ts_str, datetime):
        if ts_str.tzinfo is None:
            return ts_str.replace(tzinfo=timezone.utc)
        return ts_str.astimezone(timezone.utc)

    if isinstance(ts_str, str):
        # Handle Z suffix
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    raise ValueError(f"Cannot normalize timestamp: {ts_str}")


def normalize_actuals(raw_records: list[dict], quality: DataQualityStats) -> pd.DataFrame:
    """Normalize FUELHH WIND records into hourly periods.

    FUELHH provides half-hourly settlement periods. Since WINDFOR forecasts are
    hourly, we aggregate pairs of half-hourly actuals into hourly averages.

    The hourly period starting at time T covers actuals for settlement periods
    starting at T and T+30min.

    Args:
        raw_records: List of FUELHH raw records.
        quality: DataQualityStats object to update.

    Returns:
        DataFrame with columns: start_time_hourly, generation_mw, sp_count
    """
    quality.actual_records_retrieved = len(raw_records)

    if not raw_records:
        return pd.DataFrame(columns=["start_time_hourly", "generation_mw", "sp_count"])

    df = pd.DataFrame(raw_records)

    # Normalize timestamps
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)

    # Filter to WIND only (should already be filtered, but defensive)
    df = df[df["fuelType"] == "WIND"].copy()

    # Drop records with null generation
    null_count = df["generation"].isna().sum()
    if null_count > 0:
        logger.warning("Dropping %d FUELHH records with null generation", null_count)
    df = df.dropna(subset=["generation"])

    # Deduplicate: keep the latest publishTime for each startTime
    original_count = len(df)
    df = df.sort_values("publishTime").drop_duplicates(subset=["startTime"], keep="last")
    quality.duplicate_actuals_removed = original_count - len(df)

    if df.empty:
        return pd.DataFrame(columns=["start_time_hourly", "generation_mw", "sp_count"])

    # Aggregate half-hourly to hourly: floor each startTime to the hour
    df["start_time_hourly"] = df["startTime"].dt.floor("h")

    # Group by hour: average generation, count settlement periods
    hourly = (
        df.groupby("start_time_hourly")
        .agg(
            generation_mw=("generation", "mean"),
            sp_count=("generation", "count"),
        )
        .reset_index()
    )

    logger.info(
        "Normalized %d half-hourly actuals into %d hourly periods",
        len(df), len(hourly),
    )
    return hourly


def normalize_forecasts(raw_records: list[dict], quality: DataQualityStats) -> pd.DataFrame:
    """Normalize WINDFOR records.

    Args:
        raw_records: List of WINDFOR raw records.
        quality: DataQualityStats to update.

    Returns:
        DataFrame with columns: start_time, publish_time, generation_mw
    """
    quality.forecast_records_retrieved = len(raw_records)

    if not raw_records:
        return pd.DataFrame(columns=["start_time", "publish_time", "generation_mw"])

    df = pd.DataFrame(raw_records)

    # Normalize timestamps
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)

    # Drop records with null generation
    null_count = df["generation"].isna().sum()
    if null_count > 0:
        logger.warning("Dropping %d WINDFOR records with null generation", null_count)
    df = df.dropna(subset=["generation"])

    # Track unique publish times
    quality.unique_publish_times = df["publishTime"].nunique()
    if not df.empty:
        quality.first_publish_time = df["publishTime"].min().to_pydatetime()
        quality.last_publish_time = df["publishTime"].max().to_pydatetime()

    # Rename for internal use
    df = df.rename(columns={
        "startTime": "start_time",
        "publishTime": "publish_time",
        "generation": "generation_mw",
    })

    # Note: We keep ALL forecast revisions (duplicates by start_time are expected
    # and necessary for historical forecast selection)
    logger.info(
        "Normalized %d forecast records (%d unique publish times)",
        len(df), quality.unique_publish_times,
    )
    return df[["start_time", "publish_time", "generation_mw"]]

