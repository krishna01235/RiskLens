/**
 * RegimeBadge.tsx — Market regime indicator, migrated to design tokens.
 *
 * Text label always accompanies colour for accessibility.
 */

"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface MarketRegime {
  calm_probability: number;
  stressed_probability: number;
  updated_at: number;
}

export function RegimeBadge() {
  const [regime, setRegime] = useState<MarketRegime | null>(null);

  useEffect(() => {
    async function fetchRegime() {
      try {
        const data = await apiClient.get<MarketRegime>("/market/regime");
        setRegime(data);
      } catch {
        // Silently ignore — badge just won't show
      }
    }

    fetchRegime();
    const interval = setInterval(fetchRegime, 180_000); // every 3 min
    return () => clearInterval(interval);
  }, []);

  if (!regime) return null;

  const isStressed = regime.stressed_probability > 0.5;
  const probability = isStressed
    ? regime.stressed_probability
    : regime.calm_probability;

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
        isStressed
          ? "border-brand-watch/30 bg-brand-watch-m text-brand-watch"
          : "border-brand-safe/30 bg-brand-safe-m text-brand-safe"
      }`}
      title={`Updated ${new Date(regime.updated_at * 1000).toLocaleTimeString()}`}
      aria-label={`Market regime: ${isStressed ? "Stressed" : "Calm"} at ${(probability * 100).toFixed(1)}% confidence`}
    >
      {/* Icon */}
      {isStressed ? (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M6 1.5L10.5 10H1.5L6 1.5Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M6 5v2M6 8.5h.01" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      ) : (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <path d="M2 6h1.5M6 2v1.5M10 6H8.5M6 10V8.5M3.5 3.5l1 1M8.5 3.5l-1 1M6 4.5a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
      )}
      <span>{isStressed ? "Stressed" : "Calm"}</span>
      <span className="font-mono tabular-nums opacity-80">
        {(probability * 100).toFixed(1)}%
      </span>
    </div>
  );
}
