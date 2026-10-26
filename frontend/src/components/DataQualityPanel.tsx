import React from 'react';
import { DataQualityStats } from '../types';
import { Database, ShieldCheck, Filter, Clock, Layers, AlertCircle } from 'lucide-react';

interface DataQualityPanelProps {
  stats: DataQualityStats;
  isLoading: boolean;
}

export const DataQualityPanel: React.FC<DataQualityPanelProps> = ({ stats, isLoading }) => {
  const formatTime = (ts: string | null) => {
    if (!ts) return '—';
    try {
      const dt = new Date(ts);
      return dt.toLocaleString('en-GB', {
        timeZone: 'Europe/London',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
      });
    } catch {
      return ts;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-xs mb-6 p-4 sm:p-5">
      <div className="pb-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-teal-600" />
            <span>Data Ingestion & Integrity Audit</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Full provenance tracking of raw Elexon BMRS streaming records, normalization, and deduplication
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 my-4">
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Database className="w-3.5 h-3.5 text-blue-500" />
            <span>Raw Records Retrieved</span>
          </div>
          <div className="text-lg font-bold text-slate-800">
            {stats.actual_records_retrieved.toLocaleString()} actuals
          </div>
          <div className="text-xs text-slate-600 mt-0.5">
            {stats.forecast_records_retrieved.toLocaleString()} forecast revisions
          </div>
        </div>

        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Filter className="w-3.5 h-3.5 text-emerald-500" />
            <span>Matched Settlement Hours</span>
          </div>
          <div className="text-lg font-bold text-emerald-700">
            {stats.matched_periods.toLocaleString()} hours
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Full forecast + actual pair
          </div>
        </div>

        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Layers className="w-3.5 h-3.5 text-indigo-500" />
            <span>Deduplication & Revisions</span>
          </div>
          <div className="text-lg font-bold text-slate-800">
            {stats.unique_publish_times} publish cycles
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            {stats.duplicate_actuals_removed} duplicate actuals; {stats.duplicate_forecasts_removed} duplicate forecast rows removed
          </div>
        </div>

        {(stats.invalid_actual_records > 0 ||
          stats.invalid_forecast_records > 0 ||
          stats.incomplete_actual_hours > 0 ||
          stats.periods_missing_actual > 0 ||
          stats.periods_missing_forecast > 0) && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            Data-quality exclusions: {stats.invalid_actual_records} invalid actual rows,{' '}
            {stats.invalid_forecast_records} invalid forecast rows,{' '}
            {stats.incomplete_actual_hours} incomplete actual hours,{' '}
            {stats.periods_missing_actual} missing actual hours, and{' '}
            {stats.periods_missing_forecast} missing eligible forecasts.
          </div>
        )}

        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
          <div className="flex items-center space-x-2 text-xs text-slate-500 mb-1">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span>Cutoff Enforcements</span>
          </div>
          <div className="text-lg font-bold text-amber-700">
            {stats.forecasts_excluded_after_cutoff} excluded
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Published after decision cutoff
          </div>
        </div>
      </div>

      <div className="bg-slate-50 rounded-lg p-3 text-xs border border-slate-200 space-y-2">
        <div className="font-semibold text-slate-800 flex items-center space-x-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-teal-600" />
          <span>Resolution Normalization Semantics</span>
        </div>
        <p className="text-slate-600 leading-relaxed">
          {stats.resolution_note}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-200 text-[11px] text-slate-500">
          <div><span className="font-medium">Target Period Start:</span> {formatTime(stats.first_target_time)}</div>
          <div><span className="font-medium">Target Period End:</span> {formatTime(stats.last_target_time)}</div>
          <div><span className="font-medium">First Publish Cycle:</span> {formatTime(stats.first_publish_time)}</div>
          <div><span className="font-medium">Latest Publish Cycle:</span> {formatTime(stats.last_publish_time)}</div>
        </div>
      </div>
    </div>
  );
};
