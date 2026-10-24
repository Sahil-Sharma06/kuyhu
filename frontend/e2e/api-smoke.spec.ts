import { expect, test } from '@playwright/test'

/** Every API route must answer 200 with JSON through the same origin the UI uses. */
const ROUTES = [
  '/api/health',
  '/api/meta',
  '/api/forecast-vs-actual?date=2026-01-15&cutoff=09:30',
  '/api/metrics?start=2026-01-01&end=2026-01-31&cutoff=09:30',
  '/api/error-by-hour',
  '/api/error-by-horizon',
]

test.describe('API smoke', () => {
  test.skip(({ viewport }) => viewport!.width !== 1440, 'viewport-independent; run once')

  for (const route of ROUTES) {
    test(route, async ({ request }) => {
      const resp = await request.get(route)
      expect(resp.status()).toBe(200)
      expect(resp.headers()['content-type']).toContain('application/json')
      expect(resp.headers()['x-content-type-options']).toBe('nosniff')
    })
  }
})
