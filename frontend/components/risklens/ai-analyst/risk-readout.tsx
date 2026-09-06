'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { Play } from 'lucide-react'
import type { RiskScenarioState, RiskScenarioType } from './types'

export default function RiskReadout({
  scenarioState,
  scenarioType,
  onWhyClick,
}: {
  scenarioState: RiskScenarioState
  scenarioType: RiskScenarioType
  onWhyClick: () => void
}) {
  const isResult = scenarioState === 'result'

  const metrics = scenarioType === 'volatility' 
    ? [{ label: 'VOLATILITY', val: '+20%' }, { label: 'VaR', val: '↑ 14.7%' }, { label: 'CVaR', val: '↑ 18.3%' }, { label: 'TAIL PRESSURE', val: 'INCREASING', danger: true }]
    : scenarioType === 'regime'
    ? [{ label: 'REGIME', val: 'STRESS', danger: true }, { label: 'CORRELATION', val: '↑ 0.82' }, { label: 'VaR', val: '↑ 22.1%' }]
    : scenarioType === 'correlation'
    ? [{ label: 'SECTOR CORR', val: '↑ 0.65' }, { label: 'DIVERSIFICATION', val: '↓ 12%' }, { label: 'VaR', val: '↑ 8.4%' }]
    : [{ label: 'PRIMARY DRIVER', val: 'VOL SHOCK' }, { label: 'SECONDARY', val: 'CORR SPIKE' }]

  const explanation = scenarioType === 'volatility'
    ? "Higher conditional volatility expands the simulated loss distribution, increasing downside exposure and pushing the portfolio further into the tail."
    : scenarioType === 'regime'
    ? "The HMM has detected a transition to a stress regime. Asset correlations approach 1.0, rendering standard diversification benefits ineffective."
    : scenarioType === 'correlation'
    ? "A spike in tech sector correlations reduces portfolio diversification. Losses in a single asset now propagate more efficiently across the book."
    : "Reviewing the event timeline reveals a cascading failure: an initial price shock triggered a volatility spike, which forced a regime transition and elevated overall risk."

  return (
    <div className="flex h-full flex-col justify-center gap-8 relative z-10 pl-8">
      <div>
        <p className="mono mb-4 text-[10px] tracking-[.28em] text-accent">RISK ASSESSMENT</p>
        
        <div className="flex min-h-32 flex-col gap-4">
          <AnimatePresence>
            {isResult && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ staggerChildren: 0.1 }}
                className="grid grid-cols-2 gap-4"
              >
                {metrics.map((m, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="border-l border-grid pl-3"
                  >
                    <p className="mono text-[9px] tracking-widest text-muted">{m.label}</p>
                    <p className={`mono mt-1 text-lg ${m.danger ? 'text-danger' : 'text-foreground'}`}>{m.val}</p>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="min-h-32">
        <AnimatePresence>
          {isResult && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.5 }}
            >
              <p className="text-sm leading-6 text-muted border-l border-accent/50 pl-4 py-1">
                {explanation}
              </p>
              
              {scenarioType !== 'why' && (
                <button
                  onClick={onWhyClick}
                  className="group mt-6 inline-flex items-center gap-2 mono text-[10px] tracking-widest text-accent transition-colors hover:text-foreground"
                >
                  <Play className="size-3" />
                  WHY?
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
