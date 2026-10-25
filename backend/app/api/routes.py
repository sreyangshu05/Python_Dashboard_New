"""WindScope UK API routes."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.models import (
    AccuracyResponse,
    DataQualityStats,
    ForecastSeriesResponse,
    HealthResponse,
    OverviewResponse,
    SelectedForecast,
)
from app.services.accuracy_metrics import (
    calculate_accuracy_metrics,
    calculate_daily_metrics,
    calculate_error_distribution,
    calculate_hourly_metrics,
)
from app.services.data_normalization import normalize_actuals, normalize_forecasts
from app.services.data_quality import compute_data_quality
from app.services.elexon_client import ElexonClient, ElexonAPIError
from app.services.forecast_selection import build_evaluation_series

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Shared client and cache
_client = ElexonClient()
_cache: dict[str, tuple[datetime, object]] = {}


def _cache_key(prefix: str, start: str, end: str, decision_hour: int) -> str:
    return f"{prefix}:{start}:{end}:{decision_hour}"


def _get_cached(key: str) -> object | None:
    if key in _cache:
        cached_time, data = _cache[key]
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if age < settings.CACHE_TTL_SECONDS:
            logger.info("Cache hit for %s (age: %.0fs)", key, age)
            return data
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data: object) -> None:
    _cache[key] = (datetime.now(timezone.utc), data)


def _fetch_and_process(
    eval_start: str,
    eval_end: str,
    decision_hour: int,
) -> tuple[list[SelectedForecast], DataQualityStats]:
    """Fetch data from Elexon, normalize, select forecasts, and build evaluation series.

    Decision-time policy:
    For each day in the evaluation period, the decision time is set to
    decision_hour UTC on that day. The decision is for the NEXT day's generation.
    This means for a day-ahead decision made at e.g. 09:00 UTC on Jan 5,
    we evaluate forecasts targeting Jan 6 that were published by 09:00 UTC on Jan 5.

    To simplify for the first version: we use a single decision cutoff of
    decision_hour UTC on the last day of the evaluation period. This evaluates
    which forecasts were available for the target periods using the latest
    decision point in the month.

    A more thorough implementation would iterate each day and select per-day.
    """
    cache_key = _cache_key("eval", eval_start, eval_end, decision_hour)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached  # type: ignore

    quality = DataQualityStats()

    start_dt = datetime.fromisoformat(eval_start).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(eval_end).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

    # For actuals: we need FUELHH published during the evaluation period
    # FUELHH publishes shortly after each settlement period
    # So we need publishDateTime covering the eval period
    actual_publish_from = start_dt
    actual_publish_to = end_dt + timedelta(days=1)

    # For forecasts: we need WINDFOR published BEFORE or during the period
    # Forecasts can be published days before their target period
    # We need forecasts published from slightly before the eval start
    forecast_publish_from = start_dt - timedelta(days=3)  # forecasts may be published 2-3 days ahead
    forecast_publish_to = end_dt + timedelta(days=1)

    try:
        raw_actuals = _client.fetch_actual_wind_generation(actual_publish_from, actual_publish_to)
    except ElexonAPIError as e:
        logger.error("Failed to fetch actuals: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch actual generation data: {e}")

    try:
        raw_forecasts = _client.fetch_wind_forecasts(forecast_publish_from, forecast_publish_to)
    except ElexonAPIError as e:
        logger.error("Failed to fetch forecasts: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch forecast data: {e}")

    actuals_df = normalize_actuals(raw_actuals, quality)
    forecasts_df = normalize_forecasts(raw_forecasts, quality)

    quality.last_successful_fetch = _client.last_fetch_time

    # Build per-day decision times and aggregate results
    # For day-ahead: decision on day D at decision_hour covers targets on day D+1
    # But for simplicity and to show all data in the eval period, we use a
    # rolling approach: for each target hour, the decision time is
    # decision_hour on the day before the target.
    all_records: list[SelectedForecast] = []

    if not forecasts_df.empty:
        # Get unique target dates within the eval period
        target_dates = set()
        for st in forecasts_df["start_time"]:
            dt = st.to_pydatetime() if hasattr(st, "to_pydatetime") else st
            if start_dt <= dt <= end_dt:
                target_dates.add(dt.date())

        # Also add dates from actuals
        if not actuals_df.empty:
            for st in actuals_df["start_time_hourly"]:
                dt = st.to_pydatetime() if hasattr(st, "to_pydatetime") else st
                if start_dt <= dt <= end_dt:
                    target_dates.add(dt.date())

        # For each target date, the decision was made the day before at decision_hour
        for target_date in sorted(target_dates):
            decision_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                decision_hour, 0, 0, tzinfo=timezone.utc
            ) - timedelta(days=1)

            day_start = datetime(
                target_date.year, target_date.month, target_date.day,
                0, 0, 0, tzinfo=timezone.utc
            )
            day_end = day_start + timedelta(days=1)

            day_records = build_evaluation_series(
                actuals_df, forecasts_df, decision_dt, day_start, day_end
            )
            all_records.extend(day_records)

    quality = compute_data_quality(all_records, actuals_df, forecasts_df, quality)

    result = (all_records, quality)
    _set_cache(cache_key, result)
    return result


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Service health check."""
    return HealthResponse(
        elexon_api_url=settings.ELEXON_BASE_URL,
        evaluation_period=f"{settings.EVALUATION_START} to {settings.EVALUATION_END}",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    start: str = Query(default=None, description="Evaluation start date (YYYY-MM-DD)"),
    end: str = Query(default=None, description="Evaluation end date (YYYY-MM-DD)"),
    decision_hour: int = Query(default=None, description="Decision cutoff hour (UTC, 0-23)"),
):
    """Dashboard overview with latest forecast, metrics, and data quality."""
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    d_hour = decision_hour if decision_hour is not None else settings.DEFAULT_DECISION_HOUR_UTC

    try:
        records, quality = _fetch_and_process(eval_start, eval_end, d_hour)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing overview: %s", e)
        return OverviewResponse(
            evaluation_start=eval_start,
            evaluation_end=eval_end,
            decision_hour_utc=d_hour,
            data_quality=DataQualityStats(),
            error_message=str(e),
        )

    # Find latest fully matched record
    latest_forecast = None
    for r in reversed(records):
        if r.forecast_available and r.actual_available:
            latest_forecast = r
            break

    # Calculate metrics
    metrics = calculate_accuracy_metrics(records, eval_start, eval_end, d_hour)

    return OverviewResponse(
        evaluation_start=eval_start,
        evaluation_end=eval_end,
        decision_hour_utc=d_hour,
        latest_forecast=latest_forecast,
        metrics=metrics,
        data_quality=quality,
        last_successful_fetch=quality.last_successful_fetch,
    )


