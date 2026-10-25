export interface SelectedForecast {
  target_time: string;
  decision_time: string;
  forecast_generation_mw: number | null;
  forecast_publish_time: string | null;
  actual_generation_mw: number | null;
  error_mw: number | null;
  absolute_error_mw: number | null;
  percentage_error: number | null;
  forecast_available: boolean;
  actual_available: boolean;
  exclusion_reason: string | null;
}

export interface AccuracyMetrics {
  mae_mw: number | null;
  rmse_mw: number | null;
  mape_percent: number | null;
  mbe_mw: number | null;
  median_ae_mw: number | null;
  error_std_mw: number | null;
  total_observations: number;
  valid_observations: number;
  mape_eligible_observations: number;
  mape_excluded_zero_actual: number;
  evaluation_start: string;
  evaluation_end: string;
  decision_hour_utc: number;
}

export interface DataQualityStats {
  actual_records_retrieved: number;
  forecast_records_retrieved: number;
  matched_periods: number;
  periods_missing_actual: number;
  periods_missing_forecast: number;
  duplicate_actuals_removed: number;
  duplicate_forecasts_removed: number;
  forecasts_excluded_after_cutoff: number;
  first_target_time: string | null;
  last_target_time: string | null;
  first_publish_time: string | null;
  last_publish_time: string | null;
  last_successful_fetch: string | null;
  unique_publish_times: number;
  forecast_resolution_hours: number;
  actual_resolution_minutes: number;
  resolution_note: string;
}

export interface OverviewResponse {
  evaluation_start: string;
  evaluation_end: string;
  decision_hour_utc: number;
  latest_forecast: SelectedForecast | null;
  metrics: AccuracyMetrics | null;
  data_quality: DataQualityStats;
  data_source: string;
  last_successful_fetch: string | null;
  error_message: string | null;
}

export interface ForecastSeriesResponse {
  records: SelectedForecast[];
  total_records: number;
  evaluation_start: string;
  evaluation_end: string;
  decision_hour_utc: number;
  data_quality: DataQualityStats;
}

export interface DailyMetric {
  date: string;
  mae_mw: number;
  rmse_mw: number;
  mbe_mw: number;
  count: number;
}

export interface HourlyMetric {
  hour: number;
  mae_mw: number;
  mbe_mw: number;
  count: number;
}

export interface ErrorBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface AccuracyResponse {
  metrics: AccuracyMetrics;
  daily_metrics: DailyMetric[];
  hourly_metrics: HourlyMetric[];
  error_distribution: ErrorBin[];
  data_quality: DataQualityStats;
}
