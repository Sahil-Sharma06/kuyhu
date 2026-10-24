import { useMemo } from 'react'
import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DecisionDay } from '../api'
import { ChartCard, DataTable, EmptyState, ErrorBox, Legend, Loading, StatCard, TooltipBox } from '../components/ui'
import { fmtClock, fmtDateTime, fmtGW, fmtMW, fmtSigned } from '../format'
import { useApi, useChartColors } from '../hooks'
import { mergeSeries } from '../series'

export function DecisionView({ day, cutoff }: { day: string; cutoff: string }) {
  const { data, error, loading } = useApi<DecisionDay>('/forecast-vs-actual', { date: day, cutoff })
  const c = useChartColors()
  const rows = useMemo(() => (data ? mergeSeries(data) : []), [data])

  if (error) return <ErrorBox message={error} />
  const s = data?.summary

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {loading || !s ? (
          [0, 1, 2, 3].map((i) => <Loading key={i} height="h-24" />)
        ) : (
          <>
            <StatCard
              label="Latest forecast used"
              value={s.latest_publish_time ? fmtDateTime(s.latest_publish_time) : 'None available'}
              hint={`Cutoff ${fmtDateTime(data!.cutoff_utc)} London`}
            />
            <StatCard label="Mean forecast" value={fmtMW(s.mean_forecast_mw)} hint={`${s.hours_covered} hourly points`} />
            <StatCard
              label="Risk-adjusted wind (P90)"
              value={fmtMW(s.mean_lower_bound_mw)}
              hint={`Buy ~${fmtMW(data!.risk_buffer_mw)}/h extra vs forecast`}
            />
            <StatCard
              label="Outturn (hindsight)"
              value={fmtMW(s.mean_actual_mw)}
              hint={`Day error ${fmtSigned(s.bias_mw)} · MAE ${fmtMW(s.mae_mw)}`}
            />
          </>
        )}
      </div>

      <ChartCard
        title="Wind generation: latest forecast vs actual"
        subtitle="Times in Europe/London. Forecast is hourly; outturn is half-hourly. Lower bound = forecast − P90 of historic over-forecast error (excluding this day)."
      >
        {loading ? (
          <Loading />
        ) : rows.length === 0 ? (
          <EmptyState message="No forecast or outturn data is available for this day and cutoff. Try a later decision time or another day." />
        ) : (
          <>
            <Legend
              items={[
                { label: 'Forecast', color: c['--series-1'] },
                { label: 'Risk-adjusted lower bound', color: c['--series-3'], dashed: true },
                { label: 'Actual', color: c['--series-2'] },
              ]}
            />
            <div className="h-80" role="img" aria-label="Line chart of forecast, lower bound and actual wind generation for the selected day">
              <ResponsiveContainer>
                <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={c['--grid']} vertical={false} />
                  <XAxis
                    dataKey="t"
                    type="number"
                    scale="time"
                    domain={['dataMin', 'dataMax']}
                    tickFormatter={fmtClock}
                    stroke={c['--axis']}
                    tick={{ fill: c['--muted'], fontSize: 12 }}
                    minTickGap={24}
                  />
                  <YAxis tickFormatter={fmtGW} stroke={c['--axis']} tick={{ fill: c['--muted'], fontSize: 12 }} width={60} domain={[0, 'auto']} />
                  <Tooltip
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <TooltipBox
                          title={fmtClock(label as number)}
                          rows={[
                            { label: 'Forecast', value: fmtMW(payload[0].payload.forecast), color: c['--series-1'] },
                            { label: 'Lower bound', value: fmtMW(payload[0].payload.lower), color: c['--series-3'] },
                            { label: 'Actual', value: fmtMW(payload[0].payload.actual), color: c['--series-2'] },
                          ]}
                        />
                      ) : null
                    }
                  />
                  <Line dataKey="forecast" stroke={c['--series-1']} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                  <Line
                    dataKey="lower"
                    stroke={c['--series-3']}
                    strokeWidth={2}
                    strokeDasharray="6 4"
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                  <Line dataKey="actual" stroke={c['--series-2']} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <DataTable
              name="Hourly forecast, lower bound and actual"
              toggle="Show hourly table"
              headers={['Time (London)', 'Forecast', 'Lower bound', 'Actual']}
              rows={rows.map((r) => [fmtClock(r.t), fmtMW(r.forecast), fmtMW(r.lower), fmtMW(r.actual)])}
            />
          </>
        )}
      </ChartCard>
    </div>
  )
}
