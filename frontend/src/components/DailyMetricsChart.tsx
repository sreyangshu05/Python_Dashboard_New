import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { DailyMetric } from '../types';

interface DailyMetricsChartProps {
  dailyMetrics: DailyMetric[];
  isLoading: boolean;
}

export const DailyMetricsChart: React.FC<DailyMetricsChartProps> = ({ dailyMetrics, isLoading }) => {
  const data = dailyMetrics.map((d) => ({
    date: d.date.slice(5), // MM-DD
    fullDate: d.date,
    mae: d.mae_mw,
    rmse: d.rmse_mw,
    mbe: d.mbe_mw,
    count: d.count,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-lg text-xs space-y-1.5 border border-slate-700">
          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
            Date: {p.fullDate} ({p.count} periods)
          </p>
          <div className="flex justify-between items-center text-teal-300">
            <span>MAE:</span>
            <span className="font-mono font-medium">{p.mae.toLocaleString()} MW</span>
          </div>
          <div className="flex justify-between items-center text-indigo-300">
            <span>RMSE:</span>
            <span className="font-mono font-medium">{p.rmse.toLocaleString()} MW</span>
          </div>
          <div className="flex justify-between items-center text-amber-300">
            <span>MBE (Bias):</span>
            <span className="font-mono font-medium">{p.mbe > 0 ? '+' : ''}{p.mbe.toLocaleString()} MW</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-lg border border-slate-200 shadow-xs mb-6">
      <div className="pb-3 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">Daily Forecast Error Metrics (MW)</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Daily MAE, RMSE, and MBE aggregated over 24 hourly periods per day
        </p>
      </div>

      <div className="h-64 w-full pt-3">
        {isLoading ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            Loading daily metrics...
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            No daily metrics available.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" MW" width={65} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={32} wrapperStyle={{ fontSize: '11px' }} />
              <Line type="monotone" dataKey="mae" name="Daily MAE (MW)" stroke="#0d9488" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="rmse" name="Daily RMSE (MW)" stroke="#6366f1" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
              <Line type="monotone" dataKey="mbe" name="Daily MBE (MW)" stroke="#f59e0b" strokeWidth={1.5} dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
