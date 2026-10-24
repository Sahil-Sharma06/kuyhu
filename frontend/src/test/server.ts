import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { byHorizon, byHour, decisionDay, meta, metrics } from './fixtures'

/** Every request URL the mocked API received, for asserting refetches. */
export const requests: URL[] = []

export const handlers = [
  http.get('*/api/meta', () => HttpResponse.json(meta)),
  http.get('*/api/forecast-vs-actual', ({ request }) => {
    const url = new URL(request.url)
    return HttpResponse.json(decisionDay(url.searchParams.get('date')!, url.searchParams.get('cutoff')!))
  }),
  http.get('*/api/metrics', ({ request }) => HttpResponse.json(metrics(new URL(request.url).searchParams.get('cutoff')!))),
  http.get('*/api/error-by-hour', () => HttpResponse.json(byHour)),
  http.get('*/api/error-by-horizon', () => HttpResponse.json(byHorizon)),
]

export const server = setupServer(...handlers)
server.events.on('request:start', ({ request }) => {
  requests.push(new URL(request.url))
})
