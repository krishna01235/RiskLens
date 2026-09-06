'use client'

import { motion, useReducedMotion } from 'framer-motion'
import { useMemo, useState } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronRight,
  CircleDot,
  LogIn,
  Play,
  RotateCcw,
  Settings2,
  UserPlus,
} from 'lucide-react'
import { assets, events, matrix, phases, regimes, type RiskTheme } from '@/lib/risk-lab'
import { useMediaQuery, usePointerRef, useScrollProgress } from '@/components/risklens/use-risklens'
import GatewayBackground from '@/components/risklens/background'
import MonteCarloChapter from '@/components/risklens/monte-carlo'
import RiskSurface from '@/components/risklens/risk-surface'

// Internal routes for the deployed app
const registerUrl = '/register'
const loginUrl = '/login'

const themes: RiskTheme[] = ['cyan', 'terminal', 'amber', 'crimson', 'mono']

// Three.js cannot read CSS custom properties, so mirror the theme tokens as hex here.
const palettes: Record<RiskTheme, { accent: string; danger: string; muted: string; grid: string }> = {
  cyan: { accent: '#5ce1e6', danger: '#ff6b6b', muted: '#7e949d', grid: '#274149' },
  terminal: { accent: '#9ef01a', danger: '#ffb000', muted: '#7e949d', grid: '#274149' },
  amber: { accent: '#f5b942', danger: '#ff6847', muted: '#7e949d', grid: '#274149' },
  crimson: { accent: '#ff5c75', danger: '#ffb3b3', muted: '#7e949d', grid: '#274149' },
  mono: { accent: '#d7e1e8', danger: '#aab4bb', muted: '#7e949d', grid: '#274149' },
}
const navLinks = [
  ['#why', 'WHY'],
  ['#engine', 'ENGINE'],
  ['#covariance', 'COVARIANCE'],
  ['#simulation', 'SIMULATION'],
  ['#surface', 'TAIL'],
  ['#regimes', 'REGIMES'],
]

/* ---------- primitives ---------- */

function StartButton({ full }: { full?: boolean }) {
  return (
    <a
      href={registerUrl}
      className={`group inline-flex items-center justify-center gap-2 border border-accent bg-accent px-6 py-3 mono text-[11px] tracking-widest text-accent-foreground transition hover:bg-transparent hover:text-accent ${full ? 'w-full' : ''}`}
      id="landing-cta-get-started"
    >
      GET STARTED
      <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
    </a>
  )
}

function SignInButton() {
  return (
    <a
      href={loginUrl}
      className="group inline-flex items-center gap-2 border border-grid px-4 py-3 mono text-[11px] tracking-widest text-muted transition hover:border-accent hover:text-accent"
      id="landing-cta-sign-in"
    >
      <LogIn className="size-3.5" />
      SIGN IN
    </a>
  )
}

