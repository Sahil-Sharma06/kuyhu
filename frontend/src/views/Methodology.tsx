import { Card } from '../components/ui'

const ITEMS: [string, string][] = [
  [
    'Decision cutoff',
    'For delivery day D, the purchase decision is taken on D-1 at the chosen Europe/London time (default 09:30, around the GB day-ahead auction gate closure). The cutoff is DST-aware and adjustable above.',
  ],
  [
    'Latest available forecast',
    'For every target hour on D we use the WINDFOR forecast with the latest publish time at or before the cutoff. Forecasts published after the cutoff are never used, and rows whose target precedes their publish time (negative horizon) are discarded.',
  ],
  [
    'Data',
    'National wind only, from Elexon BMRS: WINDFOR (hourly forecasts) and FUELHH fuelType=WIND (half-hourly outturn). A cleaned snapshot is bundled with the app; all times are stored in UTC and shown in Europe/London.',
  ],
  [
    'Alignment',
    'Forecasts are hourly, so accuracy is measured at each forecast hour against the outturn for the half-hour starting at that time. No interpolation is applied.',
  ],
  [
    'Error metrics',
    'Error = forecast − actual, so positive bias means wind was over-forecast. MAE, RMSE, mean bias, P50/P90/P95/P99 of |error|, MAE as % of mean actual, and MAPE (only over non-zero actuals).',
  ],
  [
    'Risk-adjusted lower bound',
    'Forecast minus the empirical 90th percentile of signed error over the period, excluding the selected day. Buying to cover this lower bound would have covered the wind shortfall in ~90% of historic hours.',
  ],
  [
    'Limitations',
    'One month of history (January 2026), so percentiles are in-sample and seasonal. Forecasts are national and transmission-level; outturn can be reduced by curtailment, which shows up as forecast error.',
  ],
]

export function Methodology() {
  return (
    <Card>
      <h2 className="text-base font-semibold text-ink">Methodology &amp; assumptions</h2>
      <dl className="mt-3 grid gap-4 md:grid-cols-2">
        {ITEMS.map(([term, desc]) => (
          <div key={term}>
            <dt className="text-sm font-medium text-ink">{term}</dt>
            <dd className="mt-1 text-sm leading-relaxed text-ink-2">{desc}</dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}
