import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import App from './App'
import { emptyDay } from './test/fixtures'
import { requests, server } from './test/server'

const cardValue = (label: string) => within(screen.getByRole('region', { name: label })).getByText(label).nextElementSibling!.textContent

async function renderDecision() {
  render(<App />)
  await screen.findByText('Latest forecast used')
}

describe('pages', () => {
  it('renders the Decision view by default', async () => {
    await renderDecision()
    expect(screen.getByRole('heading', { name: 'GB Wind Forecast Monitor' })).toBeInTheDocument()
    expect(screen.getByText('Wind generation: latest forecast vs actual')).toBeInTheDocument()
  })

  it('renders the Accuracy view', async () => {
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Accuracy' }))
    expect(await screen.findByText('Error by forecast horizon')).toBeInTheDocument()
    expect(screen.getByText('Error by hour of day')).toBeInTheDocument()
    expect(screen.getByText('Error distribution')).toBeInTheDocument()
    expect(screen.getByText('Daily trend')).toBeInTheDocument()
  })

  it('renders the Methodology view', async () => {
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Methodology' }))
    expect(screen.getByRole('heading', { name: /Methodology/ })).toBeInTheDocument()
    expect(screen.getByText('Latest available forecast')).toBeInTheDocument()
  })
})

describe('decision chart', () => {
  it('draws forecast, lower bound and actual series with a legend', async () => {
    const { container } = render(<App />)
    await screen.findByText('Latest forecast used')
    await waitFor(() => expect(container.querySelectorAll('.recharts-line').length).toBe(3))
    const chart = screen.getByRole('img', { name: /forecast, lower bound and actual/ })
    expect(chart.querySelectorAll('path.recharts-line-curve')).toHaveLength(3)
    const legend = chart.previousElementSibling as HTMLElement
    for (const name of ['Forecast', 'Risk-adjusted lower bound', 'Actual']) {
      expect(within(legend).getByText(name)).toBeInTheDocument()
    }
  })

  it('shows an empty state when no data exists for the day', async () => {
    server.use(http.get('*/api/forecast-vs-actual', ({ request }) => {
      const u = new URL(request.url)
      return HttpResponse.json(emptyDay(u.searchParams.get('date')!, u.searchParams.get('cutoff')!))
    }))
    await renderDecision()
    expect(await screen.findByText(/No forecast or outturn data is available/)).toBeInTheDocument()
    expect(cardValue('Latest forecast used')).toBe('None available')
    expect(cardValue('Mean forecast')).toBe('–')
  })
})

describe('controls', () => {
  it('refetches and updates when the delivery day changes', async () => {
    await renderDecision()
    expect(cardValue('Mean forecast')).toBe('10,100 MW')
    fireEvent.change(screen.getByLabelText('Delivery day (D)'), { target: { value: '2026-01-20' } })
    await waitFor(() => expect(cardValue('Mean forecast')).toBe('12,000 MW'))
    expect(requests.some((u) => u.pathname === '/api/forecast-vs-actual' && u.searchParams.get('date') === '2026-01-20')).toBe(true)
  })

  it('refetches and updates when the cutoff changes', async () => {
    await renderDecision()
    expect(cardValue('Latest forecast used')).toMatch(/31 Dec.*09:30/)
    fireEvent.change(screen.getByLabelText('Decision time on D-1 (London)'), { target: { value: '06:00' } })
    await waitFor(() => expect(cardValue('Latest forecast used')).toMatch(/04:30/))
    expect(cardValue('Mean forecast')).toBe('10,600 MW')
    expect(requests.some((u) => u.searchParams.get('cutoff') === '06:00')).toBe(true)
  })

  it('restricts the date picker to January 2026 and ignores out-of-range input', async () => {
    await renderDecision()
    const input = screen.getByLabelText('Delivery day (D)') as HTMLInputElement
    expect(input.min).toBe('2026-01-01')
    expect(input.max).toBe('2026-01-31')
    const before = requests.length
    fireEvent.change(input, { target: { value: '2026-02-15' } })
    expect(input.value).toBe('2026-01-01')
    expect(requests.slice(before).some((u) => u.searchParams.get('date') === '2026-02-15')).toBe(false)
  })

  it('accuracy range inputs are restricted too', async () => {
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Accuracy' }))
    for (const label of ['From', 'To']) {
      const input = screen.getByLabelText(label) as HTMLInputElement
      expect([input.min, input.max]).toEqual(['2026-01-01', '2026-01-31'])
    }
  })
})

describe('KPI cards', () => {
  it('formats accuracy metrics with units', async () => {
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Accuracy' }))
    await screen.findByText('2,107 MW')
    expect(cardValue('MAE')).toBe('2,107 MW')
    expect(cardValue('RMSE')).toBe('2,611 MW')
    expect(cardValue('Mean bias')).toBe('+1,840 MW')
    expect(cardValue('P90 |error|')).toBe('4,377 MW')
    expect(cardValue('MAPE')).toBe('21.9%')
    expect(screen.getByText('18.2% of mean actual')).toBeInTheDocument()
  })

  it('formats decision metrics with units', async () => {
    await renderDecision()
    expect(cardValue('Risk-adjusted wind (P90)')).toBe('6,100 MW')
    expect(screen.getByText('Buy ~4,000 MW/h extra vs forecast')).toBeInTheDocument()
  })

  it('updates accuracy KPIs when the cutoff changes', async () => {
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Accuracy' }))
    await screen.findByText('2,107 MW')
    fireEvent.change(screen.getByLabelText('Decision time on D-1 (London)'), { target: { value: '05:00' } })
    await waitFor(() => expect(cardValue('MAE')).toBe('2,207 MW'))
  })
})

describe('loading and error states', () => {
  it('shows loading placeholders before data arrives', async () => {
    render(<App />)
    expect(screen.getAllByRole('status', { name: 'Loading' }).length).toBeGreaterThan(0)
    await screen.findByText('Latest forecast used')
  })

  it('shows an error when the backend is down', async () => {
    server.use(http.get('*/api/meta', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Backend unavailable (500: boom)')
  })

  it('shows the API validation message when a view request fails', async () => {
    server.use(http.get('*/api/forecast-vs-actual', () => HttpResponse.json({ detail: 'date is outside the supported delivery period' }, { status: 422 })))
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('422: date is outside the supported delivery period')
  })

  it('shows per-chart errors on the accuracy view', async () => {
    server.use(http.get('*/api/error-by-horizon', () => new HttpResponse(null, { status: 503, statusText: 'Service Unavailable' })))
    await renderDecision()
    await userEvent.click(screen.getByRole('button', { name: 'Accuracy' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('503: Service Unavailable')
    expect(await screen.findByText('2,107 MW')).toBeInTheDocument()
  })
})
