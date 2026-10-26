"""Tests for forecast selection logic.

Tests use synthetic fixtures that are explicitly identified as test data.
They are never presented as actual Elexon production data.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from app.services.forecast_selection import (
    build_evaluation_series,
    select_forecast_for_target,
)


def _utc(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _make_forecasts_df(records):
    """Helper to create forecasts DataFrame from list of (start, publish, gen) tuples."""
    return pd.DataFrame(records, columns=["start_time", "publish_time", "generation_mw"])


class TestSelectForecastForTarget:
    """Test the core forecast selection function."""

    def test_selects_latest_before_cutoff(self):
        """Given multiple revisions, selects the latest one before the decision time."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 15, 9)

        df = _make_forecasts_df([
            (target, _utc(2026, 1, 15, 2, 30), 5000.0),  # published 02:30 — eligible
            (target, _utc(2026, 1, 15, 4, 30), 5200.0),  # published 04:30 — eligible, latest
            (target, _utc(2026, 1, 15, 7, 30), 5100.0),  # published 07:30 — eligible
            (target, _utc(2026, 1, 15, 11, 30), 5300.0),  # published 11:30 — AFTER cutoff
        ])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is True
        assert gen == 5100.0  # 07:30 publication is latest before 09:00
        assert pub == _utc(2026, 1, 15, 7, 30)
        assert reason is None

    def test_no_future_leakage(self):
        """Forecasts published after the decision time must not be selected."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 14, 9)  # Decision made day before

        df = _make_forecasts_df([
            (target, _utc(2026, 1, 15, 2, 30), 5000.0),  # published 02:30 on target day — AFTER decision
            (target, _utc(2026, 1, 15, 7, 30), 5200.0),  # published 07:30 on target day — AFTER decision
        ])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is False
        assert gen is None
        assert "after decision time" in reason

    def test_no_forecasts_available(self):
        """Returns unavailable when no forecasts target the period."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 15, 9)

        df = _make_forecasts_df([
            (_utc(2026, 1, 15, 13), _utc(2026, 1, 15, 2, 30), 5000.0),  # different target
        ])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is False

    def test_empty_dataframe(self):
        """Returns unavailable for empty forecasts."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 15, 9)
        df = _make_forecasts_df([])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is False
        assert gen is None

    def test_single_eligible_forecast(self):
        """Selects the only eligible forecast."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 15, 9)

        df = _make_forecasts_df([
            (target, _utc(2026, 1, 15, 4, 30), 5000.0),
        ])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is True
        assert gen == 5000.0

    def test_forecast_at_exact_decision_time(self):
        """A forecast published exactly at the decision time is eligible."""
        target = _utc(2026, 1, 15, 12)
        decision = _utc(2026, 1, 15, 9)

        df = _make_forecasts_df([
            (target, _utc(2026, 1, 15, 9, 0), 5000.0),  # exactly at cutoff
        ])

        gen, pub, found, reason = select_forecast_for_target(target, df, decision)
        assert found is True
        assert gen == 5000.0

    def test_equivalent_timezones_compare_by_instant(self):
        target_utc = _utc(2026, 1, 15, 12)
        decision_utc = _utc(2026, 1, 15, 9)
        target_local = target_utc.astimezone(ZoneInfo("Europe/London"))
        published_local = _utc(2026, 1, 15, 8).astimezone(ZoneInfo("Europe/London"))
        df = _make_forecasts_df([(target_local, published_local, 5000.0)])

        generation, publish_time, found, _ = select_forecast_for_target(
            target_utc, df, decision_utc
        )

        assert found
        assert generation == 5000.0
        assert publish_time == _utc(2026, 1, 15, 8)


