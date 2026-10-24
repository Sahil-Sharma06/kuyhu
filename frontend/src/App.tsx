import { useEffect, useState } from 'react'
import type { Meta } from './api'
import { ErrorBox, Loading } from './components/ui'
import { useApi } from './hooks'
import { AccuracyView } from './views/AccuracyView'
import { DecisionView } from './views/DecisionView'
import { Methodology } from './views/Methodology'

type Tab = 'decision' | 'accuracy' | 'methodology'
const TABS: [Tab, string][] = [
  ['decision', 'Decision'],
  ['accuracy', 'Accuracy'],
  ['methodology', 'Methodology'],
]

const inputCls = 'mt-1 block w-full rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block min-w-0 flex-1 text-xs font-medium text-ink-2 sm:flex-none">
      {label}
      {children}
    </label>
  )
}

export default function App() {
  const meta = useApi<Meta>('/meta')
  const [tab, setTab] = useState<Tab>('decision')
  const [cutoff, setCutoff] = useState('09:30')
  const [day, setDay] = useState('')
  const [range, setRange] = useState({ start: '', end: '' })

  useEffect(() => {
    if (!meta.data) return
    setCutoff(meta.data.default_cutoff)
    setDay(meta.data.start)
    setRange({ start: meta.data.start, end: meta.data.end })
  }, [meta.data])

  const bounds = meta.data ? { min: meta.data.start, max: meta.data.end } : {}
  // Browsers do not enforce min/max on typed input, so reject out-of-range dates here too.
  const inRange = (v: string) => !!meta.data && v >= meta.data.start && v <= meta.data.end

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold text-ink">GB Wind Forecast Monitor</h1>
            <p className="text-sm text-ink-2">Day-ahead procurement · National wind · Elexon BMRS · January 2026</p>
          </div>
          <nav className="flex rounded-lg border border-line p-0.5" aria-label="Views">
            {TABS.map(([id, label]) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                aria-current={tab === id ? 'page' : undefined}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors motion-reduce:transition-none ${
                  tab === id ? 'bg-ink text-surface' : 'text-ink-2 hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        {meta.error && <ErrorBox message={`Backend unavailable (${meta.error})`} />}
        {meta.loading && <Loading height="h-16" />}
        {meta.data && tab !== 'methodology' && (
          <div className="flex flex-wrap gap-3">
            {tab === 'decision' ? (
              <Field label="Delivery day (D)">
                <input type="date" className={inputCls} value={day} {...bounds} onChange={(e) => inRange(e.target.value) && setDay(e.target.value)} />
              </Field>
            ) : (
              <>
                <Field label="From">
                  <input
                    type="date"
                    className={inputCls}
                    value={range.start}
                    {...bounds}
                    onChange={(e) => inRange(e.target.value) && setRange((r) => ({ ...r, start: e.target.value }))}
                  />
                </Field>
                <Field label="To">
                  <input
                    type="date"
                    className={inputCls}
                    value={range.end}
                    {...bounds}
                    onChange={(e) => inRange(e.target.value) && setRange((r) => ({ ...r, end: e.target.value }))}
                  />
                </Field>
              </>
            )}
            <Field label="Decision time on D-1 (London)">
              <input type="time" className={inputCls} value={cutoff} onChange={(e) => e.target.value && setCutoff(e.target.value)} />
            </Field>
          </div>
        )}

        {meta.data && day && tab === 'decision' && <DecisionView day={day} cutoff={cutoff} />}
        {meta.data && range.start && tab === 'accuracy' && <AccuracyView start={range.start} end={range.end} cutoff={cutoff} />}
        {tab === 'methodology' && <Methodology />}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-muted">
        Data: Elexon BMRS (WINDFOR, FUELHH). Snapshot bundled with the app; times shown in Europe/London.
      </footer>
    </div>
  )
}
