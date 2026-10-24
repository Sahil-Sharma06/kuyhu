import type { ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { GroupStat, HorizonStat, Metrics } from '../api'
import { ChartCard, ErrorBox, Legend, Loading, StatCard, TooltipBox } from '../components/ui'
import { fmtDay, fmtGW, fmtMW, fmtPct, fmtSigned } from '../format'
import { useApi, useChartColors, type ChartColors } from '../hooks'

const axisProps = (c: ChartColors) => ({ stroke: c['--axis'], tick: { fill: c['--muted'], fontSize: 12 } })

/** MAE bars with a bias line, sharing one MW axis. */
function MaeBiasChart({ rows, label, c, xLabel }: { rows: GroupStat[]; label: (k: GroupStat) => string; c: ChartColors; xLabel: string }) {
  const data = rows.map((r) => ({ ...r, name: label(r) }))
  return (
    <>
      <Legend
        items={[
          { label: 'MAE', color: c['--series-1'] },
          { label: 'Mean bias (forecast − actual)', color: c['--series-2'] },
        ]}
      />
      <div className="h-64" role="img" aria-label={`MAE and bias by ${xLabel}`}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c['--grid']} vertical={false} />
            <XAxis dataKey="name" {...axisProps(c)} interval="preserveStartEnd" />
            <YAxis tickFormatter={fmtGW} {...axisProps(c)} width={48} />
            <ReferenceLine y={0} stroke={c['--axis']} />
            <Tooltip
              cursor={{ fill: c['--grid'], opacity: 0.5 }}
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={`${xLabel} ${payload[0].payload.name}`}
                    rows={[
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae), color: c['--series-1'] },
                      { label: 'Bias', value: fmtSigned(payload[0].payload.bias), color: c['--series-2'] },
                      { label: 'P90 |error|', value: fmtMW(payload[0].payload.p90) },
                      { label: 'Points', value: String(payload[0].payload.n) },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="mae" fill={c['--series-1']} radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} />
            <Line dataKey="bias" stroke={c['--series-2']} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}

