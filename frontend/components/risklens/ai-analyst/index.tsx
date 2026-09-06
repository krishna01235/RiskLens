'use client'

import { forwardRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Play, RotateCcw } from 'lucide-react'
import type { RiskScenarioState, RiskScenarioType } from './types'
import PromptConsole from './prompt-console'
import SemanticConstellation from './semantic-constellation'
import QuantEnginePortal from './quant-engine-portal'
import RiskReadout from './risk-readout'

export default forwardRef<HTMLElement, { onTriggerStress: () => void }>(function RiskAnalystSection({ onTriggerStress }, ref) {
  const [state, setState] = useState<RiskScenarioState>('idle')
  const [type, setType] = useState<RiskScenarioType>('volatility')

  const runSequence = (query: string, scenarioType: RiskScenarioType) => {
    setType(scenarioType)
    setState('parsing')
    
    // Simulate the sequence
    setTimeout(() => {
      setState('tool_call')
    }, 2000) // parsing intent, building risk query...
    
    setTimeout(() => {
      setState('simulating')
    }, 3200) // quant engine boots up
    
    setTimeout(() => {
      setState('result')
    }, 5200) // result ready
  }

  const handleWhy = () => {
    // Reveal causal chain
    setType('why')
    setState('tool_call')
    setTimeout(() => setState('simulating'), 1000)
    setTimeout(() => setState('result'), 3000)
  }

  const handleReset = () => {
    setState('idle')
  }

  return (
    <section ref={ref} className="relative mx-auto max-w-7xl scroll-mt-24 px-5 py-32 md:px-10 min-h-screen">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        className="mb-16 max-w-2xl"
      >
        <p className="mono mb-4 text-[10px] tracking-[.28em] text-accent">INTELLIGENT RISK ANALYSIS</p>
        <h2 className="text-balance text-4xl font-medium tracking-[-.04em] md:text-6xl">ASK THE ENGINE.</h2>
        <p className="mt-4 text-lg text-muted">
          Turn natural-language questions into quantitative what-if analysis.
        </p>
      </motion.div>

      {/* Main Composition */}
      <div className="grid h-[500px] grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-0">
        
        {/* Left: Input */}
        <div className="h-full py-8">
          <PromptConsole scenarioState={state} onSubmit={runSequence} />
        </div>

        {/* Center: AI + Quant Vis */}
        <div className="relative h-full overflow-hidden">
          {/* We overlap them and use opacity/clip to transition visually */}
          <div className={`absolute inset-0 transition-opacity duration-1000 ${state === 'idle' || state === 'parsing' || state === 'tool_call' ? 'opacity-100' : 'opacity-0'}`}>
            <SemanticConstellation scenarioState={state} scenarioType={type} />
          </div>
          
          <div className={`absolute inset-0 transition-opacity duration-1000 ${state === 'simulating' || state === 'result' ? 'opacity-100' : 'opacity-0'}`}>
            <QuantEnginePortal scenarioState={state} scenarioType={type} />
          </div>
        </div>

        {/* Right: Result */}
        <div className="h-full py-8">
          <RiskReadout scenarioState={state} scenarioType={type} onWhyClick={handleWhy} />
        </div>

      </div>

      {/* Stress Test Control */}
      <div className="mt-12 flex justify-center gap-4">
        {state === 'result' && (
          <button 
            onClick={handleReset}
            className="flex items-center gap-2 mono text-[10px] tracking-widest text-muted hover:text-foreground transition-colors"
          >
            <RotateCcw className="size-3" />
            RESET
          </button>
        )}
        <button
          onClick={() => {
            onTriggerStress()
            runSequence('What if the market enters a stress regime?', 'regime')
          }}
          className="flex items-center gap-2 mono text-[10px] tracking-widest text-danger hover:bg-danger/10 px-3 py-1 border border-transparent hover:border-danger/30 transition-colors"
        >
          <Play className="size-3" />
          [ STRESS TEST ]
        </button>
      </div>

    </section>
  )
})
