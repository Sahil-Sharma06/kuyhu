import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { expect, it } from 'vitest'
import type { DecisionDay } from './api'
import { mergeSeries } from './series'
import { decisionDay } from './test/fixtures'
import { server } from './test/server'
import { DecisionView } from './views/DecisionView'

/** A full month of half-hourly actuals and hourly forecasts (~1,500 points per series). */
function monthOfPoints(): DecisionDay {
  const start = Date.parse('2026-01-01T00:00:00Z')
  const base = decisionDay('2026-01-15', '09:30')
  return {
    ...base,
    actual: Array.from({ length: 1488 }, (_, i) => ({ time: new Date(start + i * 1_800_000).toISOString(), actual: 10_000 + (i % 97) * 10 })),
    forecast: Array.from({ length: 1488 }, (_, i) => ({
      time: new Date(start + i * 1_800_000).toISOString(),
      forecast: 11_000,
      lower_bound: 7_000,
      publish_time: base.forecast[0].publish_time,
      horizon_h: 20,
    })),
  }
}

it('merges ~1,500 points per series quickly', () => {
  const t0 = performance.now()
  const rows = mergeSeries(monthOfPoints())
  expect(rows).toHaveLength(1488)
  expect(performance.now() - t0).toBeLessThan(50)
})

it('renders a chart with ~1,500 points per series in reasonable time', async () => {
  server.use(http.get('*/api/forecast-vs-actual', () => HttpResponse.json(monthOfPoints())))
  const t0 = performance.now()
  const { container } = render(<DecisionView day="2026-01-15" cutoff="09:30" />)
  await screen.findByText('Latest forecast used')
  await expect.poll(() => container.querySelectorAll('path.recharts-line-curve').length).toBe(3)
  // Generous bound for slow CI machines; jsdom is far slower than a real browser.
  expect(performance.now() - t0).toBeLessThan(5_000)
})
