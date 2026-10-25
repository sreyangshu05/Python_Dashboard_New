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
import { SelectedForecast } from '../types';

interface ForecastChartProps {
  records: SelectedForecast[];
  isLoading: boolean;
}

export const ForecastChart: React.FC<ForecastChartProps> = ({ records, isLoading }) => {
  // Format data for chart
  const data = records.map((r) => {
    const dt = new Date(r.target_time);
    const dateStr = dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    const timeStr = dt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    return {
      targetTime: r.target_time,
      displayTime: `${dateStr} ${timeStr}`,
      shortTime: `${dt.getDate()}/${dt.getMonth() + 1} ${timeStr}`,
      forecast: r.forecast_generation_mw,
      actual: r.actual_generation_mw,
      publishTime: r.forecast_publish_time,
      error: r.error_mw,
      absError: r.absolute_error_mw,
    };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-lg text-xs space-y-1.5 border border-slate-700 max-w-xs">
          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
            Target: {p.displayTime} GMT
          </p>
          <div className="flex justify-between items-center text-teal-300">
            <span>Forecast:</span>
            <span className="font-mono font-medium">
              {p.forecast !== null ? `${p.forecast.toLocaleString()} MW` : 'Unavailable'}
            </span>
          </div>
          <div className="flex justify-between items-center text-blue-300">
            <span>Actual:</span>
            <span className="font-mono font-medium">
              {p.actual !== null ? `${p.actual.toLocaleString()} MW` : 'Unavailable'}
            </span>
          </div>
          {p.error !== null && (
            <div className="flex justify-between items-center text-slate-300 pt-1 border-t border-slate-800">
              <span>Error (F - A):</span>
              <span className={`font-mono font-medium ${p.error > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {p.error > 0 ? '+' : ''}{p.error.toLocaleString()} MW
              </span>
            </div>
          )}
          {p.publishTime && (
            <p className="text-[10px] text-slate-400 pt-1">
              Published: {new Date(p.publishTime).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} GMT
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-lg border border-slate-200 shadow-xs mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-900">National Wind Generation: Forecast vs Actual</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Elexon BMRS WINDFOR (hourly day-ahead forecasts) vs FUELHH (hourly aggregated actuals) in MW
          </p>
        </div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-teal-600 inline-block"></span>
            <span className="text-slate-600 font-medium">Forecast (WINDFOR)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-0.5 bg-blue-600 inline-block"></span>
            <span className="text-slate-600 font-medium">Actual (FUELHH)</span>
          </div>
        </div>
      </div>

      <div className="h-80 w-full pt-4">
        {isLoading ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            Loading forecast & actual series...
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            No matched observation series for the selected filters.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="shortTime"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                stroke="#cbd5e1"
                interval="preserveStartEnd"
                minTickGap={40}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                stroke="#cbd5e1"
                unit=" MW"
                width={70}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="forecast"
                name="Day-Ahead Forecast (MW)"
                stroke="#0d9488"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: '#0f766e', strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                name="Realized Generation (MW)"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: '#1d4ed8', strokeWidth: 1 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
