export type RiskScenarioState = 'idle' | 'parsing' | 'tool_call' | 'simulating' | 'result'
export type RiskScenarioType = 'volatility' | 'correlation' | 'regime' | 'why'

export interface RiskScenario {
  query: string
  type: RiskScenarioType
}
