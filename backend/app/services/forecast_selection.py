"""Forecast selection service.

Implements the decision-time-aware forecast selection logic:
For a given target period T and decision time D, select the latest
forecast published no later than D that targets period T.

This is the core analytical requirement: ensuring we reconstruct
what information was actually available when a procurement decision
was being made.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from app.schemas.models import SelectedForecast

logger = logging.getLogger(__name__)


def select_forecast_for_target(
    target_time: datetime,
    forecasts_df: pd.DataFrame,
    decision_time: datetime,
) -> tuple[float | None, datetime | None, bool, str | None]:
    """Select the latest eligible forecast for a target period.

    Args:
        target_time: The target generation period start (UTC).
        forecasts_df: DataFrame of all forecast records with columns:
            start_time, publish_time, generation_mw.
        decision_time: The procurement decision cutoff (UTC).

    Returns:
        Tuple of (generation_mw, publish_time, found, exclusion_reason).
    """
    if forecasts_df.empty:
        return None, None, False, "No forecast records available"

    # Filter to forecasts targeting this period
    target_forecasts = forecasts_df[forecasts_df["start_time"] == target_time]
    if target_forecasts.empty:
        return None, None, False, f"No forecast found targeting {target_time.isoformat()}"

    # Filter to forecasts published before or at the decision time
    eligible = target_forecasts[target_forecasts["publish_time"] <= decision_time]
    if eligible.empty:
        earliest = target_forecasts["publish_time"].min()
        return None, None, False, (
            f"All forecasts for this period were published after decision time "
            f"{decision_time.isoformat()}. Earliest available: {earliest.isoformat()}"
        )

    # Select the latest eligible publication
    latest_idx = eligible["publish_time"].idxmax()
    row = eligible.loc[latest_idx]

    return (
        float(row["generation_mw"]),
        row["publish_time"].to_pydatetime(),
        True,
        None,
    )


def build_evaluation_series(
    actuals_df: pd.DataFrame,
    forecasts_df: pd.DataFrame,
    decision_time: datetime,
    start_time: datetime,
    end_time: datetime,
) -> list[SelectedForecast]:
    """Build a complete evaluation series matching forecasts to actuals.

    For each hourly target period in the evaluation range, selects the
    latest eligible forecast and matches it with actual generation.

    Args:
        actuals_df: Normalized hourly actuals (start_time_hourly, generation_mw).
        forecasts_df: All forecast records (start_time, publish_time, generation_mw).
        decision_time: Procurement decision cutoff (UTC).
        start_time: Evaluation period start (UTC).
        end_time: Evaluation period end (UTC).

    Returns:
        List of SelectedForecast records.
    """
    results: list[SelectedForecast] = []

    # Build a lookup for actuals by hour
    actuals_lookup: dict[datetime, float] = {}
    if not actuals_df.empty:
        for _, row in actuals_df.iterrows():
            ts = row["start_time_hourly"]
            if isinstance(ts, pd.Timestamp):
                ts = ts.to_pydatetime()
            actuals_lookup[ts] = float(row["generation_mw"])

    # Get all unique target hours from forecasts that fall within the range
    if not forecasts_df.empty:
        target_mask = (forecasts_df["start_time"] >= start_time) & (forecasts_df["start_time"] < end_time)
        target_hours = sorted(forecasts_df.loc[target_mask, "start_time"].unique())
    else:
        target_hours = []

    # Also include hours from actuals that might not have forecasts
    for ts in actuals_lookup:
        if start_time <= ts < end_time and ts not in target_hours:
            target_hours.append(ts)
    target_hours = sorted(set(target_hours))

    for target in target_hours:
        if isinstance(target, pd.Timestamp):
            target = target.to_pydatetime()
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)

        # Select forecast
        fc_gen, fc_pub, fc_found, exclusion = select_forecast_for_target(
            target, forecasts_df, decision_time
        )

        # Match actual
        actual_gen = actuals_lookup.get(target)
        actual_available = actual_gen is not None

        # Calculate errors
        error_mw = None
        abs_error_mw = None
        pct_error = None
        if fc_found and fc_gen is not None and actual_available and actual_gen is not None:
            error_mw = fc_gen - actual_gen
            abs_error_mw = abs(error_mw)
            if actual_gen != 0:
                pct_error = (abs(error_mw) / actual_gen) * 100

        results.append(SelectedForecast(
            target_time=target,
            decision_time=decision_time,
            forecast_generation_mw=fc_gen,
            forecast_publish_time=fc_pub,
            actual_generation_mw=actual_gen,
            error_mw=round(error_mw, 2) if error_mw is not None else None,
            absolute_error_mw=round(abs_error_mw, 2) if abs_error_mw is not None else None,
            percentage_error=round(pct_error, 2) if pct_error is not None else None,
            forecast_available=fc_found,
            actual_available=actual_available,
            exclusion_reason=exclusion,
        ))

    logger.info(
        "Built evaluation series: %d periods, %d with forecast, %d with actual, %d fully matched",
        len(results),
        sum(1 for r in results if r.forecast_available),
        sum(1 for r in results if r.actual_available),
        sum(1 for r in results if r.forecast_available and r.actual_available),
    )
    return results