class TestBuildEvaluationSeries:
    """Test the evaluation series builder."""

    def test_correct_error_sign(self):
        """error = forecast - actual. Overforecast → positive."""
        actuals = pd.DataFrame({
            "start_time_hourly": [_utc(2026, 1, 15, 12)],
            "generation_mw": [100.0],
            "sp_count": [2],
        })
        forecasts = _make_forecasts_df([
            (_utc(2026, 1, 15, 12), _utc(2026, 1, 14, 9), 120.0),
        ])
        decision = _utc(2026, 1, 14, 9)

        results = build_evaluation_series(
            actuals, forecasts, decision,
            _utc(2026, 1, 15), _utc(2026, 1, 16),
        )

        assert len(results) == 24
        r = next(record for record in results if record.target_time == _utc(2026, 1, 15, 12))
        assert r.error_mw == 20.0  # 120 - 100
        assert r.absolute_error_mw == 20.0

    def test_correct_error_negative(self):
        """Underforecast → negative error."""
        actuals = pd.DataFrame({
            "start_time_hourly": [_utc(2026, 1, 15, 12)],
            "generation_mw": [100.0],
            "sp_count": [2],
        })
        forecasts = _make_forecasts_df([
            (_utc(2026, 1, 15, 12), _utc(2026, 1, 14, 9), 90.0),
        ])
        decision = _utc(2026, 1, 14, 9)

        results = build_evaluation_series(
            actuals, forecasts, decision,
            _utc(2026, 1, 15), _utc(2026, 1, 16),
        )

        assert len(results) == 24
        target_record = next(
            record for record in results if record.target_time == _utc(2026, 1, 15, 12)
        )
        assert target_record.error_mw == -10.0

    def test_missing_actual(self):
        """Handles missing actual gracefully."""
        actuals = pd.DataFrame(columns=["start_time_hourly", "generation_mw", "sp_count"])
        forecasts = _make_forecasts_df([
            (_utc(2026, 1, 15, 12), _utc(2026, 1, 14, 9), 120.0),
        ])
        decision = _utc(2026, 1, 14, 9)

        results = build_evaluation_series(
            actuals, forecasts, decision,
            _utc(2026, 1, 15), _utc(2026, 1, 16),
        )

        assert len(results) == 24
        r = next(record for record in results if record.target_time == _utc(2026, 1, 15, 12))
        assert r.forecast_available is True
        assert r.actual_available is False
        assert r.error_mw is None

    def test_missing_forecast(self):
        """Handles missing forecast gracefully."""
        actuals = pd.DataFrame({
            "start_time_hourly": [_utc(2026, 1, 15, 12)],
            "generation_mw": [100.0],
            "sp_count": [2],
        })
        forecasts = _make_forecasts_df([])
        decision = _utc(2026, 1, 14, 9)

        results = build_evaluation_series(
            actuals, forecasts, decision,
            _utc(2026, 1, 15), _utc(2026, 1, 16),
        )

        # No forecasts → the only hour comes from actuals
        matched = [r for r in results if r.actual_available]
        assert len(matched) >= 1
        r = matched[0]
        assert r.forecast_available is False
        assert r.error_mw is None

    def test_includes_every_hour_when_forecast_and_actual_are_missing(self):
        results = build_evaluation_series(
            pd.DataFrame(columns=["start_time_hourly", "generation_mw", "sp_count"]),
            _make_forecasts_df([]),
            _utc(2026, 1, 14, 9),
            _utc(2026, 1, 15),
            _utc(2026, 1, 16),
        )

        assert len(results) == 24
        assert all(not record.forecast_available for record in results)
        assert all(not record.actual_available for record in results)

    @pytest.mark.parametrize(
        ("start", "end", "expected_hours"),
        [
            (
                datetime(2026, 3, 29, tzinfo=ZoneInfo("Europe/London")),
                datetime(2026, 3, 30, tzinfo=ZoneInfo("Europe/London")),
                23,
            ),
            (
                datetime(2026, 10, 25, tzinfo=ZoneInfo("Europe/London")),
                datetime(2026, 10, 26, tzinfo=ZoneInfo("Europe/London")),
                25,
            ),
        ],
    )
    def test_dst_days_preserve_elapsed_utc_hours(self, start, end, expected_hours):
        results = build_evaluation_series(
            pd.DataFrame(columns=["start_time_hourly", "generation_mw", "sp_count"]),
            _make_forecasts_df([]),
            _utc(2026, 1, 1, 9),
            start,
            end,
        )

        assert len(results) == expected_hours
        assert all(
            current.target_time - previous.target_time == timedelta(hours=1)
            for previous, current in zip(results, results[1:])
        )
