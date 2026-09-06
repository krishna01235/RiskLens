'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { Line, PerspectiveCamera } from '@react-three/drei'
import { useReducedMotion } from 'framer-motion'
import { Area, AreaChart, Line as RLine, ComposedChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useMemo, useRef, useState, type MutableRefObject } from 'react'
import type { Group, Vector3 } from 'three'
import { CircleDot, Crosshair, Layers, Target } from 'lucide-react'
import {
  horizonOptions,
  runMonteCarlo,
  simulationOptions,
  type HorizonKey,
  type MonteCarloPath,
  type MonteCarloResult,
  type SimulationKey,
} from '@/lib/risk-lab'

type Pointer = MutableRefObject<{ x: number; y: number }>
type Palette = { accent: string; danger: string; muted: string; grid: string }

function toPoints(path: MonteCarloPath, steps: number, id: number, count: number): [number, number, number][] {
  const z = (id / (count - 1) - 0.5) * 3.4
  return path.series.map((v, s) => [(s / steps) * 5 - 2.5, v * 0.14, z])
}

function PathCloud({
  data,
  pointer,
  hovered,
  setHovered,
  selected,
  setSelected,
  palette,
}: {
  data: MonteCarloResult
  pointer: Pointer
  hovered: number | null
  setHovered: (id: number | null) => void
  selected: number | null
  setSelected: (id: number | null) => void
  palette: Palette
}) {
  const reduced = useReducedMotion()
  const group = useRef<Group>(null)
  useFrame((state, delta) => {
    if (!group.current) return
    const p = pointer.current
    group.current.rotation.y += (p.x * 0.5 - group.current.rotation.y) * 0.05
    group.current.rotation.x += (-p.y * 0.25 - group.current.rotation.x) * 0.05
    if (!reduced) group.current.rotation.y += delta * 0.04
  })
  return (
    <group ref={group}>
      {data.paths.map((path) => {
        const active = hovered === path.id || selected === path.id
        const color = path.tail ? palette.danger : active ? palette.accent : palette.muted
        return (
          <Line
            key={path.id}
            points={toPoints(path, data.steps, path.id, data.count) as unknown as Vector3[]}
            color={color}
            lineWidth={active ? 2.4 : path.tail ? 1.3 : 0.7}
            transparent
            opacity={active ? 1 : path.tail ? 0.85 : 0.4}
            onPointerOver={(e) => {
              e.stopPropagation()
              setHovered(path.id)
              document.body.style.cursor = 'pointer'
            }}
            onPointerOut={() => {
              setHovered(null)
              document.body.style.cursor = 'auto'
            }}
            onClick={(e) => {
              e.stopPropagation()
              setSelected(selected === path.id ? null : path.id)
            }}
          />
        )
      })}
      <Line points={[[-2.5, 0, -1.8], [2.5, 0, -1.8]] as unknown as Vector3[]} color={palette.grid} lineWidth={1} />
    </group>
  )
}

function Scene3D(props: Parameters<typeof PathCloud>[0]) {
  return (
    <Canvas dpr={[1, 1.5]} gl={{ antialias: true }} onPointerMissed={() => props.setSelected(null)}>
      <color attach="background" args={['#0a181d']} />
      <PerspectiveCamera makeDefault position={[3.4, 2.4, 5.6]} fov={46} />
      <ambientLight intensity={0.7} />
      <PathCloud {...props} />
    </Canvas>
  )
}

function Fallback2D({ data }: { data: MonteCarloResult }) {
  const chart = data.bands.map((b) => ({ step: b.step, band: [b.p5, b.p95] as [number, number], p50: b.p50 }))
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={chart} margin={{ top: 16, right: 12, bottom: 8, left: 0 }}>
        <XAxis dataKey="step" hide />
        <YAxis width={34} tick={{ fill: 'var(--muted)', fontSize: 10, fontFamily: 'var(--font-technical)' }} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ background: 'var(--card)', border: '1px solid var(--grid)', fontFamily: 'var(--font-technical)', fontSize: 10 }}
          formatter={(v: number | number[]) => (Array.isArray(v) ? `${v[0]}% … ${v[1]}%` : `${v}%`)}
          labelFormatter={(s) => `STEP ${s}`}
        />
        <ReferenceLine y={0} stroke="var(--grid)" />
        <ReferenceLine y={-data.var95} stroke="var(--danger)" strokeDasharray="3 3" label={{ value: `VaR ${data.var95}%`, fill: 'var(--danger)', fontSize: 9, position: 'insideBottomLeft' }} />
        <Area dataKey="band" stroke="none" fill="var(--accent)" fillOpacity={0.12} />
        <RLine dataKey="p50" stroke="var(--accent)" strokeWidth={1.5} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

function Readout({ label, value, danger, mono = true }: { label: string; value: string; danger?: boolean; mono?: boolean }) {
  return (
    <div className="border-l border-grid pl-4">
      <p className="mono text-[10px] tracking-widest text-muted">{label}</p>
      <p className={`${mono ? 'mono' : ''} mt-2 text-2xl ${danger ? 'text-danger' : 'text-accent'}`}>{value}</p>
    </div>
  )
}

