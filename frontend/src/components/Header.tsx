import React from 'react';
import { Wind, Activity, RefreshCw, AlertCircle, Clock } from 'lucide-react';

interface HeaderProps {
  evaluationPeriod: string;
  decisionHour: number;
  lastFetchTime: string | null;
  isLoading: boolean;
  onRefresh: () => void;
  dataSourceStatus: 'connected' | 'error' | 'loading';
  errorMessage?: string | null;
}

export const Header: React.FC<HeaderProps> = ({
  evaluationPeriod,
  decisionHour,
  lastFetchTime,
  isLoading,
  onRefresh,
  dataSourceStatus,
  errorMessage,
}) => {
  const formatTime = (ts: string | null) => {
    if (!ts) return 'Not yet loaded';
    try {
      const dt = new Date(ts);
      return dt.toLocaleTimeString('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }) + ' GMT';
    } catch {
      return ts;
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
              <Wind className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg font-bold text-slate-900 tracking-tight">WindScope UK</h1>
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-teal-50 text-teal-700 border border-teal-200">
                  National Grid BMRS
                </span>
              </div>
              <p className="text-xs text-slate-500">Day-Ahead Wind Forecast Intelligence & Procurement Decision Support</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden md:flex flex-col text-right text-xs">
              <div className="flex items-center justify-end space-x-1.5 text-slate-600">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-medium">Scope: {evaluationPeriod}</span>
                <span className="text-slate-400">|</span>
                <span>Cutoff: {String(decisionHour).padStart(2, '0')}:00 UTC</span>
              </div>
              <div className="flex items-center justify-end space-x-1 text-slate-400 mt-0.5">
                <span>Refreshed: {formatTime(lastFetchTime)}</span>
              </div>
            </div>

            <div className="flex items-center space-x-2 border-l border-slate-200 pl-4">
              <div className="flex items-center space-x-1.5 text-xs">
                {dataSourceStatus === 'connected' && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    Elexon BMRS Live
                  </span>
                )}
                {dataSourceStatus === 'loading' && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                    <Activity className="w-3.5 h-3.5 mr-1 animate-spin text-amber-500" />
                    Fetching...
                  </span>
                )}
                {dataSourceStatus === 'error' && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                    <AlertCircle className="w-3.5 h-3.5 mr-1 text-rose-500" />
                    API Error
                  </span>
                )}
              </div>

              <button
                onClick={onRefresh}
                disabled={isLoading}
                className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors disabled:opacity-50"
                title="Refresh Elexon data"
                aria-label="Refresh data"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-teal-600' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {errorMessage && (
          <div className="bg-rose-50 border-l-4 border-rose-400 p-2.5 my-2 rounded text-xs text-rose-700 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
