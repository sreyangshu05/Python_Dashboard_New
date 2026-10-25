# WindScope UK — Internal Technical Walkthrough & Architecture Review

**Target Audience:** Internal Technical Lead / Principal Software Engineer  
**Purpose:** Technical audit, architecture rationale, validation evidence, and engineering defense.

---

## 1. System Architecture

WindScope UK is architected as a clean, decoupled full-stack platform with strict boundaries between raw data ingestion, analytical normalization, quantitative evaluation, and presentation.

### Architecture Diagram

```
[ Elexon BMRS API ] (https://data.elexon.co.uk/bmrs/api/v1)
       │
       ├── FUELHH/stream (Actuals, 30-min settlement, fuelType="WIND")
       └── WINDFOR/stream (Forecasts, hourly, multiple revisions via publishDateTime)
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend Services                          │
│                                                                        │
│  ┌──────────────────────┐        ┌───────────────────────────────────┐ │
│  │   ElexonClient       │───────▶│   Data Normalization Pipeline     │ │
│  │  - Retry / Backoff   │        │  - UTC timestamp normalization    │ │
│  │  - Bounded timeouts  │        │  - Half-hourly ➔ Hourly aggregate │ │
│  │  - In-memory cache   │        │  - Deduplication & provenance     │ │
│  └──────────────────────┘        └───────────────────────────────────┘ │
│                                                    │                   │
│                                                    ▼                   │
│  ┌──────────────────────┐        ┌───────────────────────────────────┐ │
│  │ Accuracy Engine      │◀───────│ Forecast Selection Service        │ │
│  │  - MAE, RMSE, MBE    │        │  - Historical cutoff enforcement  │ │
│  │  - Zero-actual MAPE  │        │  - Latest valid revision argmax   │ │
│  │  - Diurnal & daily   │        │  - Zero future leakage guarantee  │ │
│  └──────────────────────┘        └───────────────────────────────────┘ │
│            │                                                           │
│            ▼                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ RESTful API Router (/api/overview, /forecasts, /accuracy, /export)│ │
│  └───────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON / CSV Streaming
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        React 18 / Vite Frontend                        │
│                                                                        │
│  - TypeScript strict typing (shared schemas)                          │
│  - Tailwind CSS v4 restrained enterprise visual language               │
│  - Recharts responsive time-series & distribution charts               │
│  - Tabbed analytics: Overview, Explorer, Accuracy, Quality, Governance │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Engineering & Design Decisions

### 2.1 Backend Technology Selection: Python + FastAPI + Pydantic + Pandas
* **FastAPI:** Chosen for native OpenAPI contract generation, strict Pydantic model validation, and high-performance asynchronous dispatch.
* **Synchronous Route Handlers (`def` vs `async def`):** Implemented synchronous `def` endpoints so FastAPI dispatches CPU/data-processing operations (Pandas aggregations, numpy array mathematics) to its internal threadpool (`run_in_threadpool`), avoiding event-loop blocking.
* **Pandas & NumPy:** Standard industry tools for high-precision time-series alignment, vector arithmetic, and quantile calculations.
* **In-Memory Parameterized Caching:** Implements an in-memory TTL cache with cache keys composed of `(prefix, eval_start, eval_end, decision_hour)`. This protects the public Elexon API from redundant load while ensuring that changing decision cutoffs immediately invalidates stale forecasts.

### 2.2 Frontend Technology Selection: React + TypeScript + Vite + Tailwind CSS + Recharts
* **React + Vite:** Rapid build times, zero legacy overhead, sub-second HMR, and ultra-compact production bundle (<200 kB gzipped JS).
* **Strict TypeScript:** All API response interfaces in `src/types/index.ts` mirror backend Pydantic models. Compile-time type checking prevents runtime `undefined` access.
* **Tailwind CSS v4:** Modern utility styling ensuring consistent spacing, accessible contrast ratios, and a restrained energy-analytics aesthetic.
* **Recharts:** Composable SVG charting providing responsive containers, custom tooltips with GMT/BST formatting, and dual-axis time alignment.

### 2.3 Single-Service vs Split Deployment Strategy
* **Consolidated Production Topology:** The FastAPI backend is configured to detect and serve the compiled React SPA (`frontend/dist`) directly in production, with fallback routing for single-page client navigation.
* **Multi-Stage Dockerfile:** Stage 1 uses `node:20-slim` to compile the Vite application; Stage 2 uses `python:3.11-slim` to run Uvicorn. This provides a single, portable, self-contained container with zero Node.js footprint in the runtime image.

---

## 3. Forecast Selection Correctness & Anti-Leakage Proof

### 3.1 The Problem of Future Information Leakage
In day-ahead electricity procurement, selecting a forecast published *after* the procurement decision was finalized creates false optimism (hindsight bias), invalidating the utility's backtest.

### 3.2 Formal Selection Rule
Let:
* $T$ = Target generation settlement period start (e.g., `2026-01-15 12:00 UTC`).
* $D$ = Procurement decision cutoff timestamp (e.g., `2026-01-14 09:00 UTC`).
* $\mathcal{F}(T) = \{ (p_i, g_i) \mid \text{startTime} = T \}$ be the set of forecast revisions targeting $T$, where $p_i$ is publication time and $g_i$ is forecasted generation in MW.

The selected forecast is determined by:
$$\text{Eligible}(T, D) = \{ (p_i, g_i) \in \mathcal{F}(T) \mid p_i \le D \}$$
$$\text{SelectedForecast}(T, D) = \begin{cases} \arg\max_{p_i} \text{Eligible}(T, D) & \text{if } \text{Eligible}(T, D) \ne \emptyset \\ \text{Unavailable} & \text{otherwise} \end{cases}$$

### 3.3 Concrete Example
Consider a target period $T = \text{2026-01-15 12:00 UTC}$ with decision cutoff $D = \text{2026-01-14 09:00 UTC}$:
* Revision 1: Published `2026-01-14 04:30 UTC`, Generation = `12,500 MW` ($\le D$ ➔ Eligible)
* Revision 2: Published `2026-01-14 07:30 UTC`, Generation = `13,100 MW` ($\le D$ ➔ Eligible, latest before cutoff)
* Revision 3: Published `2026-01-14 11:30 UTC`, Generation = `14,200 MW` ($> D$ ➔ Excluded)
* Revision 4: Published `2026-01-15 02:30 UTC`, Generation = `14,800 MW` ($> D$ ➔ Excluded)

**Outcome:** Revision 2 (`13,100 MW`) is strictly selected. Revisions 3 and 4 are quarantined and counted in `forecasts_excluded_after_cutoff`.

---

## 4. Data Quality & Normalization Mechanics

### 4.1 Resolution Mismatch Handling
* **WINDFOR:** Published at 60-minute resolution (hourly).
* **FUELHH:** Published at 30-minute settlement period resolution (half-hourly).
* **Resolution Engine:** Two consecutive half-hourly actuals ($T$ and $T + \text{30min}$) are grouped by `dt.floor('h')` and averaged:
  $$\text{Actual}_{\text{hourly}}(T) = \frac{\text{Gen}(T) + \text{Gen}(T + \text{30min})}{2}$$
  The count of settlement periods averaged is tracked in `sp_count`.

### 4.2 Deduplication Rules
* If multiple FUELHH records are returned with identical `startTime`, the record with the latest `publishTime` is retained; older duplicates are dropped and recorded in `duplicate_actuals_removed`.
* For WINDFOR, duplicate `startTime` records with different `publishTime` values represent valid historical revisions and are preserved for decision cutoff filtering.

### 4.3 Missing Observation Transparency
* If no forecast satisfies $p_i \le D$, `forecast_available` is set to `False` and `forecast_generation_mw` is set to `null` with an explicit reason logged in `exclusion_reason`.
* Missing actuals or forecasts are never filled with synthetic zeros.

---

## 5. Quantitative Error Metrics Engine

### 5.1 Error Sign Convention
$$\text{error}_i = \text{forecast}_i - \text{actual}_i$$
* **$\text{error} > 0$ (Positive):** Overforecast. Predicted supply exceeded reality. In procurement terms: risk of procuring surplus volume.
* **$\text{error} < 0$ (Negative):** Underforecast. Realized supply exceeded prediction. In procurement terms: potential deficit risk if relying on wind.

### 5.2 Mathematical Formulations
1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\text{forecast}_i - \text{actual}_i| \quad [\text{MW}]$$
2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\text{forecast}_i - \text{actual}_i)^2} \quad [\text{MW}]$$
3. **Mean Bias Error (MBE):**
   $$\text{MBE} = \frac{1}{N} \sum_{i=1}^N (\text{forecast}_i - \text{actual}_i) \quad [\text{MW}]$$
4. **Mean Absolute Percentage Error (MAPE):**
   $$\text{MAPE} = \frac{1}{N_{\text{valid}}} \sum_{i=1, \text{actual}_i > 0}^{N_{\text{valid}}} \frac{|\text{forecast}_i - \text{actual}_i|}{\text{actual}_i} \times 100\% \quad [\%]$$
   *Zero-actual handling:* Any record where $\text{actual}_i = 0$ is excluded from the MAPE calculation. The excluded count is reported in `mape_excluded_zero_actual`. If all observations are zero, MAPE returns `null` rather than $\infty$ or $0$.

---

## 6. Automated Testing Suite

All 40 automated tests pass cleanly across unit, integration, and API validation:

```
backend/tests/test_accuracy_metrics.py ...............                   [ 37%]
backend/tests/test_api.py ......                                         [ 52%]
backend/tests/test_data_normalization.py .........                       [ 75%]
backend/tests/test_forecast_selection.py ..........                      [100%]
======================= 40 passed in 3.38s =======================
```

### Coverage Highlights:
* **Acceptance Criteria D-I:** Explicit unit tests verifying MAE=10, RMSE=10, MBE=0, MAPE=10% for `[110, 90]` vs `[100, 100]`.
* **Zero-Actual Isolation:** Confirmed exclusion of zero actuals from MAPE denominator.
* **Anti-Leakage Verification:** Ensured forecasts published after cutoff are quarantined.
* **Deduplication & Timestamp Parsing:** Verified UTC offset parsing and half-hourly aggregation.
* **API Route Mocking:** Validated overview, forecasts, accuracy, and CSV streaming responses.

---

## 7. Answers to Likely Technical Review Questions

### Q1: How do you know that the selected forecast was available at the decision time?
**Answer:** The Elexon WINDFOR dataset contains an explicit `publishTime` field for each forecast revision. When fetching via `publishDateTimeFrom/To`, Elexon preserves all historical forecast publications. Our selection service evaluates $\text{publishTime} \le D$ strictly. If a publication occurred even one second after $D$, it is excluded.

### Q2: What happens if the source API exposes only the latest forecast?
**Answer:** During our initial Phase 1 API probe, we tested both query modes:
- `from/to` (target time filter): Returns only the single latest forecast revision.
- `publishDateTimeFrom/To` (publish time filter): Returns all historical forecast revision cycles.
If the API were ever changed to only expose the latest forecast, our service would detect the lack of multiple `publishTime` records, log an explicit warning in `DataQualityStats`, and present the visualization as a "latest available snapshot comparison" rather than a historical backtest.

### Q3: How are missing actuals handled?
**Answer:** Missing actuals remain `null`. The record is flagged with `actual_available = False`, and error metrics are not computed for that period. Missing periods are never silently imputed with zero.

### Q4: Why use MAE and RMSE together?
**Answer:** MAE measures the average volumetric error across the month. RMSE penalizes large errors quadratically ($e^2$). In power systems, a single 4,000 MW error creates far greater grid-balancing distress and cash-out penalty risk than four separate 1,000 MW errors. The spread between RMSE and MAE indicates error variance and fat-tailed distribution.

### Q5: Why can MAPE become misleading?
**Answer:** When actual wind output drops near zero (e.g., calm summer or winter conditions with 50 MW generated), a minor 150 MW forecast error produces a 300% error. Conversely, when wind is generating 18,000 MW, a 1,000 MW error is only 5.5%. MAPE over-weights low-generation periods. WindScope UK isolates zero-actual observations and recommends evaluating MAE and RMSE in conjunction with MAPE.

### Q6: How would you scale the ingestion pipeline?
**Answer:** For an enterprise production deployment:
1. Schedule a Celery / Temporal cron job polling the Elexon stream every 15 minutes.
2. Persist ingested records into a partitioned PostgreSQL / TimescaleDB table indexed on `(startTime, publishTime)`.
3. Pre-compute daily and hourly accuracy metrics in materialized views to serve procurement analysts with sub-10ms response times.

### Q7: Why did you choose this architecture?
**Answer:** For a 16-hour delivery budget, this architecture provides maximum reliability, zero unnecessary database overhead, strict separation of concerns, complete testability, and can be containerized and run with a single `docker compose up`.

### Q8: What would you improve with another two days?
**Answer:**
1. Implement persistent TimescaleDB storage with continuous background sync.
2. Add probabilistic ensemble percentile bands (P10/P50/P90).
3. Integrate Day-Ahead System Buy/Sell Prices (SBP/SSP) to estimate indicative financial cash-out impact.
4. Add automated alerts via Slack/Email when forecast revisions exceed volatility thresholds.
