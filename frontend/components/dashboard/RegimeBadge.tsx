"use client";

import { useEffect, useState } from "react";
import { Activity, ShieldCheck, ShieldAlert } from "lucide-react";
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
      } catch (err) {
        console.error("Failed to fetch market regime:", err);
      }
    }

    fetchRegime();
    // Poll every 3 minutes
    const interval = setInterval(fetchRegime, 180000);
    return () => clearInterval(interval);
  }, []);

  if (!regime) {
    return null;
  }

  const isStressed = regime.stressed_probability > 0.5;
  const probability = isStressed 
    ? regime.stressed_probability 
    : regime.calm_probability;

  return (
    <div
      className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium shadow-sm transition-colors ${
        isStressed
          ? "border-amber-500/30 bg-amber-500/10 text-amber-500"
          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
      }`}
      title={`Updated at ${new Date(regime.updated_at * 1000).toLocaleTimeString()}`}
    >
      {isStressed ? (
        <ShieldAlert className="h-4 w-4" />
      ) : (
        <ShieldCheck className="h-4 w-4" />
      )}
      <span>Market Regime: {isStressed ? "Stressed" : "Calm"}</span>
      <span className={`rounded-full px-1.5 py-0.5 text-xs ${
        isStressed ? "bg-amber-500/20" : "bg-emerald-500/20"
      }`}>
        {(probability * 100).toFixed(1)}%
      </span>
    </div>
  );
}
