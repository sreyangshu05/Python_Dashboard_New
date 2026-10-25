import React from 'react';
import { BookOpen, AlertOctagon, HelpCircle, Check, ShieldAlert } from 'lucide-react';

export const MethodologyPanel: React.FC = () => {
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-xs mb-6 p-4 sm:p-6 text-slate-800 space-y-6">
      <div className="border-b border-slate-200 pb-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
          <BookOpen className="w-5 h-5 text-teal-600" />
          <span>Methodology, Mathematical Formulations & Analytical Limitations</span>
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Detailed documentation of data pipelines, forecast selection rules, accuracy metric formulations, and governance boundaries
        </p>
      </div>

      {/* 1. Datasets */}
      <section className="space-y-2">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-teal-800">
          1. Elexon BMRS Data Sources
        </h3>
        <p className="text-xs text-slate-600 leading-relaxed">
          WindScope UK consumes two official, public Elexon Balancing Mechanism Reporting Service (BMRS) streaming endpoints without alteration:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="border border-slate-200 rounded p-3 bg-slate-50">
            <h4 className="font-semibold text-slate-900">Actual Generation (FUELHH)</h4>
            <p className="text-slate-500 text-[11px] mt-0.5">Endpoint: <code>/datasets/FUELHH/stream</code></p>
            <ul className="list-disc list-inside mt-1.5 space-y-0.5 text-slate-600 text-[11px]">
              <li>Filter: <code>fuelType = 'WIND'</code></li>
              <li>Resolution: 30-minute settlement periods (48 periods per day)</li>
              <li>Unit: MW average generation across the half-hour</li>
              <li>Publication: Broadcast roughly at the close of each settlement period</li>
            </ul>
          </div>
          <div className="border border-slate-200 rounded p-3 bg-slate-50">
            <h4 className="font-semibold text-slate-900">Forecasted Generation (WINDFOR)</h4>
            <p className="text-slate-500 text-[11px] mt-0.5">Endpoint: <code>/datasets/WINDFOR/stream</code></p>
            <ul className="list-disc list-inside mt-1.5 space-y-0.5 text-slate-600 text-[11px]">
              <li>Fields: <code>startTime</code>, <code>publishTime</code>, <code>generation</code></li>
              <li>Resolution: Hourly forecasts (60-minute blocks)</li>
              <li>Cadence: Published approximately 8 times daily (02:30, 04:30, 07:30, 09:30, etc.)</li>
              <li>Historical revisions are preserved when filtering by <code>publishDateTimeFrom/To</code></li>
            </ul>
          </div>
        </div>
      </section>

      {/* 2. Selection & Matching Logic */}
      <section className="space-y-2">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-teal-800">
          2. Forecast Selection & Resolution Alignment
        </h3>
        <div className="space-y-2 text-xs text-slate-600 leading-relaxed">
          <p>
            <strong>The Historical Availability Guarantee:</strong> For any target settlement hour <span className="font-mono bg-slate-100 px-1 py-0.5 rounded">T</span>, let <span className="font-mono bg-slate-100 px-1 py-0.5 rounded">D</span> be the day-ahead procurement decision cutoff timestamp. The algorithm evaluates only forecasts satisfying:
          </p>
          <div className="bg-slate-100 p-2.5 rounded font-mono text-center text-slate-800 text-xs my-1">
            selected_forecast(T, D) = latest WINDFOR where (startTime == T and publishTime &le; D)
          </div>
          <p>
            Any revision published after <span className="font-mono">D</span> is strictly quarantined and excluded from that decision's backtest. This eliminates hindsight bias and guarantees zero future information leakage.
          </p>
          <p>
            <strong>Resolution Normalization:</strong> Because WINDFOR predicts generation on an hourly scale while FUELHH records actuals on a half-hourly scale, the two half-hourly periods <span className="font-mono">T</span> and <span className="font-mono">T+30min</span> are averaged into an hourly equivalent actual before computing error metrics.
          </p>
        </div>
      </section>

      {/* 3. Metrics */}
      <section className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider text-teal-800">
          3. Quantitative Error Formulations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="border border-slate-200 rounded p-3">
            <div className="font-semibold text-slate-900">Signed Error Convention</div>
            <div className="font-mono bg-slate-50 p-1.5 rounded my-1 text-slate-700">error = forecast − actual (MW)</div>
            <p className="text-slate-600 text-[11px]">
              Positive error indicates an <strong>overforecast</strong> (surplus generation predicted). Negative error indicates an <strong>underforecast</strong> (deficit risk).
            </p>
          </div>

          <div className="border border-slate-200 rounded p-3">
            <div className="font-semibold text-slate-900">Mean Absolute Error (MAE)</div>
            <div className="font-mono bg-slate-50 p-1.5 rounded my-1 text-slate-700">MAE = (1/N) * Σ |forecast_i − actual_i|</div>
            <p className="text-slate-600 text-[11px]">
              Expressed in MW. Represents average error magnitude without sign cancellation.
            </p>
          </div>

          <div className="border border-slate-200 rounded p-3">
            <div className="font-semibold text-slate-900">Root Mean Squared Error (RMSE)</div>
            <div className="font-mono bg-slate-50 p-1.5 rounded my-1 text-slate-700">RMSE = sqrt( (1/N) * Σ (forecast_i − actual_i)² )</div>
            <p className="text-slate-600 text-[11px]">
              Expressed in MW. Disproportionately penalizes large forecast errors, which carry high physical balancing severity.
            </p>
          </div>

          <div className="border border-slate-200 rounded p-3">
            <div className="font-semibold text-slate-900">Mean Bias Error (MBE)</div>
            <div className="font-mono bg-slate-50 p-1.5 rounded my-1 text-slate-700">MBE = (1/N) * Σ (forecast_i − actual_i)</div>
            <p className="text-slate-600 text-[11px]">
              Signed indicator of structural systematic bias. Near-zero MBE with high MAE indicates symmetrical dispersion.
            </p>
          </div>

          <div className="border border-slate-200 rounded p-3 md:col-span-2">
            <div className="font-semibold text-slate-900">Mean Absolute Percentage Error (MAPE) & Zero-Actual Treatment</div>
            <div className="font-mono bg-slate-50 p-1.5 rounded my-1 text-slate-700">MAPE = (1 / N_nonzero) * &Sigma; (|forecast_i &minus; actual_i| / actual_i) * 100% (for actual &gt; 0)</div>
            <p className="text-slate-600 text-[11px] mt-1">
              <strong>Crucial Edge Case Governance:</strong> When actual wind generation is zero, division by zero is mathematically undefined. WindScope UK strictly isolates and excludes all zero-actual observations from the MAPE denominator and reports the exclusion count transparently rather than returning infinity or artificial zero.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Strict Limitations & Disclaimers */}
      <section className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-xs space-y-2">
        <div className="flex items-center space-x-2 text-amber-900 font-bold">
          <ShieldAlert className="w-4 h-4 text-amber-600" />
          <span>Strict Analytical Boundaries & Disclaimers</span>
        </div>
        <ul className="list-disc list-inside space-y-1 text-amber-800 text-[11px]">
          <li>
            <strong>Forecast errors do not equal financial exposure or imbalance penalties:</strong> Utility financial imbalance depends on total system portfolio balancing, bilateral contract positions, system buy/sell prices (SBP/SSP), and cash-out mechanisms.
          </li>
          <li>
            <strong>Decision-support only:</strong> WindScope UK is a quantitative intelligence and decision-support tool. It does not perform automated algorithmic trading or dispatch optimization.
          </li>
          <li>
            <strong>No synthetic or fabricated data:</strong> All statistics reflect actual responses from Elexon BMRS API. No numbers are invented or smoothed with external weather models.
          </li>
        </ul>
      </section>
    </div>
  );
};
