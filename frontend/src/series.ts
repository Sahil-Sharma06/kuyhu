import type { DecisionDay } from './api'

export interface Row {
  t: number
  forecast?: number
  lower?: number
  actual?: number
}

/** Merge hourly forecasts and half-hourly actuals onto one time axis. */
export function mergeSeries(d: DecisionDay): Row[] {
  const rows = new Map<number, Row>()
  const at = (iso: string) => {
    const t = Date.parse(iso)
    if (!rows.has(t)) rows.set(t, { t })
    return rows.get(t)!
  }
  d.actual.forEach((a) => (at(a.time).actual = a.actual))
  d.forecast.forEach((f) => Object.assign(at(f.time), { forecast: f.forecast, lower: f.lower_bound }))
  return [...rows.values()].sort((a, b) => a.t - b.t)
}
