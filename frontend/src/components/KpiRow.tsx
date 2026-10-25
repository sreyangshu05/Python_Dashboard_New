import React from 'react';
import { AccuracyMetrics, SelectedForecast } from '../types';
import { TrendingUp, TrendingDown, Target, Zap, BarChart2, Info, CheckCircle2 } from 'lucide-react';

interface KpiRowProps {
  metrics: AccuracyMetrics | null;
  latestForecast: SelectedForecast | null;
  isLoading: boolean;
}

export const KpiRow: React.FC<KpiRowProps> = ({ metrics, latestForecast, isLoading }) => {
  const formatMw = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '—';
    return `${val.toLocaleString('en-GB', { maximumFractionDigits: 1 })} MW`;
  };

  const formatPct = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '—';
    return `${val.toFixed(1)}%`;
  };

  const formatTime = (ts: string | null | undefined) => {
    if (!ts) return '';
    try {
      const dt = new Date(ts);
      return dt.toLocaleTimeString('en-GB', {
        timeZone: 'Europe/London',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {/* 1. Latest Forecast */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-medium">Latest Forecast</span>
          <Target className="w-3.5 h-3.5 text-teal-600" />
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            formatMw(latestForecast?.forecast_generation_mw)
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1 truncate">
          {latestForecast?.target_time ? `Target: ${formatTime(latestForecast.target_time)}` : 'Period observation'}
        </div>
      </div>

      {/* 2. Latest Actual */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <span className="font-medium">Latest Actual</span>
          <Zap className="w-3.5 h-3.5 text-blue-600" />
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            formatMw(latestForecast?.actual_generation_mw)
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1 truncate">
          {latestForecast ? (
            <span className={`inline-flex items-center font-medium ${
              (latestForecast.error_mw ?? 0) > 0 ? 'text-amber-600' : 'text-emerald-600'
            }`}>
              Diff: {(latestForecast.error_mw ?? 0) > 0 ? '+' : ''}
              {formatMw(latestForecast.error_mw)}
            </span>
          ) : 'Matched realization'}
        </div>
      </div>

      {/* 3. MAE */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <div className="flex items-center space-x-1">
            <span className="font-medium">Mean Abs Error</span>
            <span title="MAE = mean(abs(forecast - actual)). Average error magnitude across the month." className="cursor-help">
              <Info className="w-3 h-3 text-slate-400" />
            </span>
          </div>
          <BarChart2 className="w-3.5 h-3.5 text-slate-400" />
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            formatMw(metrics?.mae_mw)
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          Monthly average error
        </div>
      </div>

      {/* 4. RMSE */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <div className="flex items-center space-x-1">
            <span className="font-medium">Root Mean Sq Err</span>
            <span title="RMSE = sqrt(mean((forecast - actual)^2)). Penalizes larger discrepancies more heavily." className="cursor-help">
              <Info className="w-3 h-3 text-slate-400" />
            </span>
          </div>
          <BarChart2 className="w-3.5 h-3.5 text-slate-400" />
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            formatMw(metrics?.rmse_mw)
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          Heavier weight on large errors
        </div>
      </div>

      {/* 5. Mean Bias Error (MBE) */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <div className="flex items-center space-x-1">
            <span className="font-medium">Mean Bias Error</span>
            <span title="MBE = mean(forecast - actual). Positive = Overforecasting, Negative = Underforecasting." className="cursor-help">
              <Info className="w-3 h-3 text-slate-400" />
            </span>
          </div>
          {(metrics?.mbe_mw ?? 0) >= 0 ? (
            <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5 text-blue-500" />
          )}
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            <span className={(metrics?.mbe_mw ?? 0) > 0 ? 'text-amber-700' : 'text-blue-700'}>
              {(metrics?.mbe_mw ?? 0) > 0 ? '+' : ''}{formatMw(metrics?.mbe_mw)}
            </span>
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          {(metrics?.mbe_mw ?? 0) > 0 ? 'Tendency to overforecast' : (metrics?.mbe_mw ?? 0) < 0 ? 'Tendency to underforecast' : 'Neutral average bias'}
        </div>
      </div>

      {/* 6. MAPE & Matched */}
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-xs relative group">
        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
          <div className="flex items-center space-x-1">
            <span className="font-medium">MAPE / Matched</span>
            <span title="Mean Absolute Percentage Error. Zero-actual hours excluded." className="cursor-help">
              <Info className="w-3 h-3 text-slate-400" />
            </span>
          </div>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        </div>
        <div className="text-xl font-bold text-slate-900 tracking-tight">
          {isLoading ? (
            <div className="h-6 bg-slate-200 animate-pulse rounded w-20 my-0.5"></div>
          ) : (
            formatPct(metrics?.mape_percent)
          )}
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          {metrics ? `${metrics.valid_observations} matched hours` : '—'}
        </div>
      </div>
    </div>
  );
};
