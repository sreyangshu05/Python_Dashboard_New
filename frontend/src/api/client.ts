import { AccuracyResponse, ForecastSeriesResponse, OverviewResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchOverview(start?: string, end?: string, decisionHour?: number): Promise<OverviewResponse> {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  if (decisionHour !== undefined) params.append('decision_hour', decisionHour.toString());

  const res = await fetch(`${API_BASE}/overview?${params.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to load overview: ${res.status} ${errorText}`);
  }
  return res.json();
}

export async function fetchForecastSeries(start?: string, end?: string, decisionHour?: number): Promise<ForecastSeriesResponse> {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  if (decisionHour !== undefined) params.append('decision_hour', decisionHour.toString());

  const res = await fetch(`${API_BASE}/forecasts?${params.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to load forecasts: ${res.status} ${errorText}`);
  }
  return res.json();
}

export async function fetchAccuracy(start?: string, end?: string, decisionHour?: number): Promise<AccuracyResponse> {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  if (decisionHour !== undefined) params.append('decision_hour', decisionHour.toString());

  const res = await fetch(`${API_BASE}/accuracy?${params.toString()}`);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Failed to load accuracy: ${res.status} ${errorText}`);
  }
  return res.json();
}

export function getExportUrl(start?: string, end?: string, decisionHour?: number): string {
  const params = new URLSearchParams();
  if (start) params.append('start', start);
  if (end) params.append('end', end);
  if (decisionHour !== undefined) params.append('decision_hour', decisionHour.toString());
  return `${API_BASE}/export.csv?${params.toString()}`;
}
