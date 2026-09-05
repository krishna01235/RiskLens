/**
 * AlertBanner.tsx — Risk-state transition alert, migrated to design tokens.
 *
 * Changes:
 * - Left-accent-bar style per §4.5 ("not full-background-colored")
 * - Token colours replace raw tailwind color-500 literals
 * - BREACH persists; others auto-dismiss at 5 s
 * - Dismiss button uses accessible aria-label
 */

"use client";

import { useEffect, useState } from "react";
import { DecisionUpdate } from "@/hooks/useRiskSocket";
import { DecisionCard } from "./DecisionCard";

interface AlertMessage {
  type: "alert";
  portfolio_id: string;
  from_state: string;
  to_state: string;
  utilization: number;
  cvar: number;
  fired_at: string;
}

interface Props {
  alertMsg: AlertMessage | null;
  decisionMsg: DecisionUpdate | null;
}

type RiskState = "SAFE" | "WATCH" | "HIGH" | "BREACH";

const ACCENT_BAR: Record<string, string> = {
  SAFE:   "bg-brand-safe",
  WATCH:  "bg-brand-watch",
  HIGH:   "bg-brand-high",
  BREACH: "bg-brand-breach",
};

const LABEL_COLOR: Record<string, string> = {
  SAFE:   "text-brand-safe",
  WATCH:  "text-brand-watch",
  HIGH:   "text-brand-high",
  BREACH: "text-brand-breach",
};

const BORDER_COLOR: Record<string, string> = {
  SAFE:   "border-brand-safe/30",
  WATCH:  "border-brand-watch/30",
  HIGH:   "border-brand-high/30",
  BREACH: "border-brand-breach/30",
};

export default function AlertBanner({ alertMsg, decisionMsg }: Props) {
  const [activeAlert, setActiveAlert] = useState<AlertMessage | null>(null);

  useEffect(() => {
    if (!alertMsg) return;
    setActiveAlert(alertMsg);

    // Auto-dismiss non-BREACH alerts after 5 s per spec
    if (alertMsg.to_state !== "BREACH") {
      const timer = setTimeout(() => setActiveAlert(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [alertMsg]);

  if (!activeAlert) return null;

  const state = activeAlert.to_state as RiskState;
  const isBreach = state === "BREACH";

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`flex items-start gap-0 overflow-hidden rounded-lg border ${BORDER_COLOR[state] ?? "border-brand-border"} bg-brand-elevated mb-4`}
    >
      {/* Left accent bar — coloured by severity */}
      <div
        aria-hidden="true"
        className={`w-1 self-stretch shrink-0 ${ACCENT_BAR[state] ?? "bg-brand-accent"}`}
      />

      <div className="flex flex-1 items-start gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <h4 className={`text-xs font-semibold uppercase tracking-wide ${LABEL_COLOR[state] ?? "text-brand-primary"}`}>
            Risk State: {state}
          </h4>
          <p className="text-sm text-brand-primary mt-1">
            CVaR utilisation has reached{" "}
            <span className="font-mono tabular-nums">
              {(activeAlert.utilization * 100).toFixed(1)}%
            </span>{" "}
            (${activeAlert.cvar.toLocaleString()}).
          </p>
          <p className="text-xs text-brand-tertiary mt-1.5">
            Transitioned from {activeAlert.from_state} at{" "}
            {new Date(activeAlert.fired_at).toLocaleTimeString()}
          </p>

          {/* Decision Engine section (BREACH only) */}
          {isBreach && (
            <div className="mt-4 border-t border-brand-border pt-4">
              <h5 className="text-sm font-semibold text-brand-secondary mb-3">
                Decision Engine{" "}
                <span className="text-brand-tertiary font-normal">(advisory)</span>
              </h5>
              {!decisionMsg ? (
                <div className="flex items-center gap-2 text-sm text-brand-tertiary rounded-lg border border-brand-border bg-brand-bg p-3">
                  <svg
                    aria-hidden="true"
                    className="h-4 w-4 animate-spin text-brand-breach shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 11-8 8z" />
                  </svg>
                  Evaluating candidates via Monte Carlo…
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {decisionMsg.candidates.map((candidate, idx) => (
                    <DecisionCard key={idx} candidate={candidate} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dismiss */}
        <button
          onClick={() => setActiveAlert(null)}
          aria-label="Dismiss alert"
          className="mt-0.5 shrink-0 rounded p-1 text-brand-tertiary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M11 3L3 11M3 3l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
