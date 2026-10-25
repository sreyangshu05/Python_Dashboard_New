"""Tests for accuracy metrics calculation.

All test data is synthetic and explicitly identified as test fixtures.
These are not actual Elexon generation values.
"""

import math
from datetime import datetime, timezone

import pytest

from app.schemas.models import SelectedForecast
from app.services.accuracy_metrics import (
    calculate_accuracy_metrics,
    calculate_daily_metrics,
    calculate_error_distribution,
)


def _utc(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_record(
    forecast_mw, actual_mw, target_hour=12, target_day=15,
    forecast_available=True, actual_available=True,
):
    """Create a synthetic SelectedForecast for testing."""
    error = None
    abs_error = None
    pct_error = None
    if forecast_available and actual_available and forecast_mw is not None and actual_mw is not None:
        error = forecast_mw - actual_mw
        abs_error = abs(error)
        if actual_mw != 0:
            pct_error = (abs(error) / actual_mw) * 100

    return SelectedForecast(
        target_time=_utc(2026, 1, target_day, target_hour),
        decision_time=_utc(2026, 1, target_day - 1, 9),
        forecast_generation_mw=forecast_mw,
        forecast_publish_time=_utc(2026, 1, target_day - 1, 7, ),
        actual_generation_mw=actual_mw,
        error_mw=round(error, 2) if error is not None else None,
        absolute_error_mw=round(abs_error, 2) if abs_error is not None else None,
        percentage_error=round(pct_error, 2) if pct_error is not None else None,
        forecast_available=forecast_available,
        actual_available=actual_available,
    )


class TestAccuracyMetrics:
    """Test metric calculations against acceptance criteria."""

    def test_acceptance_e_mae(self):
        """Acceptance E: MAE([110,90], [100,100]) = 10 MW."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(90, 100, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mae_mw == 10.0

    def test_acceptance_f_rmse(self):
        """Acceptance F: RMSE([110,90], [100,100]) = 10 MW."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(90, 100, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.rmse_mw == 10.0

    def test_acceptance_g_mbe(self):
        """Acceptance G: MBE([110,90], [100,100]) = 0 MW."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(90, 100, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mbe_mw == 0.0

    def test_acceptance_h_mape(self):
        """Acceptance H: MAPE([110,90], [100,100]) = 10%."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(90, 100, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mape_percent == 10.0

    def test_acceptance_i_zero_actual_excluded(self):
        """Acceptance I: Zero actual excluded from MAPE denominator."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(5, 0, target_hour=13),  # Zero actual
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mape_eligible_observations == 1
        assert metrics.mape_excluded_zero_actual == 1
        assert metrics.mape_percent == 10.0  # Only the non-zero pair

    def test_all_zero_actuals(self):
        """When all actuals are zero, MAPE should be None."""
        records = [
            _make_record(10, 0, target_hour=12),
            _make_record(20, 0, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mape_percent is None
        assert metrics.mape_eligible_observations == 0
        assert metrics.mape_excluded_zero_actual == 2

    def test_empty_dataset(self):
        """Empty records should return None metrics."""
        metrics = calculate_accuracy_metrics([], "2026-01-01", "2026-01-31", 9)
        assert metrics.mae_mw is None
        assert metrics.rmse_mw is None
        assert metrics.mape_percent is None
        assert metrics.mbe_mw is None
        assert metrics.valid_observations == 0

    def test_single_observation(self):
        """Single observation should work."""
        records = [_make_record(120, 100)]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mae_mw == 20.0
        assert metrics.rmse_mw == 20.0
        assert metrics.mbe_mw == 20.0
        assert metrics.valid_observations == 1

    def test_perfect_forecasts(self):
        """Perfect forecasts should give zero errors."""
        records = [
            _make_record(100, 100, target_hour=12),
            _make_record(200, 200, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mae_mw == 0.0
        assert metrics.rmse_mw == 0.0
        assert metrics.mbe_mw == 0.0
        assert metrics.mape_percent == 0.0

    def test_missing_forecast_excluded(self):
        """Records where forecast is unavailable should be excluded."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(None, 100, target_hour=13, forecast_available=False),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.valid_observations == 1
        assert metrics.total_observations == 2
        assert metrics.mae_mw == 10.0

    def test_missing_actual_excluded(self):
        """Records where actual is unavailable should be excluded."""
        records = [
            _make_record(110, 100, target_hour=12),
            _make_record(90, None, target_hour=13, actual_available=False),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.valid_observations == 1
        assert metrics.mae_mw == 10.0

    def test_acceptance_d_signed_error(self):
        """Acceptance D: forecast=120, actual=100 → error = +20 MW."""
        records = [_make_record(120, 100)]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mbe_mw == 20.0  # Positive = overforecast

    def test_large_errors(self):
        """Large forecast errors should be handled correctly."""
        records = [
            _make_record(20000, 5000, target_hour=12),
            _make_record(1000, 18000, target_hour=13),
        ]
        metrics = calculate_accuracy_metrics(records, "2026-01-01", "2026-01-31", 9)
        assert metrics.mae_mw is not None
        assert metrics.valid_observations == 2


class TestDailyMetrics:
    """Test daily aggregation."""

    def test_daily_aggregation(self):
        records = [
            _make_record(110, 100, target_hour=12, target_day=15),
            _make_record(90, 100, target_hour=13, target_day=15),
            _make_record(150, 100, target_hour=12, target_day=16),
        ]
        daily = calculate_daily_metrics(records)
        assert len(daily) == 2
        assert daily[0]["date"] == "2026-01-15"
        assert daily[0]["mae_mw"] == 10.0
        assert daily[0]["mbe_mw"] == 0.0


class TestErrorDistribution:
    """Test error distribution histogram."""

    def test_distribution_bins(self):
        records = [_make_record(100 + i * 10, 100) for i in range(-5, 6)]
        dist = calculate_error_distribution(records)
        assert len(dist) > 0
        total_count = sum(b["count"] for b in dist)
        assert total_count == len(records)

