# WindScope UK — Internal Technical Walkthrough & Architecture Review

**Target Audience:** Internal Technical Lead / Principal Software Engineer  
**Purpose:** Technical audit, architecture rationale, validation evidence, and engineering defense.

---

## 1. System Architecture

WindScope UK is a single-service full-stack application with separately
testable data-fetching, normalization, archive, selection, metric, and
presentation components. It performs source requests during evaluation; it
does not run a scheduled ingestion job.

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
│  └──────────────────────┘        │  - Deduplication & quality counts │ │
│                                  └───────────────────────────────────┘ │
│  ElexonClient ──▶ SQLite WINDFOR revision archive ──▶ selection       │
│                                                    │                   │
│                                                    ▼                   │
│  ┌──────────────────────┐        ┌───────────────────────────────────┐ │
│  │ Accuracy Engine      │◀───────│ Forecast Selection Service        │ │
│  │  - MAE, RMSE, MBE    │        │  - Historical cutoff enforcement  │ │
│  │  - Zero-actual MAPE  │        │  - Latest valid revision argmax   │ │
│  │  - Diurnal & daily   │        │  - Decision-cutoff enforcement    │ │
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
│                        React 19 / Vite Frontend                        │
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
* **React + Vite:** TypeScript frontend development and production bundling with Vite.
* **Strict TypeScript:** All API response interfaces in `src/types/index.ts` mirror backend Pydantic models. Compile-time type checking prevents runtime `undefined` access.
* **Tailwind CSS v4:** Utility styling for consistent spacing and a restrained energy-analytics aesthetic.
* **Recharts:** Composable responsive SVG charts with custom tooltips and UTC-aligned time series.

### 2.3 Single-Service vs Split Deployment Strategy
* **Consolidated Container Topology:** The FastAPI backend serves the compiled React SPA (`frontend/dist`) in the Docker image. The Docker runtime is configured for Python 3.11; backend test verification in this audit was performed on CPython 3.14, not 3.11.
* **Local revision archive:** Successfully fetched WINDFOR revisions are persisted in SQLite. The Compose deployment uses the `windscope-data` named volume. The archive cannot restore records unavailable before first capture, and the service still requires successful upstream requests to evaluate.
* **Deployment status:** Compose configuration validates, but container execution and public hosting have not been verified. There is no known public deployment URL.

---

## 3. Cutoff-Based Forecast Selection

### 3.1 Why Publication Time Matters
Selecting a known forecast published *after* an evaluation cutoff would use
information that was not eligible under that cutoff. This is a selection-rule
constraint, not proof that the source returned a complete historical revision
set.

### 3.2 Formal Selection Rule
Let:
* $T$ = Target generation settlement period start (e.g., `2026-01-15 12:00 UTC`).
* $D$ = Procurement decision cutoff timestamp (e.g., `2026-01-14 09:00 UTC`).
* $\mathcal{F}(T) = \{ (p_i, g_i) \mid \text{startTime} = T \}$ be the set of forecast revisions targeting $T$, where $p_i$ is publication time and $g_i$ is forecasted generation in MW.

The selected forecast is determined by:
$$\text{Eligible}(T, D) = \{ (p_i, g_i) \in \mathcal{F}(T) \mid p_i \le D \}$$
$$\text{SelectedForecast}(T, D) = \begin{cases} \arg\max_{p_i} \text{Eligible}(T, D) & \text{if } \text{Eligible}(T, D) \ne \emptyset \\ \text{Unavailable} & \text{otherwise} \end{cases}$$

### 3.3 Concrete Example
For target `2026-01-15T12:00:00Z` and cutoff `2026-01-14T09:00:00Z`, a bounded live Elexon query returned these revisions:
* `2026-01-14T02:30:00Z`: `11,049 MW` (eligible)
* `2026-01-14T04:30:00Z`: `11,049 MW` (eligible)
* `2026-01-14T07:30:00Z`: `11,049 MW` (latest eligible)
* `2026-01-14T09:30:00Z`: `11,178 MW` (after cutoff; excluded)

