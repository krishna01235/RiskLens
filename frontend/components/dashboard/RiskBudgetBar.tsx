/**
 * RiskBudgetBar.tsx — Risk budget utilisation bar, migrated to design tokens.
 *
 * Changes:
 * - All hardcoded hex (#161b22, gray-800, etc.) replaced with brand tokens
 * - Bar fill animates with duration-normal ease-out-expo (300 ms)
 * - Configure/Edit use <Button> primitive
 */

"use client";

import Button from "@/components/ui/Button";

interface RiskBudget {
  max_cvar: number;
  watch_threshold: number;
  high_threshold: number;
  breach_threshold: number;
}

interface Props {
  budget: RiskBudget | null;
  currentCvar: number | null;
  onConfigureClick: () => void;
}

type RiskState = "SAFE" | "WATCH" | "HIGH" | "BREACH";

const STATE_BAR: Record<RiskState, string> = {
  SAFE:   "bg-brand-safe",
  WATCH:  "bg-brand-watch",
  HIGH:   "bg-brand-high",
  BREACH: "bg-brand-breach",
};

const STATE_TEXT: Record<RiskState, string> = {
  SAFE:   "text-brand-safe",
  WATCH:  "text-brand-watch",
  HIGH:   "text-brand-high",
  BREACH: "text-brand-breach",
};

const STATE_BORDER: Record<RiskState, string> = {
  SAFE:   "border-brand-safe/30",
  WATCH:  "border-brand-watch/30",
  HIGH:   "border-brand-high/30",
  BREACH: "border-brand-breach/30",
};

function getState(util: number, b: RiskBudget): RiskState {
  if (util >= b.breach_threshold) return "BREACH";
  if (util >= b.high_threshold)   return "HIGH";
  if (util >= b.watch_threshold)  return "WATCH";
  return "SAFE";
}

export default function RiskBudgetBar({ budget, currentCvar, onConfigureClick }: Props) {
  if (!budget) {
    return (
      <div className="rounded-lg border border-brand-border bg-brand-elevated p-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-brand-secondary">Risk Budget</p>
          <p className="text-xs text-brand-tertiary mt-0.5">No budget configured</p>
        </div>
        <Button
          id="configure-budget-btn"
          variant="secondary"
          size="sm"
          onClick={onConfigureClick}
        >
          Configure
        </Button>
      </div>
    );
  }

  const util = currentCvar != null && budget.max_cvar > 0
    ? currentCvar / budget.max_cvar
    : 0;
  const state = getState(util, budget);
  const pct = Math.min(util * 100, 100);

  return (
    <div className={`rounded-lg border ${STATE_BORDER[state]} bg-brand-elevated p-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-brand-secondary">Risk Budget</p>
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATE_TEXT[state]}`}
            aria-label={`Risk state: ${state}`}
          >
            {state}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-brand-tertiary tabular-nums">
            {(util * 100).toFixed(1)}% used
          </span>
          <Button
            id="edit-budget-btn"
            variant="ghost"
            size="sm"
            onClick={onConfigureClick}
            aria-label="Edit risk budget"
          >
            Edit
          </Button>
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="relative w-full h-2.5 bg-brand-bg rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Risk budget utilisation: ${pct.toFixed(1)}%`}
      >
        {/* Threshold markers */}
        <div
          className="absolute top-0 h-full w-px bg-brand-watch/60 z-10"
          aria-hidden="true"
          style={{ left: `${budget.watch_threshold * 100}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-brand-high/60 z-10"
          aria-hidden="true"
          style={{ left: `${budget.high_threshold * 100}%` }}
        />
        {/* Utilisation fill — 300 ms ease-out-expo transition per spec */}
        <div
          className={`h-full rounded-full transition-[width] duration-normal ease-out-expo ${STATE_BAR[state]}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Scale labels */}
      <div className="flex justify-between text-xs text-brand-tertiary mt-1.5 font-mono tabular-nums" aria-hidden="true">
        <span>0</span>
        <span className="text-brand-watch">{(budget.watch_threshold * 100).toFixed(0)}%</span>
        <span className="text-brand-high">{(budget.high_threshold * 100).toFixed(0)}%</span>
        <span>Max ${budget.max_cvar.toLocaleString()}</span>
      </div>
    </div>
  );
}
