import { useEffect, useState } from 'react'
import { getJson } from './api'

export interface Async<T> {
  data: T | null
  error: string | null
  loading: boolean
}

/** Fetch `path` whenever it or `params` change; stale responses are discarded. */
export function useApi<T>(path: string | null, params: Record<string, string> = {}): Async<T> {
  const key = path ? `${path}?${new URLSearchParams(params)}` : null
  const [state, setState] = useState<Async<T>>({ data: null, error: null, loading: true })

  useEffect(() => {
    if (!path) return
    let live = true
    setState((s) => ({ ...s, loading: true, error: null }))
    getJson<T>(path, params)
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((e: Error) => live && setState({ data: null, error: e.message, loading: false }))
    return () => {
      live = false
    }
    // `key` captures path + params by value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}

const VARS = ['--series-1', '--series-2', '--series-3', '--ink-2', '--muted', '--grid', '--axis', '--surface', '--critical'] as const
export type ChartColors = Record<(typeof VARS)[number], string>

const readColors = (): ChartColors => {
  const css = getComputedStyle(document.documentElement)
  return Object.fromEntries(VARS.map((v) => [v, css.getPropertyValue(v).trim()])) as ChartColors
}

/** Resolved theme colors for SVG chart attributes, kept in sync with the OS color scheme. */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState(readColors)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setColors(readColors())
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return colors
}
