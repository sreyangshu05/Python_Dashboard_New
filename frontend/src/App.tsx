import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { KpiRow } from './components/KpiRow';
import { ForecastChart } from './components/ForecastChart';
import { ErrorChart } from './components/ErrorChart';
import { ErrorDistributionChart } from './components/ErrorDistributionChart';
import { DailyMetricsChart } from './components/DailyMetricsChart';
import { HourlyMetricsChart } from './components/HourlyMetricsChart';
import { ForecastExplorer } from './components/ForecastExplorer';
import { DataQualityPanel } from './components/DataQualityPanel';
import { MethodologyPanel } from './components/MethodologyPanel';
import { fetchAccuracy, fetchForecastSeries, fetchOverview } from './api/client';
import { AccuracyResponse, ForecastSeriesResponse, OverviewResponse } from './types';
import { BarChart3, Search, TrendingUp, ShieldCheck, BookOpen, Layers } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'explorer' | 'accuracy' | 'quality' | 'methodology'>('overview');
  
  // Evaluation Scope
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState('2026-01-31');
  const [decisionHour, setDecisionHour] = useState(9); // 09:00 UTC day-ahead

  // Data states
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [forecastSeries, setForecastSeries] = useState<ForecastSeriesResponse | null>(null);
  const [accuracy, setAccuracy] = useState<AccuracyResponse | null>(null);

  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [dataSourceStatus, setDataSourceStatus] = useState<'connected' | 'loading' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = useCallback(async (start: string, end: string, hour: number) => {
    setIsLoading(true);
    setDataSourceStatus('loading');
    setErrorMessage(null);
    setOverview(null);
    setForecastSeries(null);
    setAccuracy(null);

    try {
      const [overviewData, seriesData, accuracyData] = await Promise.all([
        fetchOverview(start, end, hour),
        fetchForecastSeries(start, end, hour),
        fetchAccuracy(start, end, hour),
      ]);

      setOverview(overviewData);
      setForecastSeries(seriesData);
      setAccuracy(accuracyData);
      setDataSourceStatus('connected');
    } catch (err: unknown) {
      console.error('Failed to fetch data:', err);
      setDataSourceStatus('error');
      setErrorMessage(
        err instanceof Error ? err.message : 'Error communicating with backend API.'
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(startDate, endDate, decisionHour);
  }, [loadData, startDate, endDate, decisionHour]);

  const handleFilterChange = (start: string, end: string, hour: number) => {
    setStartDate(start);
    setEndDate(end);
    setDecisionHour(hour);
  };

  const handleRefresh = () => {
    loadData(startDate, endDate, decisionHour);
  };

  const activeTabTitle = {
    overview: 'Overview',
    explorer: 'Forecast Explorer',
    accuracy: 'Accuracy Analysis',
    quality: 'Data Ingestion Quality',
    methodology: 'Methodology and Governance',
  }[activeTab];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header
        evaluationPeriod={`${startDate} to ${endDate}`}
        decisionHour={decisionHour}
        lastFetchTime={overview?.last_successful_fetch || null}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        dataSourceStatus={dataSourceStatus}
        errorMessage={errorMessage}
      />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 grow w-full">
        {/* Navigation Tabs */}
        <nav aria-label="Dashboard sections" className="flex border-b border-slate-200 mb-6 overflow-x-auto space-x-1 sm:space-x-4">
          <button
            onClick={() => setActiveTab('overview')}
            aria-pressed={activeTab === 'overview'}
            aria-controls="dashboard-content"
            className={`py-2.5 px-3 border-b-2 text-xs sm:text-sm font-medium flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'overview'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Overview</span>
          </button>

          <button
            onClick={() => setActiveTab('explorer')}
            aria-pressed={activeTab === 'explorer'}
            aria-controls="dashboard-content"
            className={`py-2.5 px-3 border-b-2 text-xs sm:text-sm font-medium flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'explorer'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>Forecast Explorer</span>
          </button>

          <button
            onClick={() => setActiveTab('accuracy')}
            aria-pressed={activeTab === 'accuracy'}
            aria-controls="dashboard-content"
            className={`py-2.5 px-3 border-b-2 text-xs sm:text-sm font-medium flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'accuracy'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Accuracy Analysis</span>
          </button>

          <button
            onClick={() => setActiveTab('quality')}
            aria-pressed={activeTab === 'quality'}
            aria-controls="dashboard-content"
            className={`py-2.5 px-3 border-b-2 text-xs sm:text-sm font-medium flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'quality'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Data Ingestion Quality</span>
          </button>

          <button
            onClick={() => setActiveTab('methodology')}
            aria-pressed={activeTab === 'methodology'}
            aria-controls="dashboard-content"
            className={`py-2.5 px-3 border-b-2 text-xs sm:text-sm font-medium flex items-center space-x-2 transition-colors whitespace-nowrap ${
              activeTab === 'methodology'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Methodology & Governance</span>
          </button>
        </nav>

        {/* Global KPI Summary */}
        <KpiRow
          metrics={overview?.metrics || null}
          latestForecast={overview?.latest_forecast || null}
          isLoading={isLoading}
        />

        {!isLoading &&
          forecastSeries &&
          !forecastSeries.records.some(
            (record) => record.forecast_available || record.actual_available
          ) && (
            <div
              role="status"
              className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
            >
              No forecast or actual observations were returned for this period.
              Check the selected dates or refresh the Elexon data.
            </div>
          )}

        <section
          id="dashboard-content"
          aria-label={`${activeTabTitle} content`}
        >
        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div>
            <ForecastChart
              records={forecastSeries?.records || []}
              isLoading={isLoading}
            />
            <ErrorChart
              records={forecastSeries?.records || []}
              isLoading={isLoading}
            />
            {overview?.data_quality && (
              <DataQualityPanel
                stats={overview.data_quality}
                isLoading={isLoading}
              />
            )}
          </div>
        )}

        {/* Tab 2: Forecast Explorer */}
        {activeTab === 'explorer' && (
          <div>
            <ForecastExplorer
              records={forecastSeries?.records || []}
              startDate={startDate}
              endDate={endDate}
              decisionHour={decisionHour}
              onFilterChange={handleFilterChange}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Tab 3: Accuracy Analysis */}
        {activeTab === 'accuracy' && (
          <div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <ErrorDistributionChart
                distribution={accuracy?.error_distribution || []}
                isLoading={isLoading}
              />
              <HourlyMetricsChart
                hourlyMetrics={accuracy?.hourly_metrics || []}
                isLoading={isLoading}
              />
            </div>
            <DailyMetricsChart
              dailyMetrics={accuracy?.daily_metrics || []}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Tab 4: Data Quality */}
        {activeTab === 'quality' && (
          <div>
            {overview?.data_quality && (
              <DataQualityPanel
                stats={overview.data_quality}
                isLoading={isLoading}
              />
            )}
          </div>
        )}

        {/* Tab 5: Methodology */}
        {activeTab === 'methodology' && (
          <MethodologyPanel />
        )}
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-auto py-5 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-800">WindScope UK v1.0.0</span>
            <span>•</span>
            <span>UK Electricity Procurement Decision Support Platform</span>
          </div>
          <div className="flex items-center space-x-4">
            <a
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream"
              target="_blank"
              rel="noreferrer"
              className="text-teal-600 hover:text-teal-800 underline"
            >
              Elexon FUELHH API
            </a>
            <a
              href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream"
              target="_blank"
              rel="noreferrer"
              className="text-teal-600 hover:text-teal-800 underline"
            >
              Elexon WINDFOR API
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
