/**
 * SimulationForm.tsx — Monte Carlo parameter form, migrated to tokens.
 *
 * Changes:
 * - bg-[#161b22] / bg-[#0d1117] → brand tokens
 * - Gradient run button → <Button primary>
 * - Portfolio ID field → <Input>
 * - Selected horizon/path chips styled with brand-accent
 */

"use client";

import { useState, useEffect } from "react";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

interface Props {
  onRun: (portfolioId: string, horizonDays: number, numPaths: number) => void;
  disabled: boolean;
  defaultPortfolioId?: string;
}

const HORIZONS = [
  { label: "1 Day",  value: 1 },
  { label: "7 Days", value: 7 },
  { label: "30 Days",value: 30 },
  { label: "90 Days",value: 90 },
];

const PATH_COUNTS = [
  { label: "10K",  value: 10_000 },
  { label: "50K",  value: 50_000 },
  { label: "100K", value: 100_000 },
];

export default function SimulationForm({ onRun, disabled, defaultPortfolioId = "" }: Props) {
  const [portfolioId, setPortfolioId] = useState(defaultPortfolioId);
  const [horizon, setHorizon] = useState(30);
  const [numPaths, setNumPaths] = useState(50_000);
  const [error, setError] = useState("");

  useEffect(() => {
    if (defaultPortfolioId && !portfolioId) {
      setPortfolioId(defaultPortfolioId);
    }
  }, [defaultPortfolioId, portfolioId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!portfolioId.trim()) {
      setError("Portfolio ID is required.");
      return;
    }
    setError("");
    onRun(portfolioId.trim(), horizon, numPaths);
  };

  return (
    <form onSubmit={handleSubmit}>
      <Card className="space-y-5">
        <Input
          id="portfolio-id-input"
          label="Portfolio ID"
          type="text"
          value={portfolioId}
          onChange={(e) => setPortfolioId(e.target.value)}
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          disabled={disabled}
          error={error || undefined}
        />

        {/* Horizon selector */}
        <div>
          <p className="text-sm font-medium text-brand-secondary mb-2">
            Simulation Horizon
          </p>
          <div className="flex gap-2 flex-wrap">
            {HORIZONS.map((h) => (
              <button
                key={h.value}
                type="button"
                id={`horizon-${h.value}`}
                onClick={() => setHorizon(h.value)}
                disabled={disabled}
                aria-pressed={horizon === h.value}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                  horizon === h.value
                    ? "bg-brand-accent text-white"
                    : "bg-brand-bg border border-brand-border text-brand-secondary hover:border-brand-accent hover:text-brand-primary"
                }`}
              >
                {h.label}
              </button>
            ))}
          </div>
        </div>

        {/* Path count selector */}
        <div>
          <p className="text-sm font-medium text-brand-secondary mb-2">
            Path Count
          </p>
          <div className="flex gap-2 flex-wrap">
            {PATH_COUNTS.map((p) => (
              <button
                key={p.value}
                type="button"
                id={`paths-${p.value}`}
                onClick={() => setNumPaths(p.value)}
                disabled={disabled}
                aria-pressed={numPaths === p.value}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] ${
                  numPaths === p.value
                    ? "bg-brand-accent text-white"
                    : "bg-brand-bg border border-brand-border text-brand-secondary hover:border-brand-accent hover:text-brand-primary"
                }`}
              >
                {p.label} paths
              </button>
            ))}
          </div>
        </div>

        <Button
          id="run-simulation-btn"
          type="submit"
          variant="primary"
          loading={disabled}
          className="w-full"
        >
          Run Simulation
        </Button>
      </Card>
    </form>
  );
}
