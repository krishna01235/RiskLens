"use client";

import { useState } from "react";

interface Props {
  onRun: (portfolioId: string, horizonDays: number, numPaths: number) => void;
  disabled: boolean;
}

const HORIZONS = [
  { label: "1 Day", value: 1 },
  { label: "7 Days", value: 7 },
  { label: "30 Days", value: 30 },
  { label: "90 Days", value: 90 },
];

const PATH_COUNTS = [
  { label: "10K paths", value: 10_000 },
  { label: "50K paths", value: 50_000 },
  { label: "100K paths", value: 100_000 },
];

export default function SimulationForm({ onRun, disabled }: Props) {
  const [portfolioId, setPortfolioId] = useState("");
  const [horizon, setHorizon] = useState(30);
  const [numPaths, setNumPaths] = useState(50_000);
  const [error, setError] = useState("");

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
    <form onSubmit={handleSubmit} className="bg-[#161b22] border border-gray-800 rounded-2xl p-6 space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Portfolio ID</label>
        <input
          id="portfolio-id-input"
          type="text"
          value={portfolioId}
          onChange={(e) => setPortfolioId(e.target.value)}
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          className="w-full bg-[#0d1117] border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={disabled}
        />
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Simulation Horizon</label>
        <div className="flex gap-2 flex-wrap">
          {HORIZONS.map((h) => (
            <button
              key={h.value}
              type="button"
              id={`horizon-${h.value}`}
              onClick={() => setHorizon(h.value)}
              disabled={disabled}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                horizon === h.value
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                  : "bg-[#0d1117] border border-gray-700 text-gray-400 hover:border-blue-500"
              }`}
            >
              {h.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Path Count</label>
        <div className="flex gap-2 flex-wrap">
          {PATH_COUNTS.map((p) => (
            <button
              key={p.value}
              type="button"
              id={`paths-${p.value}`}
              onClick={() => setNumPaths(p.value)}
              disabled={disabled}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                numPaths === p.value
                  ? "bg-cyan-600 text-white shadow-lg shadow-cyan-500/20"
                  : "bg-[#0d1117] border border-gray-700 text-gray-400 hover:border-cyan-500"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <button
        id="run-simulation-btn"
        type="submit"
        disabled={disabled}
        className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-xl font-semibold text-white hover:opacity-90 active:scale-[0.99] transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
      >
        Run Simulation
      </button>
    </form>
  );
}
