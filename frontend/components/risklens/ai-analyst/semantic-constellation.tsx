'use client'

import { useEffect, useRef } from 'react'
import type { RiskScenarioState, RiskScenarioType } from './types'

// Simple 2D Vector
class Vec2 {
  constructor(public x: number, public y: number) {}
  add(v: Vec2) { this.x += v.x; this.y += v.y; return this }
  sub(v: Vec2) { this.x -= v.x; this.y -= v.y; return this }
  mult(n: number) { this.x *= n; this.y *= n; return this }
  mag() { return Math.sqrt(this.x * this.x + this.y * this.y) }
  normalize() { const m = this.mag(); if (m > 0) this.mult(1 / m); return this }
}

class Node {
  pos: Vec2
  vel: Vec2
  target: Vec2
  radius: number
  glow: number
  isKey: boolean

  constructor(x: number, y: number, isKey: boolean = false) {
    this.pos = new Vec2(x, y)
    this.target = new Vec2(x, y)
    this.vel = new Vec2(0, 0)
    this.radius = isKey ? 3 : 1.5
    this.glow = 0
    this.isKey = isKey
  }

  update(dt: number, state: RiskScenarioState) {
    // move towards target
    const force = new Vec2(this.target.x - this.pos.x, this.target.y - this.pos.y)
    force.mult(0.05)
    this.vel.add(force)
    this.vel.mult(0.85) // friction
    this.pos.add(this.vel)
    
    // gentle drift if idle
    if (state === 'idle') {
      this.target.x += (Math.random() - 0.5) * 2
      this.target.y += (Math.random() - 0.5) * 2
    }

    // fade glow
    this.glow = Math.max(0, this.glow - dt * 2)
  }
}

