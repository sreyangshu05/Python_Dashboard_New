import React, { useState, useMemo } from 'react';
import { SelectedForecast } from '../types';
import { Download, Search, Filter, AlertTriangle, CheckCircle, XCircle, ArrowUpDown } from 'lucide-react';
import { getExportUrl } from '../api/client';

type StatusFilter = 'all' | 'matched' | 'missing_forecast' | 'missing_actual';

interface ForecastExplorerProps {
  records: SelectedForecast[];
  startDate: string;
  endDate: string;
  decisionHour: number;
  onFilterChange: (start: string, end: string, hour: number) => void;
  isLoading: boolean;
}

export const ForecastExplorer: React.FC<ForecastExplorerProps> = ({
  records,
  startDate,
  endDate,
  decisionHour,
  onFilterChange,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortField, setSortField] = useState<keyof SelectedForecast>('target_time');
  const [sortAsc, setSortAsc] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  // Local input states for date picker
  const [inputStart, setInputStart] = useState(startDate);
  const [inputEnd, setInputEnd] = useState(endDate);
  const [inputHour, setInputHour] = useState(decisionHour);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    onFilterChange(inputStart, inputEnd, inputHour);
    setCurrentPage(1);
  };

  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      // Status filter
      if (statusFilter === 'matched' && (!r.forecast_available || !r.actual_available)) return false;
      if (statusFilter === 'missing_forecast' && r.forecast_available) return false;
      if (statusFilter === 'missing_actual' && r.actual_available) return false;

      // Search term (date or numbers)
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const dateMatch =
          r.target_time.toLowerCase().includes(term) ||
          formatDateTime(r.target_time).toLowerCase().includes(term);
        const fcMatch = r.forecast_generation_mw?.toString().includes(term);
        const acMatch = r.actual_generation_mw?.toString().includes(term);
        return dateMatch || fcMatch || acMatch;
      }
      return true;
    });
  }, [records, statusFilter, searchTerm]);

  const sortedRecords = useMemo(() => {
    return [...filteredRecords].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [filteredRecords, sortField, sortAsc]);

  const totalPages = Math.ceil(sortedRecords.length / pageSize);
  const paginatedRecords = sortedRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleSort = (field: keyof SelectedForecast) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  function formatDateTime(ts: string | null) {
    if (!ts) return '—';
    try {
      const dt = new Date(ts);
      return dt.toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }) + ' GMT';
    } catch {
      return ts;
    }
  }

  const exportUrl = getExportUrl(startDate, endDate, decisionHour);

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-xs mb-6">
      {/* Header & Controls */}
      <div className="p-4 sm:p-5 border-b border-slate-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Forecast & Observation Explorer</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Inspect historical forecasts available at the decision cutoff, matched actuals, and calculated errors
            </p>
          </div>

          <a
            href={exportUrl}
            download
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded text-xs font-medium transition-colors shadow-xs shrink-0 self-start md:self-auto"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV ({sortedRecords.length} rows)</span>
          </a>
        </div>

        {/* Filter Bar */}
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 pt-3 border-t border-slate-100 items-end text-xs">
          <div>
            <label htmlFor="forecast-start-date" className="block text-slate-600 font-medium mb-1">Start Date</label>
            <input
              id="forecast-start-date"
              type="date"
              value={inputStart}
              onChange={(e) => setInputStart(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-slate-800 bg-white focus:outline-hidden focus:ring-1 focus:ring-teal-500"
            />
          </div>
          <div>
            <label htmlFor="forecast-end-date" className="block text-slate-600 font-medium mb-1">End Date</label>
            <input
              id="forecast-end-date"
              type="date"
              value={inputEnd}
              onChange={(e) => setInputEnd(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-slate-800 bg-white focus:outline-hidden focus:ring-1 focus:ring-teal-500"
            />
          </div>
          <div>
            <label htmlFor="forecast-decision-hour" className="block text-slate-600 font-medium mb-1">Decision Cutoff Hour (UTC)</label>
            <select
              id="forecast-decision-hour"
              value={inputHour}
              onChange={(e) => setInputHour(parseInt(e.target.value, 10))}
              className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-slate-800 bg-white focus:outline-hidden focus:ring-1 focus:ring-teal-500"
            >
              {[...Array(24).keys()].map((h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, '0')}:00 UTC (Day-Ahead {h < 12 ? 'Morning' : 'Afternoon'})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="forecast-status-filter" className="block text-slate-600 font-medium mb-1">Status Filter</label>
            <select
              id="forecast-status-filter"
              value={statusFilter}
              onChange={(e) => {
                const value = e.target.value;
                if (
                  value === 'all' ||
                  value === 'matched' ||
                  value === 'missing_forecast' ||
                  value === 'missing_actual'
                ) {
                  setStatusFilter(value);
                }
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-slate-800 bg-white focus:outline-hidden focus:ring-1 focus:ring-teal-500"
            >
              <option value="all">All Records</option>
              <option value="matched">Matched (Forecast + Actual)</option>
              <option value="missing_forecast">Missing Eligible Forecast</option>
              <option value="missing_actual">Missing Realized Actual</option>
            </select>
          </div>
          <div>
            <label htmlFor="forecast-search" className="block text-slate-600 font-medium mb-1">Search records</label>
            <div className="relative">
              <Search aria-hidden="true" className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                id="forecast-search"
                type="search"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Date or MW value"
                className="w-full pl-8 pr-2.5 py-1.5 border border-slate-300 rounded text-slate-800 bg-white focus:outline-hidden focus:ring-1 focus:ring-teal-500"
              />
            </div>
          </div>
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-1.5 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded font-medium transition-colors disabled:opacity-50"
            >
              Apply Filter
            </button>
          </div>
        </form>
      </div>

      {/* Table view */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
            <tr>
              <th scope="col" aria-sort={sortField === 'target_time' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by target period (UTC)" onClick={() => handleSort('target_time')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Target Period (UTC)</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" aria-sort={sortField === 'forecast_generation_mw' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by selected forecast" onClick={() => handleSort('forecast_generation_mw')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Selected Forecast</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" aria-sort={sortField === 'forecast_publish_time' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by publication time" onClick={() => handleSort('forecast_publish_time')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Published At</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" aria-sort={sortField === 'actual_generation_mw' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by actual generation" onClick={() => handleSort('actual_generation_mw')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Actual Generation</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" aria-sort={sortField === 'error_mw' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by error" onClick={() => handleSort('error_mw')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Error (F − A)</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" aria-sort={sortField === 'absolute_error_mw' ? (sortAsc ? 'ascending' : 'descending') : 'none'} className="py-2.5 px-3">
                <button type="button" aria-label="Sort by absolute error" onClick={() => handleSort('absolute_error_mw')} className="flex items-center space-x-1 cursor-pointer hover:text-slate-900">
                  <span>Absolute Error</span>
                  <ArrowUpDown aria-hidden="true" className="w-3 h-3 text-slate-400" />
                </button>
              </th>
              <th scope="col" className="py-2.5 px-3">Percentage Error</th>
              <th scope="col" className="py-2.5 px-3">Availability</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-400">
                  Loading observation table...
                </td>
              </tr>
            ) : paginatedRecords.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-400">
                  No records matching criteria.
                </td>
              </tr>
            ) : (
              paginatedRecords.map((r, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="py-2 px-3 font-mono text-slate-900 whitespace-nowrap">
                    {formatDateTime(r.target_time)}
                  </td>
                  <td className="py-2 px-3 font-mono font-medium text-teal-800">
                    {r.forecast_generation_mw !== null ? `${r.forecast_generation_mw.toLocaleString()} MW` : (
                      <span className="text-slate-400 italic">Unavailable</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-[11px] text-slate-500 whitespace-nowrap">
                    {r.forecast_publish_time ? formatDateTime(r.forecast_publish_time) : '—'}
                  </td>
                  <td className="py-2 px-3 font-mono font-medium text-blue-800">
                    {r.actual_generation_mw !== null ? `${r.actual_generation_mw.toLocaleString()} MW` : (
                      <span className="text-slate-400 italic">Pending</span>
                    )}
                  </td>
                  <td className="py-2 px-3 font-mono font-medium whitespace-nowrap">
                    {r.error_mw !== null ? (
                      <span className={r.error_mw > 0 ? 'text-amber-600' : 'text-blue-600'}>
                        {r.error_mw > 0 ? '+' : ''}{r.error_mw.toLocaleString()} MW
                      </span>
                    ) : '—'}
                  </td>
                  <td className="py-2 px-3 font-mono text-slate-600 whitespace-nowrap">
                    {r.absolute_error_mw !== null ? `${r.absolute_error_mw.toLocaleString()} MW` : '—'}
                  </td>
                  <td className="py-2 px-3 font-mono text-slate-600 whitespace-nowrap">
                    {r.percentage_error !== null ? `${r.percentage_error.toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    {r.forecast_available && r.actual_available ? (
                      <span className="inline-flex items-center text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        <CheckCircle className="w-3 h-3 mr-1 text-emerald-500" />
                        Matched
                      </span>
                    ) : !r.forecast_available ? (
                      <span className="inline-flex items-center text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200" title={r.exclusion_reason || ''}>
                        <AlertTriangle className="w-3 h-3 mr-1 text-amber-500" />
                        No Cutoff Forecast
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                        <XCircle className="w-3 h-3 mr-1 text-slate-400" />
                        No Actual
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="p-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
        <div aria-live="polite">
          Showing {paginatedRecords.length > 0 ? (currentPage - 1) * pageSize + 1 : 0} to{' '}
          {Math.min(currentPage * pageSize, sortedRecords.length)} of {sortedRecords.length} records
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
            className="px-2.5 py-1 border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="px-2">Page {currentPage} of {totalPages || 1}</span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages || totalPages === 0}
            className="px-2.5 py-1 border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};
