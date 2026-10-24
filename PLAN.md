# PLAN — Wind Forecast Monitor (v1)

## Data findings (probed 2026-10-24)
- **FUELHH** `/datasets/FUELHH/stream?settlementDateFrom&settlementDateTo&fuelType=WIND` — 30-min `startTime` (UTC), `generation` MW. Jan 2026 = 1488 rows, no dups/nulls.
- **WINDFOR** `/datasets/WINDFOR/stream?publishDateTimeFrom&publishDateTimeTo` — **hourly** `startTime`, ~8 publishes/day (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, ...), horizons −25.5h…+66.5h.
- Fetch forecasts published 2025-12-28 → 2026-02-01, chunked in 7-day windows.

## Domain rules
- Cutoff for delivery day D = D-1 at HH:MM Europe/London (default 09:30), converted to UTC (DST-safe).
- Latest forecast per target hour = row with max `publishTime <= cutoff` and `startTime - publishTime >= 0`.
- Evaluation grid = hourly target times (forecast granularity); actual = FUELHH half-hour starting at that time.
- Error = forecast − actual. Metrics: MAE, RMSE, MAPE (actual>0 only), bias, P50/P90/P95/P99 |err|, MAE % of mean actual. Breakdowns by hour (London), day, horizon bucket.
- What-if: lower bound = forecast − empirical P90 of signed error (forecast − actual) over the Jan sample for that cutoff, excluding the chosen day.

## Stages (one commit each)
1. Scaffold + ingestion script + data snapshot (parquet).
2. Backend: data/, services/ (selection, metrics), api/ + pytest.
3. Frontend: Vite React TS + Tailwind + Recharts: Decision, Accuracy, Methodology.
4. Docker + compose.
5. Vercel config + README + independent sanity check script.
