# GB Wind Forecast Monitor

A web app for a UK utility's day-ahead power procurement team. It shows the **latest national wind generation forecast that was available when the purchase decision had to be made**, and measures **how accurate those forecasts were**, so that buyers can size the extra power to procure beyond wind.

**Live app:** https://kuyhu-zeta.vercel.app

Scope: national-level wind only, Elexon BMRS data only, delivery days in January 2026.

> **AI assistance:** this project was developed with the help of AI tools (Claude Code). It was used for API exploration, code generation, tests and documentation. The author reviewed every result and checked the numbers with an independent script (see [Verification](#verification)).

---

## Key results (January 2026, 09:30 cutoff)

| Metric | Value |
|---|---|
| MAE | 2,107 MW (18.2% of mean actual) |
| RMSE | 2,611 MW |
| Mean bias (forecast − actual) | **+1,840 MW**: the forecast systematically over-predicts |
| P50 / P90 / P95 / P99 \|error\| | 1,707 / 4,377 / 5,401 / 6,213 MW |
| MAPE | 21.9% |

Error grows with lead time, from about 1.8 GW MAE at 0–6h to about 2.4 GW at 42h and beyond. Because bias is strongly positive, a buyer who trusted the raw forecast would usually have **under-bought**.

## Assumptions and domain logic

| Topic | Decision |
|---|---|
| **Decision cutoff** | For delivery day D (a Europe/London calendar day), the decision is made on **D-1 at 09:30 Europe/London** by default. This sits around the morning GB day-ahead auction gate closure. The cutoff can be changed in the UI and with the `cutoff=HH:MM` API parameter. It is converted to UTC per day, so it is DST-safe. |
| **Latest available forecast** | For each target hour, the WINDFOR row with the **maximum `publishTime` ≤ cutoff** (inclusive). Forecasts published after the cutoff are never used. |
| **Horizon** | `startTime − publishTime` in hours. Rows with a negative horizon are discarded (WINDFOR does contain them, down to about −25h). With a 09:30 cutoff, the horizons used are 14.5–37.5h. |
| **Granularity** | WINDFOR is **hourly** and FUELHH is **half-hourly**. Accuracy is measured at each forecast hour against the actual for the half-hour starting at that time, with no interpolation. Charts show the full half-hourly actual series. |
| **Error** | `error = forecast − actual` (MW). Positive means wind was over-forecast, which is the risky direction for a buyer. |
| **Metrics** | MAE, RMSE, mean bias, P50/P90/P95/P99 of \|error\|, MAE as % of mean actual, and MAPE (computed only over hours with actual > 0 to avoid division by zero). Breakdowns by London hour of day, by delivery day, and by 6h horizon bucket. |
| **Error by horizon** | Uses **all** forecast vintages for the target days, not only the latest one before the cutoff. This shows how accuracy degrades with lead time independently of the cutoff choice. |
| **Risk-adjusted lower bound** | `forecast − P90(signed error)`, computed over the selected period **excluding the chosen day**, so the day's own outcome does not leak into its buffer. Buying to cover this lower bound would have covered the wind shortfall in about 90% of historic hours. |
| **Timezones** | Stored and transported in UTC (ISO 8601). Shown in Europe/London. |
| **Data cleaning** | The fetch script keeps only `fuelType == "WIND"`, drops null generation, de-duplicates (latest publish per settlement period for actuals, and unique `(publishTime, startTime)` pairs for forecasts) and drops negative horizons. |

## Repository structure

```
.
├── api/index.py              # Vercel Python serverless entrypoint (re-exports the FastAPI app)
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + CORS
│   │   ├── models.py         # Pydantic response schemas
│   │   ├── api/routes.py     # /api endpoints and input validation
│   │   ├── data/loader.py    # Loads the bundled CSV snapshot (cached)
│   │   ├── data/cleaning.py  # Dedup, WIND filter, plausibility flags, gap detection (pure functions)
│   │   └── services/
│   │       ├── selection.py  # Cutoff and "latest forecast ≤ cutoff" logic
│   │       ├── metrics.py    # Error metrics and breakdowns
│   │       └── decision.py   # Decision-day view and P90 risk buffer
│   ├── data/                 # actuals.csv, forecasts.csv (cleaned snapshot, UTC) + quality.json
│   ├── scripts/
│   │   ├── fetch_data.py     # Pulls FUELHH + WINDFOR from Elexon (chunked, retries), cleans, writes snapshot
│   │   ├── sanity_check.py   # Independent stdlib re-computation vs the API
│   │   └── check_core_coverage.sh
│   ├── tests/
│   │   ├── unit/             # selection, metrics, cleaning: hand-computed fixtures
│   │   ├── api/              # TestClient: schemas, validation, CORS, headers, timing
│   │   └── data/             # snapshot integrity, ingestion (mocked HTTP), opt-in live test
│   └── Dockerfile            # non-root
├── frontend/
│   ├── e2e/                  # Playwright: flows, a11y (axe), API smoke; 375/768/1440 px
│   ├── src/**/*.test.tsx     # Vitest + Testing Library + MSW
│   ├── lighthouserc.cjs, playwright.config.ts, scripts/check-bundle.mjs
│   ├── src/
│   │   ├── App.tsx           # Layout, tabs, shared controls (day, range, cutoff)
│   │   ├── views/            # DecisionView, AccuracyView, Methodology
│   │   ├── components/ui.tsx # Cards, legend, tooltip, loading/error states
│   │   ├── api.ts            # Typed API client
│   │   ├── hooks.ts          # useApi (fetch + stale-response guard), theme colors for charts
│   │   ├── series.ts         # Aligns hourly forecasts with half-hourly actuals
│   │   └── format.ts         # MW / time formatting in Europe/London
│   ├── nginx.conf, Dockerfile
├── scripts/
│   ├── verify_clean_clone.sh # clone → docker compose up → health + non-root checks
│   ├── smoke_deployed.sh     # every /api route + headers + Playwright against a URL
│   └── check_submission.sh   # personal-info / README hygiene before submitting
├── docs/SUBMISSION_CHECKLIST.md
├── .github/workflows/ci.yml, .pre-commit-config.yaml
├── docker-compose.yml
├── vercel.json, requirements.txt, .python-version   # Vercel config
├── Makefile, .env.example, PLAN.md
```

## API

All endpoints are under `/api`. Interactive docs are at `/docs` when running locally.

| Endpoint | Params | Returns |
|---|---|---|
| `GET /health` | – | `{status: "ok"}` |
| `GET /meta` | – | data date range, default cutoff, row counts |
| `GET /forecast-vs-actual` | `date` (YYYY-MM-DD), `cutoff` (HH:MM) | hourly latest forecast + lower bound, half-hourly actual, day summary |
| `GET /metrics` | `start`, `end`, `cutoff` | summary metrics, by-day breakdown, error histogram |
| `GET /error-by-hour` | `start`, `end`, `cutoff` | MAE/RMSE/bias/P90 per London hour |
| `GET /error-by-horizon` | `start`, `end` | the same statistics per 6h horizon bucket (all vintages) |

Validation is server-side. Malformed dates, malformed cutoffs, dates outside 2026-01-01..2026-01-31 and `start > end` all return **422** with a message naming the offending parameter. A day inside January that has no data returns **200 with an explicit empty result** (empty series, `null` metrics, `n: 0`) rather than 404. Unknown routes return JSON `404`. `/api/meta` reports any missing half-hours in the snapshot (currently none). The API sends CSP, `nosniff` and frame-deny headers, and CORS allows only the origins in `CORS_ORIGINS`.

## Running it

Prerequisites: Python 3.12+, Node 22+, and optionally Docker and `make`.

### Locally

```bash
make install          # venv + Python deps + npm ci
make backend          # http://localhost:8000  (API docs at /docs)
make frontend         # http://localhost:5173  (Vite proxies /api to :8000)
```

Without `make`:

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt   # Windows: .venv\Scripts\...
.venv/bin/uvicorn app.main:app --reload --port 8000
cd frontend && npm ci && npm run dev
```

### Docker

```bash
docker compose up --build   # UI at http://localhost:8080, API at http://localhost:8000
```

Both containers run as non-root users. Host ports can be changed with `FRONTEND_PORT` and `BACKEND_PORT`.

### Tests

| Command | What it runs |
|---|---|
| `make test` | pytest (unit, API, data) with coverage gates (≥ 70% overall, ≥ 90% on selection/metrics), then vitest, tsc, the production build and the bundle-size budget |
| `make lint` | ruff check + format, eslint |
| `make e2e` | Playwright: user flows, axe accessibility (light/dark), API smoke at 375/768/1440 px. Starts uvicorn and `vite preview` itself |
| `make lighthouse` | Lighthouse CI (needs the backend on :8000): perf ≥ 0.8, a11y ≥ 0.9 |
| `make audit` | pip-audit + npm audit |
| `make docker-test` | `scripts/verify_clean_clone.sh`: fresh clone, `docker compose up`, health and non-root checks |
| `make integration` | the one opt-in test that hits the live Elexon API (skipped by default) |
| `make sanity` | independent re-computation of the metrics against a running API |
| `make all` | lint + test + e2e + docker-test |

Without `make` (for example on Windows):

```bash
cd backend && .venv/Scripts/python -m pytest --cov && bash scripts/check_core_coverage.sh
cd frontend && npm test && npm run typecheck && npm run lint && npm run build && npx playwright test
```

To smoke-test a deployment: `bash scripts/smoke_deployed.sh https://kuyhu-zeta.vercel.app`. The same Playwright suite runs against any URL via `E2E_BASE_URL`.

CI (`.github/workflows/ci.yml`) runs all of the above on every push and PR, plus a gitleaks secret scan. Pre-commit hooks (`pre-commit install`) run ruff, eslint, tsc and gitleaks locally.

### Refreshing the data

```bash
make fetch-data   # or: cd backend && python scripts/fetch_data.py --start 2026-01-01 --end 2026-01-31
```

FUELHH is fetched by settlement date and WINDFOR by publish time, both in 7-day chunks. The forecast window starts 4 days before the first delivery day, so the late-December forecasts for early-January targets are included (WINDFOR horizons reach about 66h).

## Deploying to Vercel

The repo deploys as one Vercel project. The static Vite build is served from `frontend/dist`, and `/api/*` is rewritten to the Python function `api/index.py`, which bundles `backend/app` and the CSV snapshot. There is no runtime dependency on Elexon. The function is about 115 MB unzipped (pandas, numpy, FastAPI), well under the 250 MB limit.

1. Push the repo to GitHub.
2. `npm i -g vercel` and run `vercel login`.
3. From the repo root, run `vercel` and accept the defaults (framework: **Other**; the root directory is the repo root). `vercel.json` provides the install, build and output settings.
4. `vercel --prod`.
5. Run `bash scripts/smoke_deployed.sh https://<project>.vercel.app`, then paste the URL at the top of this README.

Security headers (CSP, HSTS, nosniff, frame-deny, referrer and permissions policy) are set in `vercel.json` for the static app. The API function sets its own headers.

Alternatively, import the GitHub repo in the Vercel dashboard. No environment variables are needed, because the UI calls the API on the same origin.

## Verification

`backend/scripts/sanity_check.py` re-implements the selection and metrics with only the Python standard library (`csv`, `zoneinfo`, plain loops). It shares no code with the app, and it asserts that MAE, bias, RMSE and the sample size match `/api/metrics` exactly. It was run for cutoffs 09:30 and 06:00. Snapshot values were also spot-checked against raw Elexon API responses.

## Design decisions and trade-offs

- **Committed CSV snapshot instead of live API calls.** The deployed app is fast, deterministic and independent of Elexon availability. CSV was chosen over parquet to avoid shipping `pyarrow` (about 100 MB) in the serverless bundle; the data is only about 0.8 MB.
- **pandas over a database.** About 15k forecast rows fit easily in memory, and the loader caches them per process. A database would add moving parts with no benefit at this scale.
- **Hourly evaluation grid.** This matches WINDFOR's native resolution. Interpolating to half-hours would invent forecast values.
- **Leave-one-day-out P90.** The what-if buffer is closer to what a buyer could actually have known, rather than an in-sample number that includes the day being shown.
- **Horizon analysis across all vintages.** With a single cutoff, horizons only span about 15–38h. Using every vintage shows the full lead-time curve.
- **Chart colors** come from a colorblind-validated palette with light and dark variants, plus a table view for the daily data.

## Known limitations and future work

- **One month of history.** Percentiles are seasonal and in-sample for January. A rolling multi-month window, and P90 conditioned on forecast level or horizon, would give better-calibrated buffers.
- **The large positive bias is not explained yet.** Plausible causes are curtailment, which reduces metered outturn, and coverage differences between WINDFOR and FUELHH. A bias-corrected forecast is an obvious next step.
- The cutoff is inclusive of a publish at exactly that minute. In practice, data can land a few minutes after its `publishTime`, so a production version should use the actual receipt time.
- No authentication or rate limiting. These are fine for a read-only demo over public data.
- Future work: bias-corrected and quantile forecasts, MWh/£ cost-of-error view, other fuel types, scheduled data refresh.
