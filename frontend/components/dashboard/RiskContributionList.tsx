/**
 * RiskContributionList.tsx — Risk contribution breakdown, migrated to tokens.
 *
 * Changes:
 * - bg-white/5 → bg-brand-elevated / border-white/10 → border-brand-border
 * - bg-blue-500/50 → bg-brand-accent/40 (allocation bar)
 * - bg-red-500/80 → bg-brand-breach/80, bg-purple-500/80 → bg-brand-accent/60
 * - Dense 36-40 px row height per §4.5 table spec
 * - Mono font for all numeric values
 */

import { RiskContribution } from "@/hooks/useRiskSocket";
import Card from "@/components/ui/Card";

export function RiskContributionList({
  contributions,
}: {
  contributions?: RiskContribution[];
}) {
  if (!contributions || contributions.length <= 1) {
    return null;
  }

  const sorted = [...contributions].sort((a, b) => b.rc_pct - a.rc_pct);

  return (
    <Card>
      <h3 className="text-sm font-semibold text-brand-primary mb-0.5">
        Risk Contribution Breakdown
      </h3>
      <p className="text-xs text-brand-tertiary mb-4">
        Capital allocation vs. marginal contribution to portfolio volatility.
      </p>

      <div className="space-y-3">
        {sorted.map((item) => {
          const allocationPct = (item.weight * 100).toFixed(1);
          const riskPct = (item.rc_pct * 100).toFixed(1);
          const isOutsized = item.rc_pct > item.weight * 1.2;

          return (
            <div key={item.symbol} className="grid grid-cols-12 gap-3 items-center min-h-[36px]">
              <div className="col-span-2 font-mono text-xs font-medium text-brand-primary truncate">
                {item.symbol}
              </div>

              <div className="col-span-10 space-y-1.5">
                {/* Allocation bar */}
                <div className="flex items-center gap-2" aria-label={`${item.symbol} allocation ${allocationPct}%`}>
                  <div className="w-20 text-xs text-brand-tertiary shrink-0">Alloc.</div>
                  <div className="flex-1 h-1.5 bg-brand-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-accent/40 rounded-full"
                      style={{ width: `${Math.min(item.weight * 100, 100)}%` }}
                    />
                  </div>
                  <div className="w-10 text-xs font-mono tabular-nums text-brand-secondary text-right shrink-0">
                    {allocationPct}%
                  </div>
                </div>

                {/* Risk bar */}
                <div className="flex items-center gap-2" aria-label={`${item.symbol} risk contribution ${riskPct}%`}>
                  <div className="w-20 text-xs text-brand-tertiary shrink-0">Risk</div>
                  <div className="flex-1 h-1.5 bg-brand-bg rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isOutsized ? "bg-brand-breach/80" : "bg-brand-accent/60"}`}
                      style={{ width: `${Math.min(item.rc_pct * 100, 100)}%` }}
                    />
                  </div>
                  <div
                    className={`w-10 text-xs font-mono tabular-nums text-right shrink-0 ${
                      isOutsized ? "text-brand-breach" : "text-brand-secondary"
                    }`}
                  >
                    {riskPct}%
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