// Uppercase, per-letter interactive hero heading. Full phrase exposed to AT via aria-label.
function InteractiveHeading({ lines }: { lines: { text: string; accent?: boolean }[][] }) {
  const reduced = useReducedMotion()
  const label = lines.map((line) => line.map((seg) => seg.text).join('')).join(' ')
  let index = 0
  return (
    <h1
      aria-label={label}
      className="text-balance text-6xl font-medium uppercase leading-[0.92] tracking-[-.06em] md:text-8xl lg:text-9xl"
    >
      {lines.map((line, li) => (
        <span key={li} className="block" aria-hidden="true">
          {line.map((seg, si) =>
            [...seg.text].map((ch) => {
              const i = index++
              if (ch === ' ') return <span key={`${li}-${si}-${i}`}>{'\u00A0'}</span>
              return (
                <motion.span
                  key={`${li}-${si}-${i}`}
                  className="inline-block cursor-default transition-colors duration-200 hover:text-accent"
                  style={seg.accent ? { color: 'var(--accent)' } : undefined}
                  initial={reduced ? false : { opacity: 0, y: '40%' }}
                  animate={reduced ? undefined : { opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  whileHover={reduced ? undefined : { y: -10, scale: 1.06 }}
                >
                  {ch}
                </motion.span>
              )
            }),
          )}
        </span>
      ))}
    </h1>
  )
}

function Section({
  eyebrow,
  title,
  children,
  id,
}: {
  eyebrow: string
  title: string
  children: React.ReactNode
  id?: string
}) {
  return (
    <section id={id} className="relative mx-auto max-w-7xl scroll-mt-24 px-5 py-28 md:px-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        className="mb-12 max-w-2xl"
      >
        <p className="mono mb-4 text-[10px] tracking-[.28em] text-accent">{eyebrow}</p>
        <h2 className="text-balance text-4xl font-medium tracking-[-.04em] md:text-6xl">{title}</h2>
      </motion.div>
      {children}
    </section>
  )
}

function Metric({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="border-l border-grid pl-4">
      <p className="mono text-[10px] tracking-widest text-muted">{label}</p>
      <p className={danger ? 'mono mt-2 text-2xl text-danger' : 'mono mt-2 text-2xl text-accent'}>{value}</p>
    </div>
  )
}

/* ---------- glass telemetry rail ---------- */

const telemetry = [
  ['SYS', 'ONLINE'],
  ['MODEL', 'GARCH'],
  ['REGIME', 'CALM'],
  ['TAIL', 'LOW'],
  ['LAT', '4.2ms'],
]

function TelemetryRail({ stress }: { stress: boolean }) {
  return (
    <div className="pointer-events-none fixed left-4 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-px border border-grid bg-background/50 backdrop-blur-md xl:flex">
      {telemetry.map(([k, v]) => {
        const hot = stress && k !== 'SYS' && k !== 'LAT'
        const val = stress && k === 'REGIME' ? 'STRESS' : stress && k === 'TAIL' ? 'HIGH' : v
        return (
          <div key={k} className="flex w-32 items-center justify-between px-3 py-2">
            <span className="mono text-[9px] tracking-widest text-muted">{k}</span>
            <span className={`mono text-[9px] ${hot ? 'text-danger' : 'text-accent'}`}>{val}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ---------- correlation network ---------- */

function CorrelationNetwork({ active, setActive }: { active: number; setActive: (i: number) => void }) {
  const nodes = useMemo(
    () =>
      assets.map((_, i) => {
        const a = (i / assets.length) * Math.PI * 2 - Math.PI / 2
        return { x: 50 + Math.cos(a) * 34, y: 50 + Math.sin(a) * 34 }
      }),
    [],
  )
  return (
    <div className="relative aspect-square w-full max-w-xl border border-grid bg-card/60 backdrop-blur">
      <svg viewBox="0 0 100 100" className="absolute inset-0 size-full" aria-hidden="true">
        {nodes.map((n, i) =>
          nodes.map((m, j) => {
            if (j <= i) return null
            const w = matrix[i][j]
            const linked = active === i || active === j
            return (
              <line
                key={`${i}-${j}`}
                x1={n.x}
                y1={n.y}
                x2={m.x}
                y2={m.y}
                stroke={linked ? 'var(--accent)' : 'var(--grid)'}
                strokeWidth={linked ? w * 1.4 : w * 0.6}
                opacity={linked ? 0.9 : 0.35}
              />
            )
          }),
        )}
        {nodes.map((n, i) => (
          <g key={i} className="cursor-pointer" onMouseEnter={() => setActive(i)} onClick={() => setActive(i)}>
            <circle cx={n.x} cy={n.y} r={active === i ? 4 : 2.6} fill={active === i ? 'var(--accent)' : 'var(--foreground)'}>
              <animate attributeName="r" values={`${active === i ? 4 : 2.6};${active === i ? 4.8 : 3};${active === i ? 4 : 2.6}`} dur="2.4s" repeatCount="indefinite" />
            </circle>
          </g>
        ))}
      </svg>
      {nodes.map((n, i) => (
        <button
          key={i}
          onMouseEnter={() => setActive(i)}
          onFocus={() => setActive(i)}
          onClick={() => setActive(i)}
          aria-label={`Focus asset ${assets[i]}`}
          className="mono absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap px-1 text-[9px] outline-none"
          style={{ left: `${n.x}%`, top: `${n.y > 50 ? n.y + 8 : n.y - 8}%`, color: active === i ? 'var(--accent)' : 'var(--muted)' }}
        >
          {assets[i]}
        </button>
      ))}
    </div>
  )
}

/* ---------- page ---------- */

export default function RiskLensExperience() {
  const [theme, setTheme] = useState<RiskTheme>('cyan')
  const [shock, setShock] = useState(false)
  const [stressPhase, setStressPhase] = useState(0)
  const [activeAsset, setActiveAsset] = useState(2)

  const progress = useScrollProgress()
  const pointer = usePointerRef()
  const reduced = useReducedMotion()
  const isMobile = useMediaQuery('(max-width: 900px)')
  const use2D = isMobile || !!reduced
  const palette = palettes[theme]

  const runStress = () => {
    setShock(true)
    setStressPhase(5)
    window.setTimeout(() => setStressPhase(0), 5000)
  }
  const resetStress = () => {
    setShock(false)
    setStressPhase(0)
  }

  return (
    <main data-theme={theme} data-landing="true" className="relative min-h-screen bg-background text-foreground landing-root">
      <GatewayBackground pointer={pointer} progress={progress} stress={shock} palette={palette} />
      <TelemetryRail stress={shock} />

      {/* nav */}
      <nav className="fixed left-1/2 top-4 z-50 flex w-[calc(100%-2rem)] max-w-6xl -translate-x-1/2 items-center justify-between border border-grid bg-background/70 px-4 py-3 backdrop-blur-md" aria-label="Main navigation">
        <a href="#top" className="flex items-center gap-2 font-semibold tracking-[-.04em]">
          <span className="size-2 bg-accent" />
          RISK<span className="text-accent">/</span>LENS
        </a>
        <div className="mono hidden items-center gap-5 text-[10px] tracking-widest text-muted lg:flex">
          {navLinks.map(([href, label]) => (
            <a key={href} href={href} className="transition-colors hover:text-accent">
              {label}
            </a>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <span className="mono hidden text-[10px] text-success md:inline">● LIVE</span>
          <select
            aria-label="Color theme"
            value={theme}
            onChange={(e) => setTheme(e.target.value as RiskTheme)}
            className="mono hidden bg-transparent text-[10px] text-muted outline-none sm:block"
          >
            {themes.map((t) => (
              <option key={t} value={t}>
                {t.toUpperCase()}
              </option>
            ))}
          </select>
          {/* Auth buttons */}
          <SignInButton />
          <StartButton />
        </div>
      </nav>

      {/* hero */}
      <section id="top" className="relative flex min-h-screen items-center overflow-hidden">
        <div className="relative z-10 mx-auto w-full max-w-7xl px-5 pt-24 md:px-10">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="mono mb-6 text-[10px] tracking-[.34em] text-accent"
          >
            REAL-TIME QUANTITATIVE RISK PLATFORM
          </motion.p>
          <div className="max-w-4xl">
            <InteractiveHeading
              lines={[
                [{ text: 'SEE RISK' }],
                [{ text: 'BEFORE ', accent: true }, { text: 'IT MOVES' }],
              ]}
            />
          </div>
          <p className="mt-8 max-w-md text-pretty text-lg leading-7 text-muted">
            An event-driven quantitative risk engine for continuously evolving markets. Explore thousands of futures,
            interrogate the tail, and stress the book in real time.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-3">
            <StartButton />
            <a
              href="#simulation"
              className="inline-flex items-center gap-2 border border-grid px-5 py-3 mono text-[10px] tracking-widest text-muted transition hover:border-accent hover:text-accent"
            >
              EXPLORE SIMULATION
              <ArrowDownRight className="size-4" />
            </a>
          </div>
          <div className="mt-20 grid max-w-xl grid-cols-2 gap-5 border-t border-grid pt-5 md:grid-cols-4">
            {[
              ['64', 'PATHS / FRAME'],
              ['4.2ms', 'RISK LATENCY'],
              ['EVT', 'TAIL MODEL'],
              ['L-W', 'COVARIANCE'],
            ].map(([v, k]) => (
              <div key={k}>
                <p className="mono text-lg text-accent">{v}</p>
                <p className="mono mt-1 text-[9px] tracking-widest text-muted">{k}</p>
              </div>
            ))}
          </div>
        </div>
        {shock && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-8 right-8 z-10 border border-danger bg-background/80 p-4 mono text-[10px] text-danger backdrop-blur"
          >
            <CircleDot className="mb-2 size-4" />
            VOLATILITY SHIFT DETECTED
            <br />
            RISK STATE → ELEVATED
          </motion.div>
        )}
      </section>

      {/* why */}
      <Section id="why" eyebrow="00 / THE CASE FOR CLARITY" title="Risk should be a surface, not a spreadsheet.">
        <div className="grid gap-px border border-grid bg-grid md:grid-cols-4">
          {[
            ['01', 'SEE THE INVISIBLE', 'Surface concentration, hidden correlation, and tail exposure before they become losses.'],
            ['02', 'THINK IN REGIMES', 'Separate calm from stress with state-aware signals instead of one static forecast.'],
            ['03', 'STRESS WITH INTENT', 'Move the market, pull the levers, and see exactly how your book responds.'],
            ['04', 'EXPLAIN EVERY NUMBER', 'Trace VaR, CVaR, and drawdown back to events, assumptions, and model state.'],
          ].map(([n, h, d]) => (
            <motion.article
              whileHover={{ y: -6 }}
              key={n}
              className="group bg-card/70 p-6 backdrop-blur transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <span className="mono text-[10px] text-accent group-hover:text-accent-foreground/70">{n}</span>
              <h3 className="mt-10 text-xl tracking-[-.03em]">{h}</h3>
              <p className="mt-4 text-sm leading-6 text-muted group-hover:text-accent-foreground/75">{d}</p>
              <ChevronRight className="mt-10 size-4 text-accent group-hover:text-accent-foreground" />
            </motion.article>
          ))}
        </div>
      </Section>

      {/* engine */}
      <Section id="engine" eyebrow="01 / EVENT STREAM" title="It starts with an event.">
        <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
          <div className="border border-grid bg-card/70 p-6 mono text-xs backdrop-blur">
            {events.map(([time, event, asset], i) => (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                key={i}
                className="flex gap-4 border-b border-grid py-3 last:border-0"
              >
                <span className="text-muted">{time}</span>
                <span className={event === 'VOL_SHIFT' ? 'text-danger' : 'text-accent'}>{event}</span>
                <span>{asset}</span>
                <ArrowDownRight className="ml-auto size-3 text-muted" />
              </motion.div>
            ))}
          </div>
          <div className="relative min-h-64 overflow-hidden border border-grid bg-card/70 p-6 backdrop-blur">
            <p className="mono text-[10px] tracking-widest text-muted">EVENT → RISK ENGINE → STATE</p>
            <div className="absolute inset-x-8 top-1/2 flex items-center justify-between">
              <motion.div animate={{ scale: [1, 1.45, 1] }} transition={{ repeat: Infinity, duration: 2 }} className="size-4 rounded-full bg-accent shadow-[0_0_25px_var(--accent)]" />
              <div className="h-px flex-1 bg-accent/40" />
              <div className="size-8 border border-accent p-2">
                <Settings2 className="size-4 text-accent" />
              </div>
              <div className="h-px flex-1 bg-accent/40" />
              <motion.div animate={{ scale: [1, 1.45, 1] }} transition={{ repeat: Infinity, duration: 2, delay: 1 }} className="size-4 rounded-full bg-danger shadow-[0_0_25px_var(--danger)]" />
            </div>
            <p className="absolute bottom-5 left-6 mono text-[10px] text-accent">CORRELATION PROPAGATING / 4.2ms</p>
          </div>
        </div>
      </Section>

      {/* covariance + network */}
      <Section id="covariance" eyebrow="02 / COVARIANCE" title="Markets move together.">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr]">
          <CorrelationNetwork active={activeAsset} setActive={setActiveAsset} />
          <div className="flex flex-col justify-center gap-8">
            <p className="mono text-sm leading-7 text-muted">
              Ledoit–Wolf covariance estimates form a living network of concentration, exposure, and shared movement.
              Focus a node to trace how a shock propagates across the book.
            </p>
            <div className="grid grid-cols-2 gap-6">
              <Metric label="ASSET FOCUS" value={assets[activeAsset]} />
              <Metric label="MAX CORRELATION" value={`${Math.max(...matrix[activeAsset].filter((_, j) => j !== activeAsset))}`} />
              <Metric label="CONCENTRATION" value="31.8%" />
              <Metric label="ESTIMATOR" value="L-W 2.1" />
            </div>
          </div>
        </div>
      </Section>

      {/* monte carlo */}
      <Section id="simulation" eyebrow="03 / MONTE CARLO" title="One future is not enough.">
        <p className="mono mb-8 max-w-2xl text-sm leading-7 text-muted">
          RiskLens explores thousands of plausible futures, then turns their shape into a surface you can orbit and
          interrogate. Loss trajectories in the 5% tail are highlighted; hover any path for its terminal PnL.
        </p>
        <MonteCarloChapter pointer={pointer} shock={shock} use2D={use2D} palette={palette} />
      </Section>

      {/* tail surface */}
      <Section id="surface" eyebrow="04 / TAIL SURFACE" title="Where normality ends, risk begins.">
        <div className="grid gap-8 lg:grid-cols-[1.2fr_.8fr]">
          <div className="overflow-hidden border border-grid bg-card/70 backdrop-blur">
            {use2D ? (
              <div className="flex h-80 items-center justify-center p-8 text-center">
                <p className="mono text-xs leading-6 text-muted">
                  Interactive tail surface is available on larger screens with motion enabled. VaR / CVaR readouts
                  remain fully accurate below.
                </p>
              </div>
            ) : (
              <RiskSurface shock={shock} palette={palette} />
            )}
          </div>
          <div className="flex flex-col justify-center gap-6">
            <p className="mono text-sm leading-7 text-muted">
              Drag the surface. Rotate the assumptions. The tail is not a footnote—it is the terrain your portfolio must
              cross.
            </p>
            <Metric label="CONFIDENCE LEVEL" value="95%" />
            <Metric label="TAIL PRESSURE" value={shock ? 'HIGH' : 'LOW'} danger={shock} />
            <Metric label="EXTREME MODEL" value="EVT / GPD" />
          </div>
        </div>
      </Section>

      {/* regimes */}
      <Section id="regimes" eyebrow="05 / HIDDEN STATES" title="The market changes character.">
        <div className="relative min-h-80 border border-grid bg-card/60 backdrop-blur">
          <svg className="absolute inset-0 size-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {regimes.map((r, i) => (
              <line key={r.name} x1={r.x} y1={r.y} x2={regimes[(i + 1) % 4].x} y2={regimes[(i + 1) % 4].y} stroke="var(--grid)" strokeDasharray="2 2" />
            ))}
          </svg>
          {regimes.map((r) => (
            <motion.div whileHover={{ scale: 1.12 }} key={r.name} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${r.x}%`, top: `${r.y}%` }}>
              <div className="size-16 rounded-full border border-current bg-background p-5" style={{ color: r.color }}>
                <div className="size-full rounded-full bg-current shadow-[0_0_30px_currentColor]" />
              </div>
              <p className="mt-3 text-center mono text-[10px]" style={{ color: r.color }}>
                {r.name}
              </p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* stress climax */}
      <section className="relative border-y border-grid bg-card/70 py-28 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-10 px-5 md:flex-row md:items-end md:px-10">
          <div>
            <p className="mono mb-4 text-[10px] tracking-[.28em] text-danger">SYSTEM INTERVENTION</p>
            <h2 className="text-5xl uppercase tracking-[-.06em] md:text-8xl">
              Break the
              <br />
              <span className="text-danger">market.</span>
            </h2>
          </div>
          <div className="max-w-sm">
            <p className="mono text-xs leading-6 text-muted">
              Stress the event pipeline. Watch correlation rise, paths fan out, and the hidden state transition across
              the entire experience.
            </p>
            <div className="mt-8 flex items-center gap-3">
              <button
                onClick={runStress}
                id="landing-stress-btn"
                className="inline-flex items-center gap-3 border border-danger px-5 py-3 mono text-[10px] tracking-widest text-danger transition hover:bg-danger hover:text-background"
              >
                <Play className="size-4" />
                {stressPhase ? phases[stressPhase] : 'BREAK THE MARKET'}
              </button>
              {shock && (
                <button onClick={resetStress} aria-label="Reset market" className="border border-grid p-3 text-muted transition hover:border-accent hover:text-accent">
                  <RotateCcw className="size-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* final CTA */}
      <section className="relative border-b border-grid py-24">
        <div className="mx-auto max-w-7xl px-5 text-center md:px-10">
          <p className="mono mb-4 text-[10px] tracking-[.28em] text-muted">NO CREDIT CARD. NO CONFIGURATION. INSTANT DEMO DATA.</p>
          <h2 className="mb-8 text-4xl font-medium tracking-[-.04em] md:text-6xl">
            See your portfolio through a
            <br />
            <span className="text-accent">quant lens.</span>
          </h2>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <StartButton />
            <a
              href={loginUrl}
              className="inline-flex items-center gap-2 border border-grid px-6 py-3 mono text-[11px] tracking-widest text-muted transition hover:border-accent hover:text-accent"
            >
              <UserPlus className="size-4" />
              ALREADY HAVE AN ACCOUNT
            </a>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="relative border-t border-grid">
        <div className="mx-auto max-w-7xl px-5 py-20 md:px-10">
          <div className="flex flex-col justify-between gap-10 md:flex-row md:items-end">
            <div>
              <a href="#top" className="flex items-center gap-2 text-2xl font-semibold tracking-[-.04em]">
                <span className="size-2.5 bg-accent" />
                RISK<span className="text-accent">/</span>LENS
              </a>
              <h2 className="mt-6 text-4xl uppercase tracking-[-.06em] md:text-6xl">
                Make risk
                <br />
                <span className="text-accent">visible.</span>
              </h2>
              <p className="mt-6 max-w-md text-muted">
                RiskLens turns live market events into interpretable, testable quantitative risk.
              </p>
            </div>
            <div className="flex flex-col gap-6">
              <div className="grid grid-cols-2 gap-x-12 gap-y-3">
                {navLinks.map(([href, label]) => (
                  <a key={href} href={href} className="mono text-[10px] tracking-widest text-muted transition hover:text-accent">
                    {label}
                  </a>
                ))}
              </div>
              <div className="flex gap-3">
                <StartButton />
                <a
                  href={loginUrl}
                  className="inline-flex items-center gap-2 border border-grid px-4 py-3 mono text-[11px] tracking-widest text-muted transition hover:border-accent hover:text-accent"
                >
                  SIGN IN
                </a>
              </div>
            </div>
          </div>

          <div className="mt-16 flex flex-col gap-6 border-t border-grid pt-8 md:flex-row md:items-center md:justify-between">
            <p className="mono max-w-xl text-[10px] leading-5 text-muted">
              MODEL DISCLAIMER — Figures shown are deterministic demonstration data generated in-browser for
              illustration only. Not investment advice. Risk models are estimates and may not capture all sources of
              loss.
            </p>
            <div className="flex items-center gap-6">
              <span className="mono text-[10px] text-success">● SYSTEM READY</span>
              <span className="mono text-[10px] text-muted">v0.3.0</span>
              <span className="mono text-[10px] text-muted">BUILD 2026.09</span>
              <span className="mono text-[10px] text-muted">© 2026 RiskLens</span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  )
}
