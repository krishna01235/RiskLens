import { RiskContribution } from "@/hooks/useRiskSocket";

export function RiskContributionList({
  contributions,
}: {
  contributions?: RiskContribution[];
}) {
  if (!contributions || contributions.length <= 1) {
    return null;
  }

  // Sort by risk contribution percentage descending
  const sorted = [...contributions].sort((a, b) => b.rc_pct - a.rc_pct);

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-6 mt-6">
      <h3 className="text-lg font-medium text-white mb-1">Risk Contribution Breakdown</h3>
      <p className="text-sm text-gray-400 mb-6">
        Compare actual capital allocation versus marginal contribution to portfolio volatility.
      </p>

      <div className="space-y-4">
        {sorted.map((item) => {
          const allocationPct = (item.weight * 100).toFixed(1);
          const riskPct = (item.rc_pct * 100).toFixed(1);
          
          // Determine if risk outsized allocation by more than 20% relative
          const isOutsized = item.rc_pct > item.weight * 1.2;
          
          return (
            <div key={item.symbol} className="grid grid-cols-12 gap-4 items-center">
              <div className="col-span-2 font-mono font-medium text-white">
                {item.symbol}
              </div>
              
              <div className="col-span-10 space-y-2">
                {/* Allocation Bar */}
                <div className="flex items-center gap-3">
                  <div className="w-24 text-xs text-gray-400 shrink-0">Allocation</div>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500/50 rounded-full"
                      style={{ width: `${Math.min(item.weight * 100, 100)}%` }}
                    />
                  </div>
                  <div className="w-12 text-xs font-mono text-gray-400 text-right shrink-0">
                    {allocationPct}%
                  </div>
                </div>

                {/* Risk Bar */}
                <div className="flex items-center gap-3">
                  <div className="w-24 text-xs text-gray-400 shrink-0">Risk</div>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full ${isOutsized ? "bg-red-500/80" : "bg-purple-500/80"}`}
                      style={{ width: `${Math.min(item.rc_pct * 100, 100)}%` }}
                    />
                  </div>
                  <div className={`w-12 text-xs font-mono text-right shrink-0 ${isOutsized ? "text-red-400" : "text-gray-400"}`}>
                    {riskPct}%
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
