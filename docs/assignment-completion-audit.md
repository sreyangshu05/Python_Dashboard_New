# Assignment Completion Audit

Audit scope: repository state and executable checks in this workspace,
including a bounded live Elexon request on 2026-10-25. Statuses mean:
**PASS** verified within stated scope; **PARTIAL** implemented but not fully
verified or bounded; **FAIL** known unmet requirement; **BLOCKED** external
environment/access prevents verification; **NOT APPLICABLE** not required.
No requirement is marked not applicable.

## Evidence and baseline

- Before edits, `python -m pytest backend/tests -q`: 40 passed.
- Before edits, `cd frontend; npm run build`: TypeScript and Vite succeeded
  with a bundle-size advisory.
- A clean CPython 3.14.0 virtual environment installed every pinned backend
  requirement from wheels; `pip check` reported no broken requirements and
  `python -m pytest backend/tests -q` passed all 63 tests. This required
  upgrading Pydantic from 2.10.4 to 2.12.5 (to obtain a Python 3.14-compatible
  `pydantic-core`) and pandas from 2.2.3 to 2.3.3 (pandas 2.2.3 crashed during
  datetime normalization under Python 3.14). Python 3.11 was not available as
  an interpreter in this validation environment; pip successfully resolved
  the full pinned dependency set to CPython 3.11 Windows wheels, and the Docker
  runtime remains configured for Python 3.11.
- After edits, `cd frontend; npm run build`: succeeded; Vite still warns that
  the minified JS chunk exceeds 500 kB (latest build: 679.20 kB minified,
  195.03 kB gzip).
- Browser checks against the built SPA verified all five sections, refresh,
  date/cutoff application, human-readable date search, status filtering,
  ascending/descending keyboard sorting, pagination, and filtered CSV URL.
  The same replay found no browser console or page errors. At 390px and 320px
  viewport widths, document scroll width matched the visible viewport; the
  tab strip and data table retain their own horizontal scrolling.
- Focused manual accessibility checks verified associated labels on all five
  explorer fields, named controls, column scopes and sort state, keyboard
  sorting, dashboard navigation state, and accessible names for all five
  charts. This is not a formal WCAG certification or automated axe scan.
- CORS preflight tests return 200 with the configured local origin and reject
  an unconfigured origin with 400 and no allow-origin header.
- WINDFOR revisions returned by successful source fetches are stored in a
  SQLite archive and merged into later evaluations. Tests verify durable
  reopen, publication-time range filtering, duplicate handling, and retaining
  an earlier cutoff-eligible revision when a later source response only has a
  post-cutoff revision. A live request fetched 20,440 WINDFOR records, and
  19,856 distinct `(startTime, publishTime)` revisions were saved to the local
  archive. Compose mounts a named persistent data volume.
- `docker compose config --quiet`: passed. Docker CLI is installed, but the
  Linux Docker daemon is not running, so container execution is blocked.
- Live Elexon requests succeeded. January 2026 yielded 1,536 FUELHH records
  and 20,440 WINDFOR revisions. Live Uvicorn `/api/health`, `/api/overview`,
  `/api/forecasts`, `/api/accuracy`, `/api/data-quality`, filtered
  `/api/export.csv`, and the SPA root returned HTTP 200; invalid filters
  returned 422. `/api/forecasts` returned 744 hourly records and 744 matched
  hours. Overview reported MAE `2142.12 MW` and MBE `1851.9 MW` over 744
  observations for that run. A bounded WINDFOR query
  returned multiple revisions for Jan 15 12:00 UTC; the 07:30 publication
  (`11,049 MW`) was eligible at the previous-day 09:00 cutoff, while 09:30
  (`11,178 MW`) was after it.
- A browser session showed live KPIs and charts, exercised the explorer and
  navigation controls, and checked desktop/mobile widths. Docker execution and
  cloud publication were not performed.
- No Git remote is configured. No production deployment URL is known.
- No dedicated secret-scanning executable (`gitleaks`, `trufflehog`, or
  `detect-secrets`) is installed; the earlier heuristic scan is not equivalent
  to a full secret scan.

## Requirement matrix

### A. Business requirements (10)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| A01 | UK utility day-ahead procurement decision support; product and UI descriptions | PASS | — |
| A02 | National wind forecast presentation; forecast chart and API | PASS | Live dashboard and chart views exercised in browser. |
| A03 | Quantitative forecast accuracy; metrics endpoint and tested formulas | PASS | — |
| A04 | January 2026 evaluation defaults; configured and live-requested | PASS | — |
| A05 | Elexon FUELHH actual source; live request succeeded | PASS | — |
| A06 | Actuals filtered with `fuelType=WIND`; client parameter and normalization guard | PASS | — |
| A07 | Elexon WINDFOR source; live request succeeded | PASS | — |
| A08 | Publication timestamps and target timestamps kept distinct; response schema and live records | PASS | — |
| A09 | Actual/forecast target matching; UTC hourly alignment and complete 744-hour integration response | PASS | — |
| A10 | Only the two specified generation datasets; no other production datasets in code | PASS | — |