function Histogram({ bins, c }: { bins: Metrics['histogram']; c: ChartColors }) {
  const data = bins.map((b) => ({ ...b, mid: b.bin + 250 }))
  return (
    <div className="h-64" role="img" aria-label="Histogram of forecast error">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
          <CartesianGrid stroke={c['--grid']} vertical={false} />
          <XAxis dataKey="bin" tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}`} {...axisProps(c)} unit=" GW" />
          <YAxis {...axisProps(c)} width={36} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: c['--grid'], opacity: 0.5 }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <TooltipBox
                  title={`${fmtSigned(payload[0].payload.bin)} to ${fmtSigned(payload[0].payload.bin + 500)}`}
                  rows={[{ label: 'Hours', value: String(payload[0].payload.count) }]}
                />
              ) : null
            }
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.bin} fill={d.bin >= 0 ? c['--series-1'] : c['--series-2']} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function DailyTrend({ rows, c }: { rows: Metrics['by_day']; c: ChartColors }) {
  const data = rows.map((r) => ({ ...r, name: fmtDay(r.key) }))
  return (
    <>
      <Legend
        items={[
          { label: 'Mean forecast', color: c['--series-1'] },
          { label: 'Mean actual', color: c['--series-2'] },
        ]}
      />
      <div className="h-64" role="img" aria-label="Daily mean forecast and actual wind generation">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c['--grid']} vertical={false} />
            <XAxis dataKey="name" {...axisProps(c)} minTickGap={16} />
            <YAxis tickFormatter={fmtGW} {...axisProps(c)} width={48} domain={[0, 'auto']} />
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.length ? (
                  <TooltipBox
                    title={payload[0].payload.name}
                    rows={[
                      { label: 'Mean forecast', value: fmtMW(payload[0].payload.mean_forecast), color: c['--series-1'] },
                      { label: 'Mean actual', value: fmtMW(payload[0].payload.mean_actual), color: c['--series-2'] },
                      { label: 'Bias', value: fmtSigned(payload[0].payload.bias) },
                      { label: 'MAE', value: fmtMW(payload[0].payload.mae) },
                    ]}
                  />
                ) : null
              }
            />
            <Line dataKey="mean_forecast" stroke={c['--series-1']} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
            <Line dataKey="mean_actual" stroke={c['--series-2']} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-3 text-xs text-ink-2">
        <summary className="cursor-pointer select-none">Show daily table</summary>
        <div className="mt-2 max-h-64 overflow-auto">
          <table className="w-full tabular-nums">
            <thead className="text-left text-muted">
              <tr>
                <th className="py-1 pr-2">Day</th>
                <th className="pr-2 text-right">Forecast</th>
                <th className="pr-2 text-right">Actual</th>
                <th className="pr-2 text-right">Bias</th>
                <th className="text-right">MAE</th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.key} className="border-t border-line">
                  <td className="py-1 pr-2">{r.name}</td>
                  <td className="pr-2 text-right">{fmtMW(r.mean_forecast)}</td>
                  <td className="pr-2 text-right">{fmtMW(r.mean_actual)}</td>
                  <td className="pr-2 text-right">{fmtSigned(r.bias)}</td>
                  <td className="text-right">{fmtMW(r.mae)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}

function Section({ loading, error, children }: { loading: boolean; error: string | null; children: () => ReactNode }) {
  if (error) return <ErrorBox message={error} />
  return loading ? <Loading height="h-64" /> : <>{children()}</>
}

export function AccuracyView({ start, end, cutoff }: { start: string; end: string; cutoff: string }) {
  const c = useChartColors()
  const range = { start, end }
  const m = useApi<Metrics>('/metrics', { ...range, cutoff })
  const hour = useApi<GroupStat[]>('/error-by-hour', { ...range, cutoff })
  const horizon = useApi<HorizonStat[]>('/error-by-horizon', range)
  const s = m.data?.summary

  return (
    <div className="space-y-4">
      {m.error ? (
        <ErrorBox message={m.error} />
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {m.loading || !s ? (
            [0, 1, 2, 3, 4, 5].map((i) => <Loading key={i} height="h-24" />)
          ) : (
            <>
              <StatCard label="MAE" value={fmtMW(s.mae)} hint={`${fmtPct(s.mae_pct_of_mean_actual)} of mean actual`} />
              <StatCard label="RMSE" value={fmtMW(s.rmse)} hint="Penalises large misses" />
              <StatCard label="Mean bias" value={fmtSigned(s.bias)} hint={s.bias! > 0 ? 'Forecast over-predicts' : 'Forecast under-predicts'} />
              <StatCard label="P90 |error|" value={fmtMW(s.p90)} hint={`P95 ${fmtMW(s.p95)} · P99 ${fmtMW(s.p99)}`} />
              <StatCard label="MAPE" value={fmtPct(s.mape)} hint={`Median |error| ${fmtMW(s.p50)}`} />
              <StatCard
                label="Sample"
                value={`${s.n} h`}
                hint={m.data!.horizon_range_h ? `Horizons ${m.data!.horizon_range_h[0]}–${m.data!.horizon_range_h[1]} h` : undefined}
              />
            </>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Error by forecast horizon" subtitle="All forecast vintages for these target days, 6-hour lead-time buckets (independent of cutoff).">
          <Section loading={horizon.loading} error={horizon.error}>
            {() => <MaeBiasChart rows={horizon.data!} label={(r) => (r as HorizonStat).label} c={c} xLabel="Horizon" />}
          </Section>
        </ChartCard>
        <ChartCard title="Error by hour of day" subtitle="Latest pre-cutoff forecast, by Europe/London hour of the target time.">
          <Section loading={hour.loading} error={hour.error}>
            {() => <MaeBiasChart rows={hour.data!} label={(r) => `${String(r.key).padStart(2, '0')}:00`} c={c} xLabel="Hour" />}
          </Section>
        </ChartCard>
        <ChartCard title="Error distribution" subtitle="Forecast − actual in 500 MW bins. Blue = over-forecast (risk of buying too little); orange = under-forecast.">
          <Section loading={m.loading} error={m.error}>
            {() => <Histogram bins={m.data!.histogram} c={c} />}
          </Section>
        </ChartCard>
        <ChartCard title="Daily trend" subtitle="Daily mean of the latest pre-cutoff forecast vs outturn.">
          <Section loading={m.loading} error={m.error}>
            {() => <DailyTrend rows={m.data!.by_day} c={c} />}
          </Section>
        </ChartCard>
      </div>
    </div>
  )
}
