"use client";

import { TrendingDown, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

export interface ScenarioResult {
  shocks: Record<string, number>;
  var_95: number;
  cvar_95: number;
  var_95_baseline: number;
  cvar_95_baseline: number;
  expected_loss: number;
  portfolio_value: number;
  insufficient_data: boolean;
}

export function ScenarioResultCard({ result }: { result: ScenarioResult }) {
  const varChange = result.var_95 - result.var_95_baseline;
  const cvarChange = result.cvar_95 - result.cvar_95_baseline;
  const varPct = result.var_95_baseline !== 0
    ? (varChange / result.var_95_baseline) * 100
    : 0;

  const shockEntries = Object.entries(result.shocks);
  const isLoss = result.expected_loss >= 0;

  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 mt-2 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Scenario Result
        </h4>
        {result.insufficient_data && (
          <span className="flex items-center gap-1 text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">
            <AlertCircle className="w-3 h-3" />
            Approximate (limited data)
          </span>
        )}
      </div>

      {/* Shocks applied */}
      <div className="flex flex-wrap gap-2">
        {shockEntries.map(([sym, shock]) => (
          <span
            key={sym}
            className={`text-xs font-mono px-2 py-0.5 rounded-md border ${
              shock < 0
                ? "text-red-400 bg-red-500/10 border-red-500/30"
                : "text-green-400 bg-green-500/10 border-green-500/30"
            }`}
          >
            {sym} {shock > 0 ? "+" : ""}
            {(shock * 100).toFixed(0)}%
          </span>
        ))}
      </div>

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* VaR */}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">
            95% VaR (1-day)
          </p>
          <p className="text-lg font-mono text-gray-100">
            {(result.var_95 * 100).toFixed(2)}%
          </p>
          <p
            className={`text-xs font-mono mt-0.5 ${
              varChange > 0 ? "text-red-400" : "text-green-400"
            }`}
          >
            {varChange > 0 ? "▲" : "▼"} {Math.abs(varPct).toFixed(1)}% vs baseline
          </p>
        </div>

        {/* CVaR */}
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-0.5">
            95% CVaR (Expected Shortfall)
          </p>
          <p className="text-lg font-mono text-gray-100">
            {(result.cvar_95 * 100).toFixed(2)}%
          </p>
          <p className="text-xs text-gray-500 font-mono mt-0.5">
            baseline: {(result.cvar_95_baseline * 100).toFixed(2)}%
          </p>
        </div>

        {/* Expected P&L */}
        <div className="col-span-2 border-t border-gray-700/50 pt-3">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            Expected P&L Impact
          </p>
          <div className="flex items-center gap-2">
            {isLoss ? (
              <TrendingDown className="w-5 h-5 text-red-400" />
            ) : (
              <TrendingUp className="w-5 h-5 text-green-400" />
            )}
            <p
              className={`text-xl font-mono font-bold ${
                isLoss ? "text-red-400" : "text-green-400"
              }`}
            >
              {isLoss ? "-" : "+"}$
              {Math.abs(result.expected_loss).toLocaleString("en-US", {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              })}
            </p>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            First-order approximation on ${result.portfolio_value.toLocaleString()} portfolio
          </p>
        </div>
      </div>
    </div>
  );
}