### B. Historical forecast correctness (10)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| B01 | Decision timestamp policy is defined as prior-day 09:00 UTC by default | PASS | — |
| B02 | Publication and target timestamp fields are distinct | PASS | — |
| B03 | Latest eligible revision selected; unit test and live historical example | PASS | — |
| B04 | Revisions after cutoff excluded; tests and live comparison | PASS | — |
| B05 | Historical revision availability investigated using bounded API requests | PASS | Evidence is limited to queried period/targets. |
| B06 | Historical revisions remain available after successful retrieval | PASS | SQLite archive protects captured revisions; it cannot recover records unavailable before their first capture. Docker deployments must retain the `windscope-data` volume and backups. |
| B07 | Missing forecasts explicit; all hours are emitted with nullable fields | PASS | — |
| B08 | Evaluation and selection assumptions documented in methodology | PASS | — |
| B09 | UTC timezone normalization, equivalent timezone and spring/fall DST-day tests | PASS | — |
| B10 | Evaluation period and preceding decision date represented separately | PASS | — |

### C. Quantitative analysis (15)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| C01 | MAE formula; acceptance fixture verifies 10 MW | PASS | — |
| C02 | RMSE formula; acceptance fixture verifies 10 MW | PASS | — |
| C03 | MAPE formula; acceptance fixture verifies 10% | PASS | — |
| C04 | MBE formula; acceptance fixture verifies 0 MW | PASS | — |
| C05 | Signed error is `forecast - actual`; positive and negative tests | PASS | — |
| C06 | Non-finite values excluded; normalization and metric tests | PASS | — |
| C07 | Missing values are not filled with zero; nullable records and tests | PASS | — |
| C08 | Zero actuals excluded from MAPE; all-zero and mixed tests | PASS | — |
| C09 | Valid observation count returned by API metric model | PASS | — |
| C10 | Missing, non-finite, and zero-actual exclusions reported | PASS | — |
| C11 | MW and percent units documented in schemas and methodology | PASS | — |
| C12 | Empty results return null metrics | PASS | — |
| C13 | Actual duplicates and identical forecast publication duplicates handled explicitly | PASS | — |
| C14 | Metrics calculate only on finite matched observations | PASS | — |
| C15 | Production values come from upstream; fixtures explicitly identified as synthetic tests | PASS | — |

### D. Frontend (18)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| D01 | React frontend production build succeeds | PASS | — |
| D02 | Evaluation period displayed from active filters | PASS | — |
| D03 | KPI cards use backend responses | PASS | Live returned values verified in browser. |
| D04 | Forecast/actual chart rendered with live data in headless Edge | PASS | — |
| D05 | Forecast error bars rendered with live data in headless Edge | PASS | — |
| D06 | Error distribution chart is implemented and receives backend bins | PASS | Accuracy view and accessible chart name verified in browser. |
| D07 | Date and decision-time filters are sent with API requests | PASS | — |
| D08 | Forecast publication timestamp is available in explorer data | PASS | — |
| D09 | Data-quality information is surfaced in UI | PASS | — |
| D10 | Loading/skeleton states implemented | PASS | — |
| D11 | Explicit empty-data presentation | PASS | Empty upstream results produce a status banner; build and backend empty-data tests pass. |
| D12 | API error state and message implemented | PASS | — |
| D13 | CSV export URL carries current date/cutoff filters | PASS | API route supports filtered output. |
| D14 | Responsive CSS/layout patterns exist | PASS | Browser viewport checks at 390px and 320px; no document-level horizontal overflow. |
| D15 | Navigation and controls are wired in source | PASS | Browser verified all views, refresh, filters, date application, search, sorting, pagination, and CSV URL. |
| D16 | Console error-free operation | PASS | No console or page errors during the final interaction replay. |
| D17 | No fabricated production metrics; loading errors clear stale data | PASS | — |
| D18 | Readable labels and accessible control names exist | PASS | Focused manual review covered associated field labels, named buttons, keyboard sorting, table sort semantics, navigation state, and chart names; no formal WCAG certification. |

### E. Backend (15)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| E01 | FastAPI app starts under TestClient and serves API | PASS | — |
| E02 | Health, overview, forecasts, accuracy, quality, export routes exist | PASS | Live check completed for `/api/forecasts`; others have mocked route tests. |
| E03 | Date range and decision hour validated; invalid-input tests added | PASS | — |
| E04 | Pydantic response contracts cover metrics and quality counts | PASS | — |
| E05 | Upstream errors are explicit; retryable server errors, non-retryable errors, and malformed response shapes tested | PASS | — |
| E06 | HTTP timeout and bounded retries configured | PASS | — |
| E07 | UTC parsing, numeric validation, dedupe, and hourly aggregation implemented | PASS | — |
| E08 | Forecast selector independent of HTTP/frontend layer | PASS | — |
| E09 | Metric services independently tested | PASS | — |
| E10 | CORS origins configurable for known local origins | PASS | Preflight tests confirm configured local origin is allowed and an unconfigured origin is rejected. |
| E11 | Useful logs avoid logging credentials | PASS | — |
| E12 | Health endpoint returns service/config/time, not upstream readiness | PASS | Endpoint is explicitly documented as liveness-only and verified without probing Elexon. |
| E13 | CSV includes requested date and cutoff filters | PASS | — |
| E14 | OpenAPI docs exposed at `/api/docs` | PASS | — |
| E15 | Fixed static asset mount replaces unsafe path joining | PASS | — |

