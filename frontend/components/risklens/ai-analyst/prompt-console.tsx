'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import type { RiskScenarioState, RiskScenarioType } from './types'

const SUGGESTIONS: { label: string; type: RiskScenarioType }[] = [
  { label: 'What happens if volatility rises 20%?', type: 'volatility' },
  { label: 'How exposed is the portfolio to a tech selloff?', type: 'correlation' },
  { label: 'What if the market enters a stress regime?', type: 'regime' },
  { label: 'Why did risk increase?', type: 'why' },
]

const STATUS_STAGES = [
  'PARSING INTENT...',
  'BUILDING RISK QUERY...',
  'CALLING QUANT ENGINE...',
]

export default function PromptConsole({
  scenarioState,
  onSubmit,
}: {
  scenarioState: RiskScenarioState
  onSubmit: (query: string, type: RiskScenarioType) => void
}) {
  const [inputValue, setInputValue] = useState('')
  const [frozenWords, setFrozenWords] = useState<string[]>([])
  const [statusIndex, setStatusIndex] = useState(0)

  // Manage status text sequence when entering 'parsing' state
  useEffect(() => {
    if (scenarioState === 'parsing') {
      setStatusIndex(0)
      const t1 = setTimeout(() => setStatusIndex(1), 600)
      const t2 = setTimeout(() => setStatusIndex(2), 1200)
      return () => {
        clearTimeout(t1)
        clearTimeout(t2)
      }
    }
  }, [scenarioState])

  const handleSubmit = (query: string, type: RiskScenarioType) => {
    if (scenarioState !== 'idle') return
    setInputValue(query)
    setFrozenWords(query.split(' '))
    onSubmit(query, type)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      // Very naive intent parser for manual entry
      let type: RiskScenarioType = 'volatility'
      const lower = inputValue.toLowerCase()
      if (lower.includes('regime') || lower.includes('stress')) type = 'regime'
      else if (lower.includes('why')) type = 'why'
      else if (lower.includes('tech') || lower.includes('selloff') || lower.includes('correlation')) type = 'correlation'
      
      handleSubmit(inputValue, type)
    }
  }

  return (
    <div className="flex h-full flex-col justify-center gap-8 relative z-10">
      <div>
        <p className="mono mb-4 text-[10px] tracking-[.28em] text-accent">ASK RISKLENS</p>
        
        <div className="relative border border-grid bg-card/60 backdrop-blur-sm p-4 transition-colors focus-within:border-accent">
          {scenarioState === 'idle' ? (
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What happens if volatility rises 20%?"
              className="w-full bg-transparent text-lg text-foreground outline-none placeholder:text-muted"
            />
          ) : (
            <div className="flex w-full flex-wrap gap-x-1.5 text-lg text-foreground">
              {frozenWords.map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 1, y: 0, filter: 'blur(0px)', scale: 1 }}
                  animate={{ 
                    opacity: 0, 
                    y: -10 - Math.random() * 20,
                    x: Math.random() * 30,
                    filter: 'blur(4px)',
                    scale: 0.8
                  }}
                  transition={{ delay: i * 0.05, duration: 0.6, ease: 'easeOut' }}
                  className="inline-block"
                >
                  {word}
                </motion.span>
              ))}
            </div>
          )}

          {/* Submission arrow */}
          {scenarioState === 'idle' && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-muted">
              <ArrowRight className="size-4" />
            </div>
          )}
        </div>
      </div>

      <div className="h-24">
        <AnimatePresence mode="wait">
          {scenarioState === 'idle' ? (
            <motion.div
              key="suggestions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col gap-3"
            >
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSubmit(s.label, s.type)}
                  className="group flex w-fit items-center gap-2 text-left mono text-[10px] tracking-wider text-muted transition-colors hover:text-accent"
                >
                  <span className="text-grid group-hover:text-accent transition-colors">›</span>
                  <span className="border-b border-transparent group-hover:border-accent/40">{s.label}</span>
                </button>
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="status"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex h-full flex-col justify-center"
            >
              <AnimatePresence mode="wait">
                <motion.p
                  key={statusIndex}
                  initial={{ opacity: 0, filter: 'blur(4px)' }}
                  animate={{ opacity: 1, filter: 'blur(0px)' }}
                  exit={{ opacity: 0, filter: 'blur(4px)' }}
                  transition={{ duration: 0.3 }}
                  className="mono text-xs tracking-widest text-accent"
                >
                  {STATUS_STAGES[statusIndex]}
                </motion.p>
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
