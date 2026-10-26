# Architecture

WindScope UK is a single-service web application with a React SPA and a FastAPI
API. On each evaluation, the API requests Elexon BMRS data, normalizes it,
records successfully retrieved WINDFOR revisions in a local SQLite archive,
merges fetched and archived revisions, and applies the decision cutoff. API
responses also use a process-local TTL cache. There is no scheduled/background
ingestion process. The production Dockerfile builds the SPA and copies its
output beside the backend; FastAPI serves the built static assets.

```text
Browser (React, TypeScript, Vite)
  │ /api requests (same origin in container; Vite proxy in development)
  ▼
FastAPI routes ── process-local TTL response cache
  │
  ├── Elexon FUELHH → WIND filter → UTC normalize → deduplicate → hourly actuals
  └── Elexon WINDFOR → UTC normalize → SQLite archive
                             │
                    fetched + archived revisions
                             │
Hourly actuals ──────────────┴──> cutoff selection → metrics and quality
                                             │
                                   JSON API / filtered CSV
```

## Backend boundaries

- `app/services/elexon_client.py`: bounded HTTP timeouts, retry handling, and
  JSON response checks for the two fixed Elexon dataset endpoints.
- `data_normalization.py`: UTC timestamp parsing, numeric validation,
  duplicate handling, and half-hourly-to-hourly actual aggregation.
- `forecast_selection.py`: target-hour construction and latest-eligible
  publication selection.
- `accuracy_metrics.py`: independently testable metrics and aggregations.
- `data_quality.py`: observation and source-quality counts.
- `api/routes.py`: input validation, cache, responses, and CSV generation.
- `forecast_archive.py`: durable local SQLite storage and retrieval of
  successfully fetched WINDFOR revisions. It is not a complete source-of-record
  archive: records unavailable at first capture cannot be restored.

## Frontend and deployment

The React application requests overview, forecast series, and accuracy
responses using the active date and decision-hour filters. Development uses
Vite's `/api` proxy to port 8000. In the consolidated container, the SPA and
API share an origin. `CORS_ORIGINS` can allow separate origins, but no
production origin has been configured or verified. The application still
requires successful Elexon requests for evaluations; it does not operate as an
archive-only offline service.

The archive defaults to `backend/data/windfor.sqlite3`. Docker Compose
configures `/app/data/windfor.sqlite3` and persists it using the
`windscope-data` named volume. Retaining/backing up that volume is an operator
responsibility.

`docker compose config --quiet` validates the Compose configuration. Docker
image build/start was not run because the local Docker daemon was unavailable.
See the [completion audit](./assignment-completion-audit.md) for verification
evidence and remaining limits.
