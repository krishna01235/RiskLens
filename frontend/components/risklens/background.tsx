'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { Float, PerspectiveCamera, Points, PointMaterial } from '@react-three/drei'
import { useReducedMotion } from 'framer-motion'
import { useMemo, useRef, type MutableRefObject } from 'react'
import type { Group, Mesh, MeshBasicMaterial } from 'three'

type Pointer = MutableRefObject<{ x: number; y: number }>
type Palette = { accent: string; danger: string; muted: string; grid: string }
export type Palette = { accent: string; danger: string; muted: string; grid: string }

function Field({
  pointer,
  progress,
  stress,
  palette,
  aiInView,
}: {
  pointer: Pointer
  progress: number
  stress: boolean
  palette: Palette
  aiInView?: boolean
}) {
  const reduced = useReducedMotion()
  const group = useRef<Group>(null)
  const lensRef = useRef<Mesh>(null)
  const lensMatRef = useRef<MeshBasicMaterial>(null)
  const aiProgress = useRef(0)

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
    
    // Lens animation transition
    const targetAi = aiInView ? 1 : 0
    aiProgress.current += (targetAi - aiProgress.current) * 0.05

    // Mouse movement
    cam.position.x += (p.x * 1.1 - cam.position.x) * 0.04
    cam.position.y += (p.y * 0.7 + 0.2 - cam.position.y) * 0.04
    cam.lookAt(0, 0, 0)
    
    if (group.current && !reduced) {
      // Slow down rotation when AI section is in view
      const speedMult = 1 - aiProgress.current * 0.85
      group.current.rotation.y += delta * (0.05 + progress * 0.12) * speedMult
      
      const scale = 1 + progress * 0.35 - (aiProgress.current * 0.15)
      group.current.scale.setScalar(scale)
    }

    if (lensRef.current && lensMatRef.current) {
      const s = 0.5 + aiProgress.current * 1.2
      lensRef.current.scale.setScalar(s)
      lensMatRef.current.opacity = aiProgress.current * 0.6
      lensRef.current.rotation.z += delta * 0.2
    }
  })

  const color = stress ? palette.danger : palette.accent
  
  return (
    <group ref={group}>
      <Points positions={positions} stride={3}>
        <PointMaterial transparent color={color} size={0.028 + progress * 0.02} sizeAttenuation depthWrite={false} opacity={0.6} />
      </Points>
      
      {/* Lens ring for AI section */}
      <mesh ref={lensRef} position={[0, 0, 0.5]}>
        <ringGeometry args={[1.4, 1.42, 64]} />
        <meshBasicMaterial ref={lensMatRef} color={palette.accent} transparent opacity={0} depthWrite={false} />
      </mesh>
      <mesh position={[0, 0, 0.5]} scale={1.05}>
         {/* Subtle inner glow for lens */}
         <ringGeometry args={[1.35, 1.4, 64]} />
         <meshBasicMaterial color={palette.accent} transparent opacity={aiInView ? 0.15 : 0} depthWrite={false} />
      </mesh>

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
  aiSectionInView,
}: {
  pointer: Pointer
  progress: number
  stress: boolean
  palette: Palette
  aiSectionInView?: boolean
}) {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 bg-[#061014]" aria-hidden="true">
      <div className="absolute inset-0">
        <Canvas dpr={[1, 1.5]} gl={{ antialias: false, alpha: true }} style={{ background: 'transparent' }}>
          <PerspectiveCamera makeDefault position={[0, 0, 6]} fov={52} />
          <Field pointer={pointer} progress={progress} stress={stress} palette={palette} aiInView={aiSectionInView} />
        </Canvas>
      </div>
      {/* contrast scrims keep foreground copy readable over the animation */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,transparent_2%,rgba(6,16,20,.35)_55%,var(--background)_94%)]" />
      <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-background to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-background to-transparent" />
    </div>
  )
}
