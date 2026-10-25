import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { ErrorBin } from '../types';

interface ErrorDistributionChartProps {
  distribution: ErrorBin[];
  isLoading: boolean;
}

export const ErrorDistributionChart: React.FC<ErrorDistributionChartProps> = ({ distribution, isLoading }) => {
  const data = distribution.map((b) => ({
    range: `${b.bin_start > 0 ? '+' : ''}${Math.round(b.bin_start)} to ${b.bin_end > 0 ? '+' : ''}${Math.round(b.bin_end)}`,
    midpoint: (b.bin_start + b.bin_end) / 2,
    count: b.count,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 text-white p-2.5 rounded-lg text-xs space-y-1">
          <p className="font-semibold text-slate-200">Error Band: {p.range} MW</p>
          <p className="text-teal-400 font-medium">Frequency: {p.count} hours</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-lg border border-slate-200 shadow-xs mb-6">
      <div className="pb-3 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">Forecast Error Distribution (MW)</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Histogram of signed errors (forecast − actual). Symmetrical around zero indicates unbiased forecasts.
        </p>
      </div>

      <div className="h-64 w-full pt-3">
        {isLoading ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            Loading distribution...
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center bg-slate-50 rounded text-slate-400 text-xs">
            No error distribution data available.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="range"
                tick={{ fontSize: 10, fill: '#64748b' }}
                angle={-30}
                textAnchor="end"
                interval={0}
                stroke="#cbd5e1"
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
                stroke="#cbd5e1"
                unit=" hrs"
                width={55}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#0d9488" radius={[2, 2, 0, 0]} opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
