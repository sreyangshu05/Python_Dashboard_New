"""Tests for data normalization."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.schemas.models import DataQualityStats
from app.services.data_normalization import (
    normalize_actuals,
    normalize_forecasts,
    normalize_timestamp,
)


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestNormalizeTimestamp:
    def test_iso_string_with_z(self):
        result = normalize_timestamp("2026-01-15T09:30:00Z")
        assert result == _utc(2026, 1, 15, 9, 30)
        assert result.tzinfo is not None

    def test_iso_string_with_offset(self):
        result = normalize_timestamp("2026-01-15T09:30:00+00:00")
        assert result == _utc(2026, 1, 15, 9, 30)

    def test_naive_datetime(self):
        dt = datetime(2026, 1, 15, 9, 30)
        result = normalize_timestamp(dt)
        assert result.tzinfo == timezone.utc

    def test_aware_datetime(self):
        dt = _utc(2026, 1, 15, 9, 30)
        result = normalize_timestamp(dt)
        assert result == dt


class TestNormalizeActuals:
    def test_half_hourly_to_hourly(self):
        """Two half-hourly records should be averaged into one hourly."""
        raw = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T13:00:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": 5000,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T13:30:00Z",
                "startTime": "2026-01-15T12:30:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 26,
                "fuelType": "WIND",
                "generation": 6000,
            },
        ]
        quality = DataQualityStats()
        df = normalize_actuals(raw, quality)

        assert len(df) == 1
        assert df.iloc[0]["generation_mw"] == 5500.0  # Average of 5000 and 6000
        assert df.iloc[0]["sp_count"] == 2
        assert quality.actual_records_retrieved == 2

    def test_empty_input(self):
        quality = DataQualityStats()
        df = normalize_actuals([], quality)
        assert len(df) == 0
        assert quality.actual_records_retrieved == 0

    def test_deduplication(self):
        """Duplicate startTimes should keep the latest publishTime."""
        raw = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T12:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": 5000,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-15T13:00:00Z",  # Later publish
                "startTime": "2026-01-15T12:00:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 25,
                "fuelType": "WIND",
                "generation": 5100,
            },
        ]
        quality = DataQualityStats()
        df = normalize_actuals(raw, quality)
        assert quality.duplicate_actuals_removed == 1

    def test_rejects_incomplete_hours_and_invalid_generations(self):
        raw = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-03-29T01:30:00Z",
                "startTime": "2026-03-29T01:00:00Z",
                "settlementDate": "2026-03-29",
                "settlementPeriod": 5,
                "fuelType": "WIND",
                "generation": 5000,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-03-29T02:00:00Z",
                "startTime": "2026-03-29T01:30:00Z",
                "settlementDate": "2026-03-29",
                "settlementPeriod": 6,
                "fuelType": "WIND",
                "generation": float("nan"),
            },
        ]
        quality = DataQualityStats()
        df = normalize_actuals(raw, quality)

        assert df.empty
        assert quality.invalid_actual_records == 1
        assert quality.incomplete_actual_hours == 1


class TestNormalizeForecasts:
    def test_preserves_revisions(self):
        """Multiple forecasts for the same target should all be preserved."""
        raw = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-15T02:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 5000,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-15T07:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 5200,
            },
        ]
        quality = DataQualityStats()
        df = normalize_forecasts(raw, quality)

        assert len(df) == 2  # Both revisions preserved
        assert quality.forecast_records_retrieved == 2
        assert quality.unique_publish_times == 2

    def test_empty_input(self):
        quality = DataQualityStats()
        df = normalize_forecasts([], quality)
        assert len(df) == 0

    def test_deduplicates_only_identical_publication_revisions(self):
        raw = [
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-15T07:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 5000,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-15T07:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 5000,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2026-01-15T09:30:00Z",
                "startTime": "2026-01-15T12:00:00Z",
                "generation": 5100,
            },
        ]
        quality = DataQualityStats()

        df = normalize_forecasts(raw, quality)

        assert len(df) == 2
        assert quality.duplicate_forecasts_removed == 1
