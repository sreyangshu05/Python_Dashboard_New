"""Tests for FastAPI endpoints."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.api.routes import (
    export_csv,
    get_accuracy,
    get_data_quality,
    get_forecasts,
    get_overview,
    health_check,
)
from app.main import root
from app.schemas.models import DataQualityStats, SelectedForecast


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_health_endpoint():
    data = health_check()
    assert data.status == "ok"
    assert data.service == "windscope-uk-backend"
    assert data.elexon_api_url is not None


def test_root_endpoint():
    data = root()
    assert "WindScope UK" in data["service"]


@patch("app.api.routes._fetch_and_process")
def test_overview_endpoint(mock_fetch):
    mock_records = [
        SelectedForecast(
            target_time=_utc(2026, 1, 15, 12),
            decision_time=_utc(2026, 1, 14, 9),
            forecast_generation_mw=12000.0,
            forecast_publish_time=_utc(2026, 1, 14, 7, 30),
            actual_generation_mw=11500.0,
            error_mw=500.0,
            absolute_error_mw=500.0,
            percentage_error=4.35,
            forecast_available=True,
            actual_available=True,
        )
    ]
    quality = DataQualityStats(
        actual_records_retrieved=100,
        forecast_records_retrieved=200,
        matched_periods=1,
    )
    mock_fetch.return_value = (mock_records, quality)

    data = get_overview(start="2026-01-01", end="2026-01-31", decision_hour=9)
    assert data.evaluation_start == "2026-01-01"
    assert data.evaluation_end == "2026-01-31"
    assert data.decision_hour_utc == 9
    assert data.latest_forecast is not None
    assert data.latest_forecast.forecast_generation_mw == 12000.0
    assert data.metrics.mae_mw == 500.0
    assert data.metrics.rmse_mw == 500.0
    assert data.metrics.mbe_mw == 500.0


@patch("app.api.routes._fetch_and_process")
def test_forecasts_endpoint(mock_fetch):
    mock_records = [
        SelectedForecast(
            target_time=_utc(2026, 1, 15, 12),
            decision_time=_utc(2026, 1, 14, 9),
            forecast_generation_mw=12000.0,
            forecast_publish_time=_utc(2026, 1, 14, 7, 30),
            actual_generation_mw=11500.0,
            error_mw=500.0,
            absolute_error_mw=500.0,
            percentage_error=4.35,
            forecast_available=True,
            actual_available=True,
        )
    ]
    quality = DataQualityStats(matched_periods=1)
    mock_fetch.return_value = (mock_records, quality)

    data = get_forecasts(start="2026-01-01", end="2026-01-31", decision_hour=9)
    assert len(data.records) == 1
    assert data.total_records == 1


@patch("app.api.routes._fetch_and_process")
def test_accuracy_endpoint(mock_fetch):
    mock_records = [
        SelectedForecast(
            target_time=_utc(2026, 1, 15, 12),
            decision_time=_utc(2026, 1, 14, 9),
            forecast_generation_mw=110.0,
            forecast_publish_time=_utc(2026, 1, 14, 7, 30),
            actual_generation_mw=100.0,
            error_mw=10.0,
            absolute_error_mw=10.0,
            percentage_error=10.0,
            forecast_available=True,
            actual_available=True,
        ),
        SelectedForecast(
            target_time=_utc(2026, 1, 15, 13),
            decision_time=_utc(2026, 1, 14, 9),
            forecast_generation_mw=90.0,
            forecast_publish_time=_utc(2026, 1, 14, 7, 30),
            actual_generation_mw=100.0,
            error_mw=-10.0,
            absolute_error_mw=10.0,
            percentage_error=10.0,
            forecast_available=True,
            actual_available=True,
        ),
    ]
    quality = DataQualityStats(matched_periods=2)
    mock_fetch.return_value = (mock_records, quality)

    data = get_accuracy(start="2026-01-01", end="2026-01-31", decision_hour=9)
    assert data.metrics.mae_mw == 10.0
    assert data.metrics.rmse_mw == 10.0
    assert data.metrics.mbe_mw == 0.0
    assert data.metrics.mape_percent == 10.0
    assert len(data.daily_metrics) == 1
    assert len(data.hourly_metrics) == 2


@patch("app.api.routes._fetch_and_process")
def test_export_csv_endpoint(mock_fetch):
    mock_records = [
        SelectedForecast(
            target_time=_utc(2026, 1, 15, 12),
            decision_time=_utc(2026, 1, 14, 9),
            forecast_generation_mw=120.0,
            forecast_publish_time=_utc(2026, 1, 14, 7, 30),
            actual_generation_mw=100.0,
            error_mw=20.0,
            absolute_error_mw=20.0,
            percentage_error=20.0,
            forecast_available=True,
            actual_available=True,
        )
    ]
    quality = DataQualityStats()
    mock_fetch.return_value = (mock_records, quality)

    response = export_csv(start="2026-01-01", end="2026-01-31", decision_hour=9)
    assert response.media_type == "text/csv"
    assert "attachment; filename=windscope_uk_2026-01-01_to_2026-01-31.csv" in response.headers["content-disposition"]
