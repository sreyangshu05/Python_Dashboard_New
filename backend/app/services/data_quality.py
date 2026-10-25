"""Data quality analysis service."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from app.schemas.models import DataQualityStats, SelectedForecast

logger = logging.getLogger(__name__)


def compute_data_quality(
    records: list[SelectedForecast],
    actuals_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    quality: DataQualityStats,
) -> DataQualityStats:
    """Compute comprehensive data quality statistics.

    Args:
        records: Evaluation series records.
        actuals_df: Normalized actuals DataFrame.
        forecasts_df: Normalized forecasts DataFrame.
        quality: Initial DataQualityStats (already partially populated).

    Returns:
        Updated DataQualityStats.
    """
    quality.matched_periods = sum(
        1 for r in records if r.forecast_available and r.actual_available
    )
    quality.periods_missing_actual = sum(
        1 for r in records if not r.actual_available
    )
    quality.periods_missing_forecast = sum(
        1 for r in records if not r.forecast_available
    )
    quality.forecasts_excluded_after_cutoff = sum(
        1 for r in records
        if not r.forecast_available and r.exclusion_reason and "after decision time" in r.exclusion_reason
    )

    if records:
        target_times = [r.target_time for r in records]
        quality.first_target_time = min(target_times)
        quality.last_target_time = max(target_times)

    return quality

