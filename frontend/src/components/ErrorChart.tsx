import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { SelectedForecast } from '../types';

interface ErrorChartProps {
  records: SelectedForecast[];
  isLoading: boolean;
}

export const ErrorChart: React.FC<ErrorChartProps> = ({ records, isLoading }) => {
  const data = records
    .filter((r) => r.error_mw !== null)
    .map((r) => {
      const dt = new Date(r.target_time);
      const dateStr = dt.toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: 'numeric',
        month: 'short',
      });
      const timeStr = dt.toLocaleTimeString('en-GB', {
        timeZone: 'UTC',
        hour: '2-digit',
        minute: '2-digit',
      });
      return {
        displayTime: `${dateStr} ${timeStr}`,
        shortTime: `${dt.getDate()}/${dt.getMonth() + 1} ${timeStr}`,
        error: r.error_mw,
        absError: r.absolute_error_mw,
        forecast: r.forecast_generation_mw,
        actual: r.actual_generation_mw,
      };
    });

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      const isOver = p.error > 0;
      return (
        <div className="bg-slate-900 text-white p-3 rounded-lg shadow-lg text-xs space-y-1 border border-slate-700">
          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
            {p.displayTime} UTC
          </p>
          <div className="flex justify-between items-center space-x-3">
            <span>Signed Error:</span>
            <span className={`font-mono font-medium ${isOver ? 'text-amber-400' : 'text-blue-400'}`}>
              {isOver ? '+' : ''}{p.error.toLocaleString()} MW
            </span>
          </div>
          <div className="text-[11px] text-slate-400">
            {isOver ? '⚠️ Overforecast (Surplus procurement)' : '⚡ Underforecast (Deficit risk)'}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-lg border border-slate-200 shadow-xs mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-900">Forecast Error Over Time (Signed: Forecast − Actual)</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Positive values indicate overforecasting; negative values indicate underforecasting (MW)
          </p>
        </div>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-amber-500 inline-block"></span>
            <span className="text-slate-600">Overforecast (+MW)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-xs bg-blue-500 inline-block"></span>
            <span className="text-slate-600">Underforecast (−MW)</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full pt-3">
        {isLoading ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            Loading error series...
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            No matched errors to display.
          </div>
        ) : (
          <ResponsiveContainer
            width="100%"
            height="100%"
            role="img"
            aria-label="Bar chart of hourly signed forecast errors in megawatts; positive values indicate overforecasting and negative values indicate underforecasting. Detailed values are available in Forecast Explorer."
          >
            <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
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
                tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#475569" strokeWidth={1.5} />
              <Bar dataKey="error" name="Forecast Error (MW)" isAnimationActive={false}>
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={(entry.error ?? 0) > 0 ? '#f59e0b' : '#3b82f6'}
                    opacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
