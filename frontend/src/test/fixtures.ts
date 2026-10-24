import type { DecisionDay, GroupStat, HorizonStat, Meta, Metrics } from '../api'

export const meta: Meta = {
  start: '2026-01-01',
  end: '2026-01-31',
  default_cutoff: '09:30',
  timezone: 'Europe/London',
  actual_rows: 1488,
  forecast_rows: 15215,
  missing_half_hours: [],
}

/** A decision day whose numbers depend on date and cutoff, so UI updates are observable. */
export function decisionDay(date: string, cutoff: string): DecisionDay {
  const dayNum = Number(date.slice(8, 10))
  const early = cutoff < '09:30'
  const prev = new Date(Date.parse(`${date}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10)
  const publish = `${prev}T${early ? '04' : '09'}:30:00Z`
  const base = 10_000 + dayNum * 100 + (early ? 500 : 0)
  const hours = Array.from({ length: 24 }, (_, h) => h)
  return {
    date,
    cutoff_utc: `${prev}T${cutoff}:00+00:00`,
    risk_buffer_mw: 4000,
    forecast: hours.map((h) => ({
      time: `${date}T${String(h).padStart(2, '0')}:00:00Z`,
      forecast: base,
      lower_bound: base - 4000,
      publish_time: publish,
      horizon_h: 14.5 + h,
    })),
    actual: hours.flatMap((h) =>
      ['00', '30'].map((m) => ({ time: `${date}T${String(h).padStart(2, '0')}:${m}:00Z`, actual: base - 1000 })),
    ),
    summary: {
      latest_publish_time: publish,
      mean_forecast_mw: base,
      mean_actual_mw: base - 1000,
      mean_lower_bound_mw: base - 4000,
      mae_mw: 1000,
      bias_mw: 1000,
      hours_covered: 24,
    },
  }
}

export const emptyDay = (date: string, cutoff: string): DecisionDay => ({
  ...decisionDay(date, cutoff),
  forecast: [],
  actual: [],
  summary: {
    latest_publish_time: null,
    mean_forecast_mw: null,
    mean_actual_mw: null,
    mean_lower_bound_mw: null,
    mae_mw: null,
    bias_mw: null,
    hours_covered: 0,
  },
})

export function metrics(cutoff: string): Metrics {
  const shift = cutoff < '09:30' ? 100 : 0
  return {
    start: '2026-01-01',
    end: '2026-01-31',
    cutoff,
    summary: {
      n: 744,
      mae: 2107.18 + shift,
      rmse: 2611.24,
      mape: 21.877,
      bias: 1839.92,
      p50: 1707,
      p90: 4377,
      p95: 5400.55,
      p99: 6212.85,
      mae_pct_of_mean_actual: 18.195,
    },
    by_day: [
      { key: '2026-01-01', n: 24, mae: 4274, rmse: 4300, bias: 4274, p90: 5000, mean_actual: 15356, mean_forecast: 19630 },
      { key: '2026-01-02', n: 24, mae: 1000, rmse: 1200, bias: -200, p90: 2000, mean_actual: 12000, mean_forecast: 11800 },
    ],
    histogram: [
      { bin: -500, count: 40 },
      { bin: 0, count: 300 },
      { bin: 500, count: 404 },
    ],
    horizon_range_h: [14.5, 37.5],
  }
}

export const byHour: GroupStat[] = Array.from({ length: 24 }, (_, h) => ({ key: h, n: 31, mae: 2000 + h, rmse: 2500, bias: 1500, p90: 4000 }))

export const byHorizon: HorizonStat[] = [0, 6, 12].map((k) => ({ key: k, label: `${k}-${k + 6}h`, n: 500, mae: 1800 + k * 10, rmse: 2200, bias: 1400, p90: 3900 }))
