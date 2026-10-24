import { describe, expect, it } from 'vitest'
import type { DecisionDay } from './api'
import { fmtClock } from './format'
import { mergeSeries } from './series'

describe('mergeSeries', () => {
  it('aligns hourly forecasts with half-hourly actuals on one sorted axis', () => {
    const day = {
      forecast: [{ time: '2026-01-15T00:00:00Z', forecast: 100, lower_bound: 60, publish_time: '', horizon_h: 14.5 }],
      actual: [
        { time: '2026-01-15T00:30:00Z', actual: 95 },
        { time: '2026-01-15T00:00:00Z', actual: 90 },
      ],
    } as DecisionDay
    expect(mergeSeries(day)).toEqual([
      { t: Date.parse('2026-01-15T00:00:00Z'), actual: 90, forecast: 100, lower: 60 },
      { t: Date.parse('2026-01-15T00:30:00Z'), actual: 95 },
    ])
  })
})

describe('fmtClock', () => {
  it('shows Europe/London time (BST in summer)', () => {
    expect(fmtClock('2026-07-01T08:30:00Z')).toBe('09:30')
    expect(fmtClock('2026-01-15T08:30:00Z')).toBe('08:30')
  })
})