**Outcome:** the `07:30Z` revision (`11,049 MW`) is selected. The later `09:30Z` record is not eligible. The values above are observed source records for this target only, not a monthly performance claim.

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
   $$\text{MAPE} = \frac{1}{N_{\text{nonzero}}} \sum_{\text{actual}_i \ne 0} \frac{|\text{forecast}_i - \text{actual}_i|}{|\text{actual}_i|} \times 100\% \quad [\%]$$
   *Zero-actual handling:* Any record where $\text{actual}_i = 0$ is excluded from the MAPE calculation. The excluded count is reported in `mape_excluded_zero_actual`. If all observations are zero, MAPE returns `null` rather than $\infty$ or $0$.

---

## 6. Automated Testing Suite

All 63 backend tests passed in a clean CPython 3.14.0 environment on
2026-10-26. This does not claim that the suite was run on Python 3.11:

```
63 passed
```

### Coverage Highlights:
* **Metric examples:** Unit tests verify MAE=10, RMSE=10, MBE=0, MAPE=10% for `[110, 90]` vs `[100, 100]`.
* **Zero-Actual Isolation:** Confirmed exclusion of zero actuals from MAPE denominator.
* **Anti-Leakage Verification:** Ensured forecasts published after cutoff are quarantined.
* **Deduplication & Timestamp Parsing:** Verified UTC offset parsing and half-hourly aggregation.
* **API Route Mocking:** Validated overview, forecasts, accuracy, and CSV streaming responses.

---

## 7. Answers to Likely Technical Review Questions

### Q1: How do you know that the selected forecast was available at the decision time?
**Answer:** Each returned WINDFOR record has an explicit `publishTime`. A bounded Jan 2026 publication-time query returned multiple revisions for a target, which were checked against the cutoff. The selector requires `publishTime <= D`; one second after the cutoff is ineligible. This verifies the observed interval, not a guarantee of indefinite source retention.

### Q2: What happens if the source API exposes only the latest forecast?
**Answer:** The implementation queries a bounded `publishDateTimeFrom/To` interval. The current probe confirms multiple revisions for the tested January target. The application does not currently detect a future source-retention or query-semantics change; that remains a monitoring limitation.

### Q3: How are missing actuals handled?
**Answer:** Missing actuals remain `null`. The record is flagged with `actual_available = False`, and error metrics are not computed for that period. Missing periods are never silently imputed with zero.

### Q4: Why use MAE and RMSE together?
**Answer:** MAE is the mean absolute error for finite matched observations. RMSE gives larger errors more weight through squaring. Neither metric directly measures grid-balancing distress, cash-out exposure, or cost; those require additional system, contract, and price data and a validated model.

### Q5: Why can MAPE become misleading?
**Answer:** When actual wind output drops near zero (e.g., calm summer or winter conditions with 50 MW generated), a minor 150 MW forecast error produces a 300% error. Conversely, when wind is generating 18,000 MW, a 1,000 MW error is only 5.5%. MAPE over-weights low-generation periods. WindScope UK isolates zero-actual observations and recommends evaluating MAE and RMSE in conjunction with MAPE.

### Q6: How would you scale the ingestion pipeline?
**Answer:** For an enterprise production deployment:
1. Define operational freshness and retention requirements with data owners.
2. Evaluate whether the current SQLite archive is sufficient for the intended data volume, recovery, and concurrent access needs.
3. Benchmark representative workloads before selecting a database or introducing background ingestion and precomputed metrics.

### Q7: Why did you choose this architecture?
**Answer:** The services keep ingestion, normalization, selection, and metrics separately testable. The provided Compose configuration validates, but container execution still requires a running Docker daemon and has not been verified here.

### Q8: What would you improve with another two days?
**Answer:**
1. Define monitoring and recovery expectations for upstream requests and the local archive.
2. Add probabilistic ensemble percentile bands (P10/P50/P90).
3. Only consider financial analysis after defining required market, contract, and validation inputs.
4. Add automated alerts via Slack/Email when forecast revisions exceed volatility thresholds.