export default function MonteCarloChapter({
  pointer,
  shock,
  use2D,
  palette,
}: {
  pointer: Pointer
  shock: boolean
  use2D: boolean
  palette: Palette
}) {
  const [simulations, setSimulations] = useState<SimulationKey>('50K')
  const [horizon, setHorizon] = useState<HorizonKey>('5D')
  const [hovered, setHovered] = useState<number | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const data = useMemo(() => runMonteCarlo(simulations, horizon, shock), [simulations, horizon, shock])

  const focusId = hovered ?? selected
  const focusPath = focusId != null ? data.paths.find((p) => p.id === focusId) : null

  return (
    <div className="overflow-hidden border border-grid bg-card/70 backdrop-blur-md">
      {/* command-style control surface */}
      <div className="flex flex-wrap items-center gap-3 border-b border-grid p-4 md:p-5">
        <span className="mono flex items-center gap-2 text-[10px] tracking-widest text-accent">
          <Layers className="size-3.5" /> MONTE&nbsp;CARLO&nbsp;ENGINE
        </span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <span className="mono text-[10px] text-muted">PATHS</span>
          {simulationOptions.map((v) => (
            <button
              key={v}
              onClick={() => setSimulations(v)}
              aria-pressed={simulations === v}
              className={`mono border px-3 py-1.5 text-[10px] transition ${simulations === v ? 'border-accent bg-accent-soft text-accent' : 'border-grid text-muted hover:border-accent/50'}`}
            >
              {v}
            </button>
          ))}
          <span className="mono ml-2 text-[10px] text-muted">HORIZON</span>
          {horizonOptions.map((v) => (
            <button
              key={v}
              onClick={() => setHorizon(v)}
              aria-pressed={horizon === v}
              className={`mono border px-3 py-1.5 text-[10px] transition ${horizon === v ? 'border-accent bg-accent-soft text-accent' : 'border-grid text-muted hover:border-accent/50'}`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.35fr_.65fr]">
        {/* visualization */}
        <div className="relative h-[22rem] border-b border-grid lg:border-b-0 lg:border-r">
          {use2D ? (
            <div className="h-full w-full p-3 md:p-5">
              <Fallback2D data={data} />
            </div>
          ) : (
            <Scene3D
              data={data}
              pointer={pointer}
              hovered={hovered}
              setHovered={setHovered}
              selected={selected}
              setSelected={setSelected}
              palette={palette}
            />
          )}
          <div className="pointer-events-none absolute left-4 top-4 flex flex-col gap-1">
            <span className="mono flex items-center gap-1.5 text-[10px] text-accent"><CircleDot className="size-3" /> {data.count} paths rendered</span>
            <span className="mono flex items-center gap-1.5 text-[10px] text-danger"><Target className="size-3" /> tail ≤ {data.tailThreshold.toFixed(2)}%</span>
            {!use2D && (
              <span className="mono flex items-center gap-1.5 text-[10px] text-muted"><Crosshair className="size-3" /> hover / click a path</span>
            )}
          </div>
          {/* floating quant annotation */}
          <div className="pointer-events-none absolute bottom-4 right-4 border border-grid bg-background/70 p-3 backdrop-blur">
            <p className="mono text-[10px] text-muted">{'CVaR_\u03b1 = E[ L | L \u2265 VaR_\u03b1 ]'}</p>
          </div>
        </div>

        {/* linked readouts */}
        <div className="flex flex-col justify-between gap-6 p-5 md:p-6">
          <div className="grid grid-cols-2 gap-5">
            <Readout label="EXPECTED PnL" value={`${data.expected > 0 ? '+' : ''}${data.expected}%`} danger={data.expected < 0} />
            <Readout label="VaR 95%" value={`${data.var95}%`} danger />
            <Readout label="CVaR 95%" value={`${data.cvar95}%`} danger />
            <Readout label="WORST PATH" value={`${data.worst}%`} danger />
          </div>
          <div className="border border-grid bg-background/60 p-4">
            <p className="mono mb-2 text-[10px] tracking-widest text-muted">SELECTION READOUT</p>
            {focusPath ? (
              <div className="mono space-y-1 text-[11px]">
                <p className="text-accent">PATH #{String(focusPath.id).padStart(2, '0')}</p>
                <p className={focusPath.terminal < 0 ? 'text-danger' : 'text-foreground'}>
                  TERMINAL&nbsp;PnL&nbsp;→&nbsp;{focusPath.terminal > 0 ? '+' : ''}{focusPath.terminal.toFixed(2)}%
                </p>
                <p className="text-muted">CLASS → {focusPath.tail ? 'TAIL / EXTREME' : 'CENTRAL MASS'}</p>
              </div>
            ) : (
              <p className="mono text-[11px] leading-5 text-muted">
                {use2D ? 'Band shows the 5th–95th percentile cone; dashed line marks VaR.' : 'Hover a trajectory to inspect its terminal PnL and tail classification.'}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
