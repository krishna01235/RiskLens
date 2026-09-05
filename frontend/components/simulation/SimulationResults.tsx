/**
 * SimulationResults.tsx — Simulation results display, migrated to tokens.
 *
 * Changes: bg-green-900/20 / bg-red-900/20 → brand-safe-m / brand-breach-m,
 * font-mono numerals, Card wrapper, brand border colours.
 */

"use client";

import Card from "@/components/ui/Card";
import EVTComparisonRow from "./EVTComparisonRow";

interface SimResult {
  prob_profit: number;
  prob_loss: number;
  expected_pnl: number;
  pnl_p5: number;
  pnl_p50: number;
  pnl_p95: number;
  num_paths: number;
  evt?: {
    is_valid: boolean;
    message: string;
    var_95: number | null;
    cvar_95: number | null;
  } | null;
}

function fmt(n: number) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  })}`;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function SimulationResults({ result }: { result: SimResult }) {
  const range = result.pnl_p95 - result.pnl_p5;
  const barWidth = (v: number) => {
    if (range === 0) return 50;
    return Math.max(5, Math.min(95, ((v - result.pnl_p5) / range) * 100));
  };

  return (
    <div className="mt-6 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-brand-primary">Simulation Results</h2>
        <p className="text-xs text-brand-tertiary">{result.num_paths.toLocaleString()} paths</p>
      </div>

      {/* Probability row */}
      <div className="grid grid-cols-2 gap-4">
        <Card
          className="text-center border-brand-safe/30 bg-brand-safe-m"
          padding="md"
        >
          <p className="text-2xl font-mono tabular-nums font-semibold text-brand-safe">
            {pct(result.prob_profit)}
          </p>
          <p className="text-xs text-brand-secondary mt-1">Probability of Profit</p>
        </Card>
        <Card
          className="text-center border-brand-breach/30 bg-brand-breach-m"
          padding="md"
        >
          <p className="text-2xl font-mono tabular-nums font-semibold text-brand-breach">
            {pct(result.prob_loss)}
          </p>
          <p className="text-xs text-brand-secondary mt-1">Probability of Loss</p>
        </Card>
      </div>

      {/* Expected P&L */}
      <Card
        padding="md"
        className={result.expected_pnl >= 0 ? "border-brand-accent/30" : "border-brand-high/30"}
      >
        <p className="text-xs text-brand-tertiary mb-1">Expected P&amp;L</p>
        <p className={`text-3xl font-mono tabular-nums font-semibold ${
          result.expected_pnl >= 0 ? "text-brand-accent" : "text-brand-high"
        }`}>
          {fmt(result.expected_pnl)}
        </p>
      </Card>

      {/* Percentile range bar */}
      <Card padding="md" className="space-y-3">
        <p className="text-xs text-brand-secondary font-medium">
          P&amp;L Range (5th – 95th Percentile)
        </p>
        <div
          className="relative h-7 bg-brand-bg rounded-md overflow-hidden"
          role="img"
          aria-label={`P&L range from ${fmt(result.pnl_p5)} to ${fmt(result.pnl_p95)}`}
        >
          <div
            className="absolute top-0 h-full rounded-md"
            style={{
              left: "5%",
              width: "90%",
              background:
                "linear-gradient(to right, var(--color-high) 0%, var(--color-accent) 100%)",
              opacity: 0.4,
            }}
          />
          <div
            className="absolute top-0 h-full w-px bg-brand-primary/80"
            aria-hidden="true"
            style={{ left: `${barWidth(result.pnl_p50)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs font-mono tabular-nums text-brand-tertiary" aria-hidden="true">
          <span className="text-brand-high">P5: {fmt(result.pnl_p5)}</span>
          <span className="text-brand-primary">P50: {fmt(result.pnl_p50)}</span>
          <span className="text-brand-accent">P95: {fmt(result.pnl_p95)}</span>
        </div>
      </Card>

      <EVTComparisonRow evt={result.evt} mcVarPnl={result.pnl_p5} />
    </div>
  );
}
