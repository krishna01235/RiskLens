'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { Float, PerspectiveCamera, Points, PointMaterial } from '@react-three/drei'
import { useReducedMotion } from 'framer-motion'
import { useMemo, useRef, type MutableRefObject } from 'react'
import type { Group } from 'three'
import GatewayFlow from '@/components/ui/gateway-flow'

type Pointer = MutableRefObject<{ x: number; y: number }>
type Palette = { accent: string; danger: string; muted: string; grid: string }
export type Palette = { accent: string; danger: string; muted: string; grid: string }

function Field({
  pointer,
  progress,
  stress,
  palette,
}: {
  pointer: Pointer
  progress: number
  stress: boolean
  palette: Palette
}) {
  const reduced = useReducedMotion()
  const group = useRef<Group>(null)
  const positions = useMemo(
    () =>
      new Float32Array(
        Array.from({ length: 1100 }, (_, i) => {
          const a = i * 0.27
          const r = 1.6 + Math.sin(i * 0.11) * 1.9
          return [Math.cos(a) * r, Math.sin(a * 0.73) * r * 0.5, Math.sin(a) * r].map(
            (v) => v + (Math.sin(i * 12.9898) * 43758.5453 % 1 - 0.5) * 0.3,
          )
        }).flat(),
      ),
    [],
  )
  useFrame((state, delta) => {
    const p = pointer.current
    const cam = state.camera
    cam.position.x += (p.x * 1.1 - cam.position.x) * 0.04
    cam.position.y += (p.y * 0.7 + 0.2 - cam.position.y) * 0.04
    cam.lookAt(0, 0, 0)
    if (group.current && !reduced) {
      group.current.rotation.y += delta * (0.05 + progress * 0.12)
      const scale = 1 + progress * 0.35
      group.current.scale.setScalar(scale)
    }
  })
  const color = stress ? palette.danger : palette.accent
  return (
    <group ref={group}>
      <Points positions={positions} stride={3}>
        <PointMaterial transparent color={color} size={0.028 + progress * 0.02} sizeAttenuation depthWrite={false} opacity={0.6} />
      </Points>
      <Float speed={stress ? 3 : 1.2} rotationIntensity={0.35} floatIntensity={0.6}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.25, 0.012, 8, 120]} />
          <meshBasicMaterial color={color} transparent opacity={0.4} />
        </mesh>
      </Float>
      <Float speed={0.9} rotationIntensity={0.6}>
        <mesh position={[0, 0.2, -0.4]}>
          <icosahedronGeometry args={[0.5, 1]} />
          <meshBasicMaterial color={color} wireframe transparent opacity={0.22} />
        </mesh>
      </Float>
    </group>
  )
}

export default function GatewayBackground({
  pointer,
  progress,
  stress,
  palette,
}: {
  pointer: Pointer
  progress: number
  stress: boolean
  palette: Palette
}) {
  // Scroll drives speed/hue live (no iframe rebuild). Stress pushes both harder.
  const speed = 0.55 + progress * 1.1 + (stress ? 0.9 : 0)
  const hue = stress ? 150 : progress * 40
  const opacity = 0.5 + progress * 0.25

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 bg-[#061014]" aria-hidden="true">
      <div className="absolute inset-0 opacity-90">
        <GatewayFlow className="h-full w-full" speed={speed} density={1} opacity={opacity} hue={hue} />
      </div>
      <div className="absolute inset-0">
        <Canvas dpr={[1, 1.5]} gl={{ antialias: false, alpha: true }} style={{ background: 'transparent' }}>
          <PerspectiveCamera makeDefault position={[0, 0, 6]} fov={52} />
          <Field pointer={pointer} progress={progress} stress={stress} palette={palette} />
        </Canvas>
      </div>
      {/* contrast scrims keep foreground copy readable over the animation */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,transparent_2%,rgba(6,16,20,.35)_55%,var(--background)_94%)]" />
      <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-background to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-background to-transparent" />
    </div>
  )
}