### F. Testing (12)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| F01 | Backend unit tests; 63 pass on CPython 3.14.0 | PASS | Python 3.11 test execution remains unverified. |
| F02 | Forecast selection revision tests | PASS | — |
| F03 | Metric acceptance tests | PASS | — |
| F04 | Equivalent timezone and 23/25-hour DST day handling tested | PASS | — |
| F05 | Empty, missing, zero, non-finite, and duplicate edge cases covered | PASS | — |
| F06 | API route/contract tests | PASS | Most route data is fixture-mocked. |
| F07 | Frontend TypeScript check succeeds in build | PASS | — |
| F08 | Frontend production bundle builds | PASS | Bundle-size advisory remains. |
| F09 | Live API integration via TestClient and real Elexon data | PASS | `/api/forecasts` verified. |
| F10 | Docker startup test | BLOCKED | Docker daemon unavailable. |
| F11 | Regression tests added for repaired behavior | PASS | — |
| F12 | Test fixture data labeled synthetic and separate from production | PASS | — |

### G. Docker and deployment (14)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| G01 | `docker compose config --quiet` succeeds | PASS | — |
| G02 | Docker Compose service start | BLOCKED | Docker daemon unavailable. |
| G03 | Single-service production networking and port mapping configured | PASS | Runtime not exercised. |
| G04 | Docker healthcheck points to API health path | PARTIAL | Container health behavior not executed; API health is shallow. |
| G05 | Environment names documented in `.env.example` and README | PASS | — |
| G06 | Elexon and frontend API base URLs configurable | PASS | — |
| G07 | Production frontend uses same-origin `/api`, not localhost | PASS | — |
| G08 | Production CORS for deployment | PARTIAL | No deployed frontend origin to check. |
| G09 | Vercel/Heroku deployment | BLOCKED | No deployment credentials, remote, or platform configuration available. |
| G10 | Deployed frontend reachability | BLOCKED | No verified deployment URL. |
| G11 | Deployed backend reachability | BLOCKED | No verified deployment URL. |
| G12 | Deployed frontend/backend communication | BLOCKED | No deployment exists to test. |
| G13 | Live source loading works; errors are explicit | PASS | Bounded requests and live API integration succeeded. |
| G14 | Actual deployment URLs recorded | BLOCKED | No deployment URL exists. |

### H. GitHub and documentation (16)

| ID | Requirement / evidence | Status | Remediation or scope |
|---|---|---|---|
| H01 | Public repository or prepared publication steps | BLOCKED | No Git remote or repository URL is configured. |
| H02 | Anonymous repository name | BLOCKED | Cannot create a repository without authenticated access and a chosen identity. |
| H03 | No committed credentials | PARTIAL | No `.env` file or remote found; a full secret-scanner was not available/run. |
| H04 | README product overview | PASS | Updated. |
| H05 | README stack matches manifests | PASS | React/TypeScript versions corrected. |
| H06 | README repository structure | PASS | Includes supporting docs. |
| H07 | README startup commands | PASS | Matches current scripts and ports. |
| H08 | Environment variables documented | PASS | Timeout, retries, CORS, host, and port included. |
| H09 | Test commands documented | PASS | — |
| H10 | Data sources and methodology documented | PASS | Dedicated methodology document added. |
| H11 | README includes actual deployment URL | BLOCKED | No deployment URL verified. |
| H12 | AI usage disclosed | PASS | Completion assistance disclosed; submitter should add any earlier tools. |
| H13 | Known limitations disclosed | PASS | — |
| H14 | Client presentation exists and avoids unsupported production metrics | PASS | Updated. |
| H15 | Technical walkthrough explains architecture and real-source example | PASS | Unsupported sample values replaced with observed records. |
| H16 | Documentation avoids unverified success claims | PASS | Reviewed README, presentation, and walkthrough; bounded retention/cutoff claims and removed unsupported enterprise-grade, guarantee, and performance wording. |

## Totals and remaining blockers

**110 requirements audited:** 97 PASS, 3 PARTIAL, 10 BLOCKED, 0 FAIL, 0 NOT
APPLICABLE. These are categorical counts, not a weighted completion score.
The application is **functionally complete with documented external and
environment-verification blockers**, not fully verified.

Remaining items: Docker health behavior cannot be run until Docker Desktop is
available (G04); production CORS cannot be verified without a deployed origin
(G08); and a dedicated secret scan remains unavailable (H03). Elexon may not
return the complete historical revision set on an archive's first capture;
the application preserves only records actually received. The local and
Docker archives must be backed up and retained.
Deployment, public repository, and submission URLs remain blocked by the
absence of a configured remote, hosting account, and verified deployment.
No placeholder URL has been used.

The final accepted local checks were:

```powershell
python -m pytest backend\tests -q
Set-Location frontend
npm run build
Set-Location ..
docker compose config --quiet
```
