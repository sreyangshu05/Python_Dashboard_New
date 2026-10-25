"""Forecast accuracy metrics calculation.

Implements MAE, RMSE, MAPE, MBE, and supplementary metrics.

Error convention: error = forecast - actual
  Positive error → overforecasting
  Negative error → underforecasting

All metrics operate on valid matched observations only (both forecast
and actual are finite). MAPE additionally excludes zero-actual observations.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np

from app.schemas.models import AccuracyMetrics, SelectedForecast

logger = logging.getLogger(__name__)


def calculate_accuracy_metrics(
    records: list[SelectedForecast],
    evaluation_start: str,
    evaluation_end: str,
    decision_hour_utc: int,
) -> AccuracyMetrics:
    """Calculate forecast accuracy metrics from evaluation records.

    Args:
        records: List of SelectedForecast records.
        evaluation_start: Evaluation period start date string.
        evaluation_end: Evaluation period end date string.
        decision_hour_utc: Decision cutoff hour (UTC).

    Returns:
        AccuracyMetrics with all calculated values.
    """
    from datetime import datetime, timezone

    # Extract valid pairs (both forecast and actual are available and finite)
    valid_pairs: list[tuple[float, float]] = []
    for r in records:
        if (
            r.forecast_available
            and r.actual_available
            and r.forecast_generation_mw is not None
            and r.actual_generation_mw is not None
            and math.isfinite(r.forecast_generation_mw)
            and math.isfinite(r.actual_generation_mw)
        ):
            valid_pairs.append((r.forecast_generation_mw, r.actual_generation_mw))

    total_observations = len(records)
    valid_count = len(valid_pairs)

    if valid_count == 0:
        return AccuracyMetrics(
            mae_mw=None,
            rmse_mw=None,
            mape_percent=None,
            mbe_mw=None,
            median_ae_mw=None,
            error_std_mw=None,
            total_observations=total_observations,
            valid_observations=0,
            mape_eligible_observations=0,
            mape_excluded_zero_actual=0,
            evaluation_start=datetime.fromisoformat(evaluation_start).replace(tzinfo=timezone.utc),
            evaluation_end=datetime.fromisoformat(evaluation_end).replace(tzinfo=timezone.utc),
            decision_hour_utc=decision_hour_utc,
        )

    forecasts = np.array([p[0] for p in valid_pairs])
    actuals = np.array([p[1] for p in valid_pairs])

    # Signed errors: error = forecast - actual
    errors = forecasts - actuals
    abs_errors = np.abs(errors)

    # MAE
    mae = float(np.mean(abs_errors))

    # RMSE
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MBE
    mbe = float(np.mean(errors))

    # Median Absolute Error
    median_ae = float(np.median(abs_errors))

    # Error standard deviation
    error_std = float(np.std(errors, ddof=1)) if valid_count > 1 else None

    # MAPE: exclude zero-actual observations
    mape_mask = actuals != 0
    mape_eligible = int(np.sum(mape_mask))
    mape_excluded = valid_count - mape_eligible

    mape: Optional[float] = None
    if mape_eligible > 0:
        mape = float(np.mean(np.abs(errors[mape_mask] / actuals[mape_mask])) * 100)

    return AccuracyMetrics(
        mae_mw=round(mae, 2),
        rmse_mw=round(rmse, 2),
        mape_percent=round(mape, 2) if mape is not None else None,
        mbe_mw=round(mbe, 2),
        median_ae_mw=round(median_ae, 2),
        error_std_mw=round(error_std, 2) if error_std is not None else None,
        total_observations=total_observations,
        valid_observations=valid_count,
        mape_eligible_observations=mape_eligible,
        mape_excluded_zero_actual=mape_excluded,
        evaluation_start=datetime.fromisoformat(evaluation_start).replace(tzinfo=timezone.utc),
        evaluation_end=datetime.fromisoformat(evaluation_end).replace(tzinfo=timezone.utc),
        decision_hour_utc=decision_hour_utc,
    )


def calculate_daily_metrics(records: list[SelectedForecast]) -> list[dict]:
    """Calculate daily aggregated error statistics.

    Returns:
        List of dicts with date, mae, rmse, mbe, count.
    """
    from collections import defaultdict

    daily: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in records:
        if (
            r.forecast_available
            and r.actual_available
            and r.forecast_generation_mw is not None
            and r.actual_generation_mw is not None
            and math.isfinite(r.forecast_generation_mw)
            and math.isfinite(r.actual_generation_mw)
        ):
            day = r.target_time.strftime("%Y-%m-%d")
            daily[day].append((r.forecast_generation_mw, r.actual_generation_mw))

    results = []
    for day in sorted(daily.keys()):
        pairs = daily[day]
        fc = np.array([p[0] for p in pairs])
        ac = np.array([p[1] for p in pairs])
        errors = fc - ac
        results.append({
            "date": day,
            "mae_mw": round(float(np.mean(np.abs(errors))), 2),
            "rmse_mw": round(float(np.sqrt(np.mean(errors ** 2))), 2),
            "mbe_mw": round(float(np.mean(errors)), 2),
            "count": len(pairs),
        })
    return results


def calculate_hourly_metrics(records: list[SelectedForecast]) -> list[dict]:
    """Calculate error statistics grouped by hour of day (UTC).

    Returns:
        List of dicts with hour, mae, mbe, count.
    """
    from collections import defaultdict

    hourly: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for r in records:
        if (
            r.forecast_available
            and r.actual_available
            and r.forecast_generation_mw is not None
            and r.actual_generation_mw is not None
            and math.isfinite(r.forecast_generation_mw)
            and math.isfinite(r.actual_generation_mw)
        ):
            hour = r.target_time.hour
            hourly[hour].append((r.forecast_generation_mw, r.actual_generation_mw))

    results = []
    for hour in range(24):
        if hour in hourly:
            pairs = hourly[hour]
            fc = np.array([p[0] for p in pairs])
            ac = np.array([p[1] for p in pairs])
            errors = fc - ac
            results.append({
                "hour": hour,
                "mae_mw": round(float(np.mean(np.abs(errors))), 2),
                "mbe_mw": round(float(np.mean(errors)), 2),
                "count": len(pairs),
            })
    return results


def calculate_error_distribution(records: list[SelectedForecast]) -> list[dict]:
    """Calculate error distribution histogram.

    Returns:
        List of dicts with bin_start, bin_end, count.
    """
    errors = []
    for r in records:
        if r.error_mw is not None and math.isfinite(r.error_mw):
            errors.append(r.error_mw)

    if not errors:
        return []

    errors_arr = np.array(errors)
    # Determine bin range
    min_err = float(np.min(errors_arr))
    max_err = float(np.max(errors_arr))

    # Use roughly 20 bins
    n_bins = min(20, max(5, len(errors) // 5))
    bin_edges = np.linspace(min_err, max_err, n_bins + 1)

    counts, edges = np.histogram(errors_arr, bins=bin_edges)
    result = []
    for i in range(len(counts)):
        result.append({
            "bin_start": round(float(edges[i]), 1),
            "bin_end": round(float(edges[i + 1]), 1),
            "count": int(counts[i]),
        })
    return result