@router.get("/forecasts", response_model=ForecastSeriesResponse)
def get_forecasts(
    start: str = Query(default=None, description="Evaluation start date (YYYY-MM-DD)"),
    end: str = Query(default=None, description="Evaluation end date (YYYY-MM-DD)"),
    decision_hour: int = Query(default=None, description="Decision cutoff hour (UTC, 0-23)"),
):
    """Forecast vs actual time series for the evaluation period."""
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    d_hour = decision_hour if decision_hour is not None else settings.DEFAULT_DECISION_HOUR_UTC

    records, quality = _fetch_and_process(eval_start, eval_end, d_hour)

    return ForecastSeriesResponse(
        records=records,
        total_records=len(records),
        evaluation_start=eval_start,
        evaluation_end=eval_end,
        decision_hour_utc=d_hour,
        data_quality=quality,
    )


@router.get("/accuracy", response_model=AccuracyResponse)
def get_accuracy(
    start: str = Query(default=None, description="Evaluation start date (YYYY-MM-DD)"),
    end: str = Query(default=None, description="Evaluation end date (YYYY-MM-DD)"),
    decision_hour: int = Query(default=None, description="Decision cutoff hour (UTC, 0-23)"),
):
    """Forecast accuracy analysis with metrics and distributions."""
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    d_hour = decision_hour if decision_hour is not None else settings.DEFAULT_DECISION_HOUR_UTC

    records, quality = _fetch_and_process(eval_start, eval_end, d_hour)
    metrics = calculate_accuracy_metrics(records, eval_start, eval_end, d_hour)
    daily = calculate_daily_metrics(records)
    hourly = calculate_hourly_metrics(records)
    error_dist = calculate_error_distribution(records)

    return AccuracyResponse(
        metrics=metrics,
        daily_metrics=daily,
        hourly_metrics=hourly,
        error_distribution=error_dist,
        data_quality=quality,
    )


@router.get("/data-quality")
def get_data_quality(
    start: str = Query(default=None, description="Evaluation start date (YYYY-MM-DD)"),
    end: str = Query(default=None, description="Evaluation end date (YYYY-MM-DD)"),
    decision_hour: int = Query(default=None, description="Decision cutoff hour (UTC, 0-23)"),
):
    """Data quality statistics."""
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    d_hour = decision_hour if decision_hour is not None else settings.DEFAULT_DECISION_HOUR_UTC

    records, quality = _fetch_and_process(eval_start, eval_end, d_hour)
    return quality


@router.get("/export.csv")
def export_csv(
    start: str = Query(default=None, description="Evaluation start date (YYYY-MM-DD)"),
    end: str = Query(default=None, description="Evaluation end date (YYYY-MM-DD)"),
    decision_hour: int = Query(default=None, description="Decision cutoff hour (UTC, 0-23)"),
):
    """Export evaluation data as CSV.

    Timestamps are in UTC (ISO 8601 format).
    Error convention: error = forecast - actual.
    """
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    d_hour = decision_hour if decision_hour is not None else settings.DEFAULT_DECISION_HOUR_UTC

    records, _ = _fetch_and_process(eval_start, eval_end, d_hour)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "target_time_utc",
        "decision_time_utc",
        "forecast_generation_mw",
        "forecast_publish_time_utc",
        "actual_generation_mw",
        "error_mw",
        "absolute_error_mw",
        "percentage_error",
        "forecast_available",
        "actual_available",
        "exclusion_reason",
    ])

    for r in records:
        writer.writerow([
            r.target_time.isoformat(),
            r.decision_time.isoformat(),
            r.forecast_generation_mw if r.forecast_generation_mw is not None else "",
            r.forecast_publish_time.isoformat() if r.forecast_publish_time else "",
            r.actual_generation_mw if r.actual_generation_mw is not None else "",
            r.error_mw if r.error_mw is not None else "",
            r.absolute_error_mw if r.absolute_error_mw is not None else "",
            r.percentage_error if r.percentage_error is not None else "",
            r.forecast_available,
            r.actual_available,
            r.exclusion_reason or "",
        ])

    output.seek(0)
    filename = f"windscope_uk_{eval_start}_to_{eval_end}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

