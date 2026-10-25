"""Pydantic schemas for WindScope UK API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Elexon raw record schemas ---

class FuelHHRecord(BaseModel):
    """Raw FUELHH record from Elexon API."""
    dataset: str = "FUELHH"
    publishTime: datetime
    startTime: datetime
    settlementDate: str
    settlementPeriod: int
    fuelType: str
    generation: Optional[float] = None


class WindForRecord(BaseModel):
    """Raw WINDFOR record from Elexon API."""
    dataset: str = "WINDFOR"
    publishTime: datetime
    startTime: datetime
    generation: Optional[float] = None


# --- Normalized internal schemas ---

class ActualGeneration(BaseModel):
    """Normalized actual wind generation for an hourly period."""
    start_time: datetime = Field(description="Start of the hourly period (UTC)")
    generation_mw: Optional[float] = Field(description="Actual wind generation in MW (average of half-hourly)")
    settlement_periods_count: int = Field(description="Number of half-hourly periods averaged (normally 2)")
    source_records: int = Field(description="Number of FUELHH source records used")


class ForecastGeneration(BaseModel):
    """A single wind generation forecast for a target period."""
    start_time: datetime = Field(description="Target period start (UTC)")
    publish_time: datetime = Field(description="When this forecast was published (UTC)")
    generation_mw: Optional[float] = Field(description="Forecasted wind generation in MW")


class SelectedForecast(BaseModel):
    """Result of forecast selection for a target period at a decision time."""
    target_time: datetime = Field(description="Target generation period start (UTC)")
    decision_time: datetime = Field(description="Procurement decision cutoff (UTC)")
    forecast_generation_mw: Optional[float] = Field(description="Selected forecast generation MW")
    forecast_publish_time: Optional[datetime] = Field(description="Publication time of selected forecast")
    actual_generation_mw: Optional[float] = Field(description="Actual generation MW")
    error_mw: Optional[float] = Field(description="Signed error: forecast - actual (MW)")
    absolute_error_mw: Optional[float] = Field(description="Absolute error (MW)")
    percentage_error: Optional[float] = Field(description="Percentage error (%), null if actual is zero")
    forecast_available: bool = Field(description="Whether an eligible forecast was found")
    actual_available: bool = Field(description="Whether actual generation data exists")
    exclusion_reason: Optional[str] = Field(default=None, description="Why this observation was excluded")


# --- API response schemas ---

class AccuracyMetrics(BaseModel):
    """Forecast accuracy metrics for an evaluation period."""
    mae_mw: Optional[float] = Field(description="Mean Absolute Error (MW)")
    rmse_mw: Optional[float] = Field(description="Root Mean Squared Error (MW)")
    mape_percent: Optional[float] = Field(description="Mean Absolute Percentage Error (%)")
    mbe_mw: Optional[float] = Field(description="Mean Bias Error (MW)")
    median_ae_mw: Optional[float] = Field(description="Median Absolute Error (MW)")
    error_std_mw: Optional[float] = Field(description="Standard Deviation of Error (MW)")
    total_observations: int = Field(description="Total matched observations")
    valid_observations: int = Field(description="Observations used for MAE/RMSE/MBE")
    mape_eligible_observations: int = Field(description="Observations used for MAPE (non-zero actual)")
    mape_excluded_zero_actual: int = Field(description="Observations excluded from MAPE due to zero actual")
    evaluation_start: datetime
    evaluation_end: datetime
    decision_hour_utc: int


class DataQualityStats(BaseModel):
    """Data quality statistics."""
    actual_records_retrieved: int = 0
    forecast_records_retrieved: int = 0
    matched_periods: int = 0
    periods_missing_actual: int = 0
    periods_missing_forecast: int = 0
    duplicate_actuals_removed: int = 0
    duplicate_forecasts_removed: int = 0
    forecasts_excluded_after_cutoff: int = 0
    first_target_time: Optional[datetime] = None
    last_target_time: Optional[datetime] = None
    first_publish_time: Optional[datetime] = None
    last_publish_time: Optional[datetime] = None
    last_successful_fetch: Optional[datetime] = None
    unique_publish_times: int = 0
    forecast_resolution_hours: int = 1
    actual_resolution_minutes: int = 30
    resolution_note: str = "Forecasts are hourly; actuals are half-hourly. Two half-hourly actuals are averaged per forecast hour."


class OverviewResponse(BaseModel):
    """Dashboard overview response."""
    evaluation_start: str
    evaluation_end: str
    decision_hour_utc: int
    latest_forecast: Optional[SelectedForecast] = None
    metrics: Optional[AccuracyMetrics] = None
    data_quality: DataQualityStats
    data_source: str = "Elexon BMRS (FUELHH + WINDFOR)"
    last_successful_fetch: Optional[datetime] = None
    error_message: Optional[str] = None


class ForecastSeriesResponse(BaseModel):
    """Forecast vs actual series response."""
    records: list[SelectedForecast]
    total_records: int
    evaluation_start: str
    evaluation_end: str
    decision_hour_utc: int
    data_quality: DataQualityStats


class AccuracyResponse(BaseModel):
    """Accuracy analysis response."""
    metrics: AccuracyMetrics
    daily_metrics: list[dict] = Field(default_factory=list, description="Daily aggregated error stats")
    hourly_metrics: list[dict] = Field(default_factory=list, description="Hourly pattern error stats")
    error_distribution: list[dict] = Field(default_factory=list, description="Error distribution buckets")
    data_quality: DataQualityStats


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "windscope-uk-backend"
    version: str = "1.0.0"
    elexon_api_url: str
    evaluation_period: str
    timestamp: datetime

