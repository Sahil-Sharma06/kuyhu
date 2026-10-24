const TZ = 'Europe/London'

const mwFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

export const fmtMW = (v: number | null | undefined): string => (v == null ? '–' : `${mwFmt.format(v)} MW`)

export const fmtGW = (v: number): string => `${Number((v / 1000).toFixed(1))} GW`

export const fmtPct = (v: number | null | undefined): string => (v == null ? '–' : `${v.toFixed(1)}%`)

export const fmtSigned = (v: number | null | undefined): string =>
  v == null ? '–' : `${v > 0 ? '+' : ''}${mwFmt.format(v)} MW`

/** "14:30" in London time. */
export const fmtClock = (iso: string | number): string =>
  new Date(iso).toLocaleTimeString('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })

/** "Wed 14 Jan, 09:30" in London time. */
export const fmtDateTime = (iso: string): string =>
  new Date(iso).toLocaleString('en-GB', {
    timeZone: TZ,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })

/** "14 Jan" for a YYYY-MM-DD delivery day. */
export const fmtDay = (day: string): string =>
  new Date(`${day}T12:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
