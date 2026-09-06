'use client'

import { useEffect, useRef } from 'react'
import type { RiskScenarioState, RiskScenarioType } from './types'

export default function QuantEnginePortal({
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

    let animationFrameId: number
    let startTimestamp = performance.now()

    // Monte Carlo state
    const numPaths = 50
    const paths: number[][] = Array.from({ length: numPaths }, () => [height / 2])
    const steps = 100
    
    // Generate pre-computed paths
    for (let p = 0; p < numPaths; p++) {
      let val = height / 2
      for (let s = 1; s < steps; s++) {
        // drift + vol (higher vol if scenarioType is volatility)
        const vol = scenarioType === 'volatility' ? 4 : 1.5
        val += (Math.random() - 0.5) * vol
        paths[p].push(val)
      }
    }

    const render = (time: number) => {
      // Handle resize
      if (cvs.clientWidth !== width || cvs.clientHeight !== height) {
        width = cvs.clientWidth
        height = cvs.clientHeight
        cvs.width = width * window.devicePixelRatio
        cvs.height = height * window.devicePixelRatio
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
      }

      ctx.clearRect(0, 0, width, height)

      const style = getComputedStyle(document.body)
      const accent = style.getPropertyValue('--accent').trim() || '#5ce1e6'
      const danger = style.getPropertyValue('--danger').trim() || '#ff6b6b'
      const gridColor = style.getPropertyValue('--grid').trim() || '#274149'
      const muted = style.getPropertyValue('--muted').trim() || '#7e949d'

      // Draw Grid
      ctx.strokeStyle = gridColor
      ctx.lineWidth = 1
      const gridSize = 40
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
      }

      if (scenarioState === 'simulating' || scenarioState === 'result') {
        const elapsed = time - startTimestamp
        const progress = Math.min(1, elapsed / 2000) // 2 second animation

        if (scenarioType === 'volatility' || scenarioType === 'regime') {
           // Draw Monte Carlo paths
           const stepWidth = width / steps
           const visibleSteps = Math.floor(progress * steps)
           
           for (let p = 0; p < numPaths; p++) {
             ctx.beginPath()
             ctx.moveTo(0, paths[p][0])
             for (let s = 1; s < visibleSteps; s++) {
               ctx.lineTo(s * stepWidth, paths[p][s])
             }
             // highlight tail paths in danger color
             const isTail = paths[p][steps - 1] > height * 0.75
             ctx.strokeStyle = isTail ? danger : accent
             ctx.globalAlpha = isTail ? 0.8 : 0.15
             ctx.stroke()
           }
           ctx.globalAlpha = 1.0

           // Draw distribution curve at the end if finished
           if (progress === 1) {
              ctx.beginPath()
              ctx.moveTo(width, height * 0.2)
              ctx.quadraticCurveTo(width - 60, height / 2, width, height * 0.8)
              ctx.strokeStyle = accent
              ctx.lineWidth = 2
              ctx.stroke()
              ctx.fillStyle = danger
              ctx.globalAlpha = 0.3
              ctx.fill()
              ctx.globalAlpha = 1.0
           }
        } else if (scenarioType === 'correlation') {
           // Draw correlation matrix visualization
           const cols = 5
           const rows = 5
           const cellSize = 30
           const startX = width / 2 - (cols * cellSize) / 2
           const startY = height / 2 - (rows * cellSize) / 2
           
           for (let r = 0; r < rows; r++) {
             for (let c = 0; c < cols; c++) {
                if (r === c) {
                  ctx.fillStyle = accent
                  ctx.globalAlpha = progress
                } else {
                  const val = Math.random()
                  ctx.fillStyle = val > 0.7 ? danger : muted
                  ctx.globalAlpha = progress * val
                }
                ctx.fillRect(startX + c * cellSize, startY + r * cellSize, cellSize - 2, cellSize - 2)
             }
           }
           ctx.globalAlpha = 1.0
        }
      } else {
        // Reset timestamp so when state changes it starts fresh
        startTimestamp = time
      }

      animationFrameId = requestAnimationFrame(render)
    }

    animationFrameId = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(animationFrameId)
    }
  }, [scenarioState, scenarioType])

  return (
    <div className="relative h-full w-full border border-grid bg-background/40 backdrop-blur-sm">
      <p className="absolute left-4 top-4 mono text-[10px] tracking-widest text-muted z-10">QUANT ENGINE</p>
      
      {/* Dynamic label based on active tool */}
      <p className={`absolute bottom-4 left-4 mono text-[10px] tracking-widest transition-opacity duration-300 ${scenarioState === 'simulating' || scenarioState === 'result' ? 'opacity-100 text-accent' : 'opacity-0'}`}>
        {scenarioType === 'volatility' ? 'MODEL / GARCH / MONTE CARLO' 
         : scenarioType === 'correlation' ? 'MODEL / L-W COVARIANCE'
         : 'MODEL / HMM REGIME'}
      </p>
      
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
    </div>
  )
}
