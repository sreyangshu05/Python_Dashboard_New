import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { HourlyMetric } from '../types';

interface HourlyMetricsChartProps {
  hourlyMetrics: HourlyMetric[];
  isLoading: boolean;
}

export const HourlyMetricsChart: React.FC<HourlyMetricsChartProps> = ({ hourlyMetrics, isLoading }) => {
  const data = hourlyMetrics.map((h) => ({
    hour: `${String(h.hour).padStart(2, '0')}:00`,
    mae: h.mae_mw,
    mbe: h.mbe_mw,
    count: h.count,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-2.5 rounded-lg text-xs space-y-1">
          <p className="font-semibold text-slate-200">{p.hour} UTC ({p.count} samples)</p>
          <div className="flex justify-between items-center text-teal-300">
            <span>Hourly MAE:</span>
            <span className="font-mono">{p.mae.toLocaleString()} MW</span>
          </div>
          <div className="flex justify-between items-center text-amber-300">
            <span>Hourly MBE (Bias):</span>
            <span className="font-mono">{p.mbe > 0 ? '+' : ''}{p.mbe.toLocaleString()} MW</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-lg border border-slate-200 shadow-xs mb-6">
      <div className="pb-3 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">Diurnal Pattern of Forecast Errors (Hour of Day UTC)</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Reveals whether forecast uncertainty or bias is concentrated during morning ramp, peak hours, or overnight
        </p>
      </div>

      <div className="h-64 w-full pt-3">
        {isLoading ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            Loading diurnal pattern...
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            No diurnal metrics available.
          </div>
        ) : (
          <ResponsiveContainer
            width="100%"
            height="100%"
            role="img"
            aria-label="Bar chart of mean absolute error and mean bias error by UTC hour, measured in megawatts."
          >
            <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} stroke="#cbd5e1" />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" MW" width={65} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={32} wrapperStyle={{ fontSize: '11px' }} />
              <ReferenceLine y={0} stroke="#94a3b8" />
              <Bar dataKey="mae" name="Mean Abs Error (MW)" fill="#0d9488" radius={[2, 2, 0, 0]} opacity={0.85} isAnimationActive={false} />
              <Bar dataKey="mbe" name="Mean Bias (MW)" fill="#f59e0b" radius={[2, 2, 0, 0]} opacity={0.85} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
