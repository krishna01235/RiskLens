/**
 * DecisionCard.tsx — Decision engine candidate card, migrated to tokens.
 */

"use client";

import { DecisionCandidate } from "@/hooks/useRiskSocket";
import Card from "@/components/ui/Card";

export function DecisionCard({ candidate }: { candidate: DecisionCandidate }) {
  const isBest = candidate.score === 100;

  return (
    <Card
      className={`flex flex-col gap-2 transition-colors ${
        isBest
          ? "border-brand-safe/40 bg-brand-safe-m"
          : "hover:border-brand-border"
      }`}
      padding="md"
    >
      <div className="flex justify-between items-start gap-2">
        <h4 className="text-sm font-semibold text-brand-primary leading-snug">
          {candidate.label}
        </h4>
        {isBest && (
          <span className="flex items-center gap-1 text-xs font-semibold text-brand-safe px-1.5 py-0.5 rounded bg-brand-safe/15 shrink-0">
            {/* Check icon */}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M2 5.5L4 7.5L8 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Best
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-1">
        <div>
          <p className="text-xs text-brand-tertiary uppercase tracking-wide">E[Return]</p>
          <p className={`text-base font-mono tabular-nums font-medium ${
            candidate.expected_return >= 0 ? "text-brand-safe" : "text-brand-breach"
          }`}>
            {candidate.expected_return > 0 ? "+" : ""}
            {(candidate.expected_return * 100).toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-brand-tertiary uppercase tracking-wide">CVaR 95%</p>
          <p className="text-base font-mono tabular-nums font-medium text-brand-primary">
            {(candidate.cvar * 100).toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-brand-tertiary uppercase tracking-wide">P(Loss)</p>
          <p className="text-base font-mono tabular-nums font-medium text-brand-primary">
            {(candidate.p_loss * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-brand-tertiary uppercase tracking-wide">Score</p>
          <p className="text-base font-mono tabular-nums font-medium text-brand-primary">
            {candidate.score.toFixed(0)}/100
          </p>
        </div>
      </div>

      {candidate.is_fallback && (
        <div className="mt-1 flex items-start gap-2 text-xs text-brand-watch bg-brand-watch-m p-2 rounded">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="shrink-0 mt-0.5" aria-hidden="true">
            <path d="M6 1.5L10.5 10H1.5L6 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
            <path d="M6 5v2.5M6 8.5h.01" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
          <p>Timed out — score uses deterministic approximation, not full Monte Carlo.</p>
        </div>
      )}
    </Card>
  );
}