export default function SemanticConstellation({
  scenarioState,
  scenarioType,
}: {
  scenarioState: RiskScenarioState
  scenarioType: RiskScenarioType
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const cvs = canvasRef.current
    if (!cvs) return
    const ctx = cvs.getContext('2d')
    if (!ctx) return

    let width = cvs.clientWidth
    let height = cvs.clientHeight
    cvs.width = width * window.devicePixelRatio
    cvs.height = height * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)

    // init nodes
    const nodes: Node[] = []
    const numNodes = 30
    for (let i = 0; i < numNodes; i++) {
      nodes.push(new Node(width * Math.random(), height * Math.random(), i < 5))
    }

    let animationFrameId: number
    let lastTime = performance.now()

    const render = (time: number) => {
      const dt = (time - lastTime) / 1000
      lastTime = time

      // Update resize (if changed)
      if (cvs.clientWidth !== width || cvs.clientHeight !== height) {
        width = cvs.clientWidth
        height = cvs.clientHeight
        cvs.width = width * window.devicePixelRatio
        cvs.height = height * window.devicePixelRatio
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
      }

      ctx.clearRect(0, 0, width, height)

      // Get theme colors from computed style or fallback
      const style = getComputedStyle(document.body)
      const accent = style.getPropertyValue('--accent').trim() || '#5ce1e6'
      const muted = style.getPropertyValue('--muted').trim() || '#7e949d'
      const grid = style.getPropertyValue('--grid').trim() || '#274149'

      // Update nodes
      nodes.forEach((n) => n.update(dt, scenarioState))

      // If parsing/tool_call, organize the key nodes in a line and pulse them
      if (scenarioState === 'parsing' || scenarioState === 'tool_call') {
        const keyNodes = nodes.filter(n => n.isKey)
        keyNodes.forEach((n, i) => {
          n.target.x = width * 0.5
          n.target.y = (height * 0.3) + i * 25
          if (Math.random() < 0.05) n.glow = 1
        })
        const otherNodes = nodes.filter(n => !n.isKey)
        otherNodes.forEach((n) => {
           // swarm around center
           const center = new Vec2(width * 0.5, height * 0.5)
           const dir = new Vec2(center.x - n.pos.x, center.y - n.pos.y)
           dir.mult(0.01)
           n.vel.add(dir)
           if (Math.random() < 0.01) n.glow = 0.5
        })
      }

      // Draw edges
      ctx.lineWidth = 1
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const d = new Vec2(nodes[i].pos.x - nodes[j].pos.x, nodes[i].pos.y - nodes[j].pos.y).mag()
          if (d < 80) {
            ctx.beginPath()
            ctx.moveTo(nodes[i].pos.x, nodes[i].pos.y)
            ctx.lineTo(nodes[j].pos.x, nodes[j].pos.y)
            const alpha = (1 - d / 80) * 0.3 * (1 + Math.max(nodes[i].glow, nodes[j].glow))
            ctx.strokeStyle = `rgba(126, 148, 157, ${alpha})` // muted
            ctx.stroke()
          }
        }
      }

      // Draw nodes
      nodes.forEach((n) => {
        ctx.beginPath()
        ctx.arc(n.pos.x, n.pos.y, n.radius + n.glow * 2, 0, Math.PI * 2)
        ctx.fillStyle = n.glow > 0.1 ? accent : muted
        
        if (n.glow > 0.1) {
          ctx.shadowColor = accent
          ctx.shadowBlur = 10 * n.glow
        } else {
          ctx.shadowBlur = 0
        }
        
        ctx.fill()
        ctx.shadowBlur = 0
      })

      // Draw structured parameters if tool_call
      if (scenarioState === 'tool_call' || scenarioState === 'simulating') {
        ctx.font = '10px monospace'
        ctx.fillStyle = accent
        ctx.textAlign = 'center'
        const keyNodes = nodes.filter(n => n.isKey)
        const params = scenarioType === 'volatility' ? ['VOLATILITY +20%', 'HORIZON 10D', 'CONFIDENCE 99%'] 
                     : scenarioType === 'correlation' ? ['TECH SECTOR', 'CORRELATION +0.4', 'VaR MODEL']
                     : scenarioType === 'regime' ? ['HMM STATE', 'STRESS REGIME', 'TRANSITION 1.0']
                     : ['CAUSAL CHAIN', 'SHOCK EVENT', 'TRACE']

        keyNodes.slice(0, params.length).forEach((n, i) => {
           // Parameter text floats off to the right
           const slide = scenarioState === 'simulating' ? (time - lastTime)*0.1 : 0 
           ctx.fillText(params[i], n.pos.x + 40 + (scenarioState === 'simulating' ? 50 : 0), n.pos.y + 3)
           
           // Connecting line
           ctx.beginPath()
           ctx.moveTo(n.pos.x + 5, n.pos.y)
           ctx.lineTo(n.pos.x + 30 + (scenarioState === 'simulating' ? 50 : 0), n.pos.y)
           ctx.strokeStyle = accent
           ctx.globalAlpha = 0.5
           ctx.stroke()
           ctx.globalAlpha = 1.0
        })
      }

      animationFrameId = requestAnimationFrame(render)
    }

    animationFrameId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animationFrameId)
    }
  }, [scenarioState, scenarioType])

  return (
    <div className="relative h-full w-full">
      <p className="absolute left-4 top-4 mono text-[10px] tracking-widest text-muted z-10">AI ANALYST</p>
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      {/* Tool Call Bridge Line */}
      <div className={`absolute right-0 top-1/4 h-1/2 w-px transition-colors duration-700 ${scenarioState === 'tool_call' ? 'bg-accent shadow-[0_0_10px_var(--accent)]' : 'bg-grid'}`} />
      <p className={`absolute right-4 top-1/2 -translate-y-1/2 mono text-[9px] transition-opacity duration-500 ${scenarioState === 'tool_call' ? 'opacity-100 text-accent' : 'opacity-0'}`} style={{ writingMode: 'vertical-rl' }}>
        TOOL CALL
      </p>
    </div>
  )
}
