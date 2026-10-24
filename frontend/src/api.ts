/** Typed client for the backend API. All timestamps are ISO 8601 UTC. */

export interface Meta {
  start: string
  end: string
  default_cutoff: string
  timezone: string
  actual_rows: number
  forecast_rows: number
}

export interface ForecastPoint {
  time: string
  forecast: number
  lower_bound: number
  publish_time: string
  horizon_h: number
}

export interface DecisionDay {
  date: string
  cutoff_utc: string
  risk_buffer_mw: number
  forecast: ForecastPoint[]
  actual: { time: string; actual: number }[]
  summary: {
    latest_publish_time: string | null
    mean_forecast_mw: number | null
    mean_actual_mw: number | null
    mean_lower_bound_mw: number | null
    mae_mw: number | null
    bias_mw: number | null
    hours_covered: number
  }
}

export interface Summary {
  n: number
  mae: number | null
  rmse: number | null
  mape: number | null
  bias: number | null
  p50: number | null
  p90: number | null
  p95: number | null
  p99: number | null
  mae_pct_of_mean_actual: number | null
}

export interface GroupStat {
  key: number | string
  n: number
  mae: number | null
  rmse: number | null
  bias: number | null
  p90: number | null
}

export interface Metrics {
  start: string
  end: string
  cutoff: string
  summary: Summary
  by_day: (GroupStat & { key: string; mean_actual: number; mean_forecast: number })[]
  histogram: { bin: number; count: number }[]
  horizon_range_h: [number, number] | null
}

export type HorizonStat = GroupStat & { key: number; label: string }

const BASE = import.meta.env.VITE_API_BASE ?? ''

export async function getJson<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}/api${path}${qs ? `?${qs}` : ''}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : res.statusText
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}
