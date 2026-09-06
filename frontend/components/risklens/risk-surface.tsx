'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { Line, OrbitControls } from '@react-three/drei'
import { useReducedMotion } from 'framer-motion'
import { useMemo, useRef } from 'react'
import type { Mesh, Vector3 } from 'three'

const COLS = 14
const ROWS = 12

type Palette = { accent: string; danger: string; muted: string; grid: string }

function Surface({ shock, palette }: { shock: boolean; palette: Palette }) {
  const reduced = useReducedMotion()
  const refs = useRef<(Mesh | null)[]>([])
  const base = useMemo(
    () =>
      Array.from({ length: COLS * ROWS }, (_, i) => {
        const x = ((i % COLS) / (COLS - 1)) * 4 - 2
        const z = (Math.floor(i / COLS) / (ROWS - 1)) * 3.2 - 1.6
        return { x, z }
      }),
    [],
  )
  useFrame(({ clock }) => {
    const t = reduced ? 0 : clock.elapsedTime
    base.forEach(({ x, z }, i) => {
      const m = refs.current[i]
      if (!m) return
      const y =
        Math.sin(x * 1.5 + t * 0.5) * 0.18 +
        Math.cos(z * 2.1 + t * 0.3) * 0.22 +
        (shock ? Math.sin(x * 3 + z * 2 + t) * 0.3 : 0)
      m.position.y = y
      m.scale.setScalar(0.6 + Math.max(0, y) * 1.4)
    })
  })
  return (
    <group rotation={[-0.28, 0, 0]}>
      {base.map(({ x, z }, i) => (
        <mesh key={i} ref={(el) => { refs.current[i] = el }} position={[x, 0, z]}>
          <sphereGeometry args={[0.03, 8, 8]} />
          <meshBasicMaterial color={shock ? palette.danger : palette.accent} transparent opacity={0.8} />
        </mesh>
      ))}
      <Line points={[[-2, -0.2, -1.6], [2, -0.2, -1.6], [2, -0.2, 1.6]] as unknown as Vector3[]} color={palette.grid} lineWidth={1} />
    </group>
  )
}

export default function RiskSurface({ shock, palette }: { shock: boolean; palette: Palette }) {
  return (
    <div className="h-80 w-full">
      <Canvas camera={{ position: [4.3, 3.3, 5.5], fov: 42 }}>
        <color attach="background" args={['#0a181d']} />
        <ambientLight intensity={0.8} />
        <Surface shock={shock} palette={palette} />
        <gridHelper args={[5, 12, '#274149', '#13282d']} position={[0, -0.24, 0]} />
        <OrbitControls enablePan={false} minDistance={3.5} maxDistance={8} />
      </Canvas>
    </div>
  )
}
