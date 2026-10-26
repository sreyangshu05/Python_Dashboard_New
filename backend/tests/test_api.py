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
    _resolve_filters,
)
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from app.main import app, root
from app.schemas.models import DataQualityStats, SelectedForecast


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_health_endpoint():
    data = health_check()
    assert data.status == "ok"
    assert data.service == "windscope-uk-backend"
    assert data.elexon_api_url is not None


def test_cors_allows_configured_local_frontend_origin():
    response = TestClient(app).options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unconfigured_origin():
    response = TestClient(app).options(
        "/api/health",
        headers={
            "Origin": "https://unconfigured.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_health_does_not_expose_url_credentials_or_query(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(
        settings,
        "ELEXON_BASE_URL",
        "https://user:secret@example.test/bmrs/api?token=private",
    )

    data = health_check()

    assert data.elexon_api_url == "https://example.test/bmrs/api"
    assert "secret" not in data.model_dump_json()
    assert "private" not in data.model_dump_json()


@pytest.mark.parametrize(
    ("start", "end", "hour"),
    [
        ("2026-02-30", "2026-03-01", 9),
        ("2026-01-02", "2026-01-01", 9),
        ("2026-01-01", "2026-01-02", 24),
        ("not-a-date", "2026-01-02", 9),
        ("2026-1-1", "2026-01-02", 9),
    ],
)
def test_invalid_filters_are_rejected(start, end, hour):
    with pytest.raises(HTTPException) as error:
        _resolve_filters(start, end, hour)
    assert error.value.status_code == 422


@patch("app.api.routes._client.fetch_wind_forecasts", return_value=[])
@patch("app.api.routes._client.fetch_actual_wind_generation", return_value=[])
def test_empty_upstream_data_returns_explicit_hourly_gaps(
    mock_actuals, mock_forecasts, monkeypatch, tmp_path
):
    from app.api import routes
    from app.services.forecast_archive import ForecastRevisionArchive

    routes._cache.clear()
    monkeypatch.setattr(
        routes,
        "_forecast_archive",
        ForecastRevisionArchive(tmp_path / "empty-windfor.sqlite3"),
    )
    records, quality = routes._fetch_and_process("2026-01-01", "2026-01-02", 9)

    assert len(records) == 48
    assert all(not record.forecast_available for record in records)
    assert all(not record.actual_available for record in records)
    assert quality.periods_missing_forecast == 48
    assert quality.periods_missing_actual == 48


@patch("app.api.routes._client.fetch_wind_forecasts")
@patch("app.api.routes._client.fetch_actual_wind_generation", return_value=[])
def test_evaluation_keeps_archived_eligible_forecast_revision(
    mock_actuals, mock_forecasts, monkeypatch, tmp_path
):
    from app.api import routes
    from app.services.forecast_archive import ForecastRevisionArchive

    archive = ForecastRevisionArchive(tmp_path / "windfor.sqlite3")
    archive.store(
        [
            {
                "startTime": "2026-01-15T12:00:00Z",
                "publishTime": "2026-01-14T07:30:00Z",
                "generation": 5200,
            }
        ]
    )
    monkeypatch.setattr(routes, "_forecast_archive", archive)
    mock_forecasts.return_value = [
        {
            "startTime": "2026-01-15T12:00:00Z",
            "publishTime": "2026-01-14T09:30:00Z",
            "generation": 5300,
        }
    ]
    routes._cache.clear()

    records, quality = routes._fetch_and_process("2026-01-15", "2026-01-15", 9)

    target_record = next(
        record for record in records
        if record.target_time == _utc(2026, 1, 15, 12)
    )
    assert target_record.forecast_generation_mw == 5200
    assert target_record.forecast_publish_time == _utc(2026, 1, 14, 7, 30)
    assert quality.forecast_records_retrieved == 2
    mock_actuals.assert_called_once()


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
