"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";

interface EVTResult {
  is_valid: boolean;
  message: string;
  var_95: number | null;
  cvar_95: number | null;
}

interface Props {
  evt: EVTResult | null | undefined;
  mcVarPnl: number;
}

function pct(n: number) {
  return `${(n * 100).toFixed(2)}%`;
}

function fmt(n: number) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}`;
}

export default function EVTComparisonRow({ evt, mcVarPnl }: Props) {
  if (!evt) return null;

  return (
    <div className="mt-4 bg-[#161b22] border border-gray-800 rounded-xl p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center">
        <AlertTriangle className="w-4 h-4 mr-2 text-orange-400" />
        Tail Risk Comparison (95% Confidence)
      </h3>

      {!evt.is_valid ? (
        <div className="flex items-start space-x-2 text-sm text-gray-400 bg-gray-900/50 p-3 rounded-lg border border-gray-800">
          <AlertCircle className="w-5 h-5 text-gray-500 shrink-0" />
          <p>{evt.message}</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
            <p className="text-xs text-gray-400">Monte Carlo (Gaussian/GARCH)</p>
            <p className="text-lg font-mono font-medium text-orange-300 mt-1">
              {fmt(mcVarPnl)}
            </p>
            <p className="text-[10px] text-gray-500 mt-1">5th Percentile P&L</p>
          </div>
          
          <div className="bg-orange-900/10 rounded-lg p-3 border border-orange-500/20">
            <p className="text-xs text-orange-400/80">Extreme Value Theory (POT)</p>
            <p className="text-lg font-mono font-medium text-orange-400 mt-1">
              -{pct(evt.cvar_95 || 0)}
            </p>
            <p className="text-[10px] text-orange-500/60 mt-1">Expected Shortfall (CVaR)</p>
          </div>
        </div>
      )}
    </div>
  );
}
