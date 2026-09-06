export const riskThemes = {
  cyan: { accent: '#5ce1e6', glow: '#1b8790', danger: '#ff6b6b' },
  terminal: { accent: '#9ef01a', glow: '#3b7210', danger: '#ffb000' },
  amber: { accent: '#f5b942', glow: '#8d5e11', danger: '#ff6847' },
  crimson: { accent: '#ff5c75', glow: '#8f223d', danger: '#ffb3b3' },
  mono: { accent: '#d7e1e8', glow: '#66737d', danger: '#aab4bb' },
} as const

export const assets = ['BTC-USD', 'SPY', 'SPX', 'BOOK_07', 'EURUSD', 'UST10Y']
export const events = [
  ['09:41:21.008', 'TICK', 'BTC-USD'], ['09:41:21.011', 'TICK', 'SPY'],
  ['09:41:21.014', 'VOL_SHIFT', 'SPX'], ['09:41:21.019', 'EXPOSURE', 'BOOK_07'],
  ['09:41:21.024', 'RISK_CALC', 'BOOK_07'], ['09:41:21.030', 'REGIME', 'TRANSITION'],
]
export const matrix = assets.map((_, i) => assets.map((__, j) => Number((i === j ? 1 : 0.18 + Math.abs(Math.sin(i * 4 + j)) * 0.62).toFixed(2))))
export const paths = Array.from({ length: 42 }, (_, path) => Array.from({ length: 28 }, (_, step) => {
  const t = step / 27
  return 50 + Math.sin(path * 1.7 + step * 0.38) * (4 + t * 14) + (path - 20) * t * 0.45
}))
export const regimes = [
  { name: 'CALM', color: 'var(--success)', x: 16, y: 50 },
  { name: 'VOLATILE', color: 'var(--accent)', x: 45, y: 24 },
  { name: 'STRESS', color: 'var(--danger)', x: 75, y: 48 },
  { name: 'RECOVERY', color: 'var(--warning)', x: 48, y: 77 },
]
export const phases = ['CALM', 'SHOCK ENTERS', 'CORRELATION RISES', 'VOLATILITY CLUSTERS', 'TAIL EXPANDS', 'SYSTEM STRESSED']

export function riskMetrics(shock: boolean, simulations: string, horizon: string) {
  const multiplier = shock ? 1.42 : 1
  const sim = simulations === '100K+' ? 1.02 : simulations === '50K' ? 1.01 : 1
  const day = horizon === '10D' ? 1.7 : horizon === '5D' ? 1.34 : 1
  return { var: (2.41 * multiplier * sim * day).toFixed(2), cvar: (3.18 * multiplier * sim * day).toFixed(2), vol: (18.6 * multiplier).toFixed(1), tail: shock ? 'HIGH' : 'LOW' }
}

type Theme = keyof typeof riskThemes
export function themeStyle(theme: Theme) { return riskThemes[theme] }
export type RiskTheme = Theme

/* ---------- Deterministic Monte Carlo lab ---------- */

export const simulationOptions = ['10K', '50K', '100K+'] as const
export const horizonOptions = ['1D', '5D', '10D'] as const
export type SimulationKey = (typeof simulationOptions)[number]
export type HorizonKey = (typeof horizonOptions)[number]

const horizonDays: Record<HorizonKey, number> = { '1D': 1, '5D': 5, '10D': 10 }
const simSeed: Record<SimulationKey, number> = { '10K': 0x10a5, '50K': 0x50b7, '100K+': 0xf00d }

function mulberry32(seed: number) {
  let a = seed >>> 0
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function gaussian(rng: () => number) {
  let u = 0
  let v = 0
  while (u === 0) u = rng()
  while (v === 0) v = rng()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

export type MonteCarloPath = { id: number; series: number[]; terminal: number; tail: boolean }
export type MonteCarloResult = {
  paths: MonteCarloPath[]
  steps: number
  count: number
  horizonDays: number
  tailThreshold: number
  var95: number
  cvar95: number
  expected: number
  worst: number
  best: number
  bands: { step: number; p5: number; p50: number; p95: number }[]
}

const VIZ_PATHS = 64

// Deterministic given (simulations, horizon, shock): same inputs always yield identical output.
export function runMonteCarlo(simulations: SimulationKey, horizon: HorizonKey, shock = false): MonteCarloResult {
  const rng = mulberry32(simSeed[simulations] ^ (horizonDays[horizon] * 2654435761))
  const days = horizonDays[horizon]
  const steps = days * 8
  const drift = 0.0002 - (shock ? 0.0016 : 0)
  const vol = (0.012 + (shock ? 0.02 : 0)) / Math.sqrt(8)
  const count = VIZ_PATHS

  const paths: MonteCarloPath[] = []
  for (let i = 0; i < count; i++) {
    const series = [0]
    let v = 0
    for (let s = 0; s < steps; s++) {
      const z = gaussian(rng)
      v += drift + vol * z
      series.push(Number((v * 100).toFixed(3)))
    }
    paths.push({ id: i, series, terminal: series[series.length - 1], tail: false })
  }

  const terminals = paths.map((p) => p.terminal).sort((a, b) => a - b)
  const tailIdx = Math.max(0, Math.floor(0.05 * count))
  const tailThreshold = terminals[tailIdx]
  const var95 = -tailThreshold
  const cvar95 = -(terminals.slice(0, tailIdx + 1).reduce((a, b) => a + b, 0) / (tailIdx + 1))
  const expected = paths.reduce((a, b) => a + b.terminal, 0) / count
  paths.forEach((p) => { p.tail = p.terminal <= tailThreshold })

  const bands = Array.from({ length: steps + 1 }, (_, s) => {
    const col = paths.map((p) => p.series[s]).sort((a, b) => a - b)
    const at = (q: number) => col[Math.min(col.length - 1, Math.floor(q * (col.length - 1)))]
    return { step: s, p5: at(0.05), p50: at(0.5), p95: at(0.95) }
  })

  return {
    paths,
    steps,
    count,
    horizonDays: days,
    tailThreshold,
    var95: Number(var95.toFixed(2)),
    cvar95: Number(cvar95.toFixed(2)),
    expected: Number(expected.toFixed(2)),
    worst: Number(terminals[0].toFixed(2)),
    best: Number(terminals[terminals.length - 1].toFixed(2)),
    bands,
  }
}
