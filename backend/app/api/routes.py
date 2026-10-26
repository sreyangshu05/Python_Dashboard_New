"""WindScope UK API routes."""

from __future__ import annotations

import csv
import io
import logging
import sqlite3
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

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
from app.services.forecast_archive import ForecastRevisionArchive
from app.services.forecast_selection import build_evaluation_series

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Shared client and cache
_client = ElexonClient()
_cache: dict[str, tuple[datetime, object]] = {}
_forecast_archive = ForecastRevisionArchive(settings.WINDFOR_ARCHIVE_PATH)


def _cache_key(prefix: str, start: str, end: str, decision_hour: int) -> str:
    return f"{prefix}:{start}:{end}:{decision_hour}"


def _resolve_filters(
    start: str | None,
    end: str | None,
    decision_hour: int | None,
) -> tuple[str, str, int]:
    eval_start = start or settings.EVALUATION_START
    eval_end = end or settings.EVALUATION_END
    resolved_hour = (
        decision_hour
        if decision_hour is not None
        else settings.DEFAULT_DECISION_HOUR_UTC
    )

    try:
        start_date = datetime.strptime(eval_start, "%Y-%m-%d").date()
        end_date = datetime.strptime(eval_end, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="start and end must be valid dates in YYYY-MM-DD format",
        ) from exc

    if start_date.isoformat() != eval_start or end_date.isoformat() != eval_end:
        raise HTTPException(
            status_code=422,
            detail="start and end must use zero-padded YYYY-MM-DD format",
        )
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    if not 0 <= resolved_hour <= 23:
        raise HTTPException(status_code=422, detail="decision_hour must be between 0 and 23")

    return eval_start, eval_end, resolved_hour


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
    """Fetch, normalize, and evaluate each target day at its prior-day cutoff."""
    cache_key = _cache_key("eval", eval_start, eval_end, decision_hour)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached  # type: ignore

    quality = DataQualityStats()

    start_date = datetime.strptime(eval_start, "%Y-%m-%d").date()
    end_date = datetime.strptime(eval_end, "%Y-%m-%d").date()
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=timezone.utc
    )

    actual_publish_from = start_dt
    actual_publish_to = end_exclusive + timedelta(hours=2)

    forecast_publish_from = start_dt - timedelta(days=3)
    forecast_publish_to = end_exclusive + timedelta(days=1)

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

    try:
        _forecast_archive.store(raw_forecasts)
        archived_forecasts = _forecast_archive.load(
            forecast_publish_from, forecast_publish_to
        )
    except sqlite3.Error as e:
        logger.exception("Failed to persist or read the WINDFOR revision archive")
        raise HTTPException(
            status_code=503,
            detail="Failed to persist or read the local WINDFOR revision archive",
        ) from e
    raw_forecasts = archived_forecasts

    actuals_df = normalize_actuals(raw_actuals, quality)
    forecasts_df = normalize_forecasts(raw_forecasts, quality)

    quality.last_successful_fetch = _client.last_fetch_time

    all_records: list[SelectedForecast] = []
    target_dates = {
        start_date + timedelta(days=day_offset)
        for day_offset in range((end_date - start_date).days + 1)
    }
    if not forecasts_df.empty:
        for st in forecasts_df["start_time"]:
            dt = st.to_pydatetime() if hasattr(st, "to_pydatetime") else st
            if start_dt <= dt < end_exclusive:
                target_dates.add(dt.date())

    if not actuals_df.empty:
        for st in actuals_df["start_time_hourly"]:
            dt = st.to_pydatetime() if hasattr(st, "to_pydatetime") else st
            if start_dt <= dt < end_exclusive:
                target_dates.add(dt.date())

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
    """Liveness check; this does not probe upstream Elexon readiness."""
    configured_url = urlsplit(settings.ELEXON_BASE_URL)
    hostname = configured_url.hostname or ""
    if ":" in hostname:
        hostname = f"[{hostname}]"
    if configured_url.port is not None:
        hostname = f"{hostname}:{configured_url.port}"
    safe_api_url = urlunsplit(
        (configured_url.scheme, hostname, configured_url.path, "", "")
    )
    return HealthResponse(
        elexon_api_url=safe_api_url,
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
    eval_start, eval_end, d_hour = _resolve_filters(start, end, decision_hour)
    records, quality = _fetch_and_process(eval_start, eval_end, d_hour)

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
    eval_start, eval_end, d_hour = _resolve_filters(start, end, decision_hour)

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
    eval_start, eval_end, d_hour = _resolve_filters(start, end, decision_hour)

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
    eval_start, eval_end, d_hour = _resolve_filters(start, end, decision_hour)

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
    eval_start, eval_end, d_hour = _resolve_filters(start, end, decision_hour)

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
