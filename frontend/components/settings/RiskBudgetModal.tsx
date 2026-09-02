"use client";

import { useState, useEffect } from "react";

export interface RiskBudget {
  max_cvar: number;
  watch_threshold: number;
  high_threshold: number;
  breach_threshold: number;
}

interface Props {
  portfolioId: string;
  initialBudget: RiskBudget | null;
  onClose: () => void;
  onSave: (budget: RiskBudget) => void;
}

export default function RiskBudgetModal({ portfolioId, initialBudget, onClose, onSave }: Props) {
  const [maxCvar, setMaxCvar] = useState<string>("5000");
  const [watch, setWatch] = useState<string>("60");
  const [high, setHigh] = useState<string>("80");
  const [breach, setBreach] = useState<string>("100");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialBudget) {
      setMaxCvar(initialBudget.max_cvar.toString());
      setWatch((initialBudget.watch_threshold * 100).toFixed(0));
      setHigh((initialBudget.high_threshold * 100).toFixed(0));
      setBreach((initialBudget.breach_threshold * 100).toFixed(0));
    }
  }, [initialBudget]);

  const handleSave = async () => {
    setError(null);
    const m = parseFloat(maxCvar);
    const w = parseFloat(watch) / 100;
    const h = parseFloat(high) / 100;
    const b = parseFloat(breach) / 100;

    if (isNaN(m) || m <= 0) {
      setError("Max CVaR must be a positive number.");
      return;
    }
    if (!(w < h && h <= b)) {
      setError("Thresholds must satisfy Watch < High <= Breach.");
      return;
    }

    setIsSaving(true);
    try {
      const resp = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/portfolios/${portfolioId}/risk-budget`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({
            max_cvar: m,
            watch_threshold: w,
            high_threshold: h,
            breach_threshold: b,
          }),
        }
      );

      if (!resp.ok) {
        throw new Error(await resp.text());
      }

      const updated = await resp.json();
      onSave(updated);
    } catch (err: any) {
      setError(err.message || "Failed to save budget");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#1c2128] border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <h3 className="text-xl font-semibold text-white mb-4">Risk Budget</h3>
        
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Max CVaR ($)</label>
            <input
              type="number"
              value={maxCvar}
              onChange={(e) => setMaxCvar(e.target.value)}
              className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g. 5000"
            />
            <p className="text-xs text-gray-500 mt-1">Maximum acceptable 95% CVaR limit.</p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Watch (%)</label>
              <input
                type="number"
                value={watch}
                onChange={(e) => setWatch(e.target.value)}
                className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-yellow-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">High (%)</label>
              <input
                type="number"
                value={high}
                onChange={(e) => setHigh(e.target.value)}
                className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Breach (%)</label>
              <input
                type="number"
                value={breach}
                onChange={(e) => setBreach(e.target.value)}
                className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-red-500"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Budget"}
          </button>
        </div>
      </div>
    </div>
  );
}
