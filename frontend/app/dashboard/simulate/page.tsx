"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import SimulationForm from "@/components/simulation/SimulationForm";
import SimulationProgress from "@/components/simulation/SimulationProgress";
import SimulationResults from "@/components/simulation/SimulationResults";

type SimStatus = "idle" | "pending" | "running" | "complete" | "failed";

interface SimResult {
  prob_profit: number;
  prob_loss: number;
  expected_pnl: number;
  pnl_p5: number;
  pnl_p50: number;
  pnl_p95: number;
  num_paths: number;
}

interface SimulationResponse {
  id: string;
  status: SimStatus;
  results: SimResult | null;
  error_message: string | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function SimulatePage() {
  const [status, setStatus] = useState<SimStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<SimResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [simId, setSimId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Poll GET /simulations/{id} every 2s until terminal state
  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const token = localStorage.getItem("access_token");
          const resp = await fetch(`${API_URL}/simulations/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!resp.ok) return;
          const data: SimulationResponse = await resp.json();

          if (data.status === "complete") {
            stopPolling();
            setStatus("complete");
            setProgress(1);
            setResult(data.results);
          } else if (data.status === "failed") {
            stopPolling();
            setStatus("failed");
            setErrorMsg(data.error_message ?? "Unknown error");
          } else if (data.status === "running") {
            setStatus("running");
          }
        } catch {
          // transient network error -- keep polling
        }
      }, 2000);
    },
    [stopPolling]
  );

  // WS progress listener
  useEffect(() => {
    if (!simId || status === "complete" || status === "failed") return;
    // Progress updates via WS are handled in useRiskSocket;
    // for the simulation we additionally listen here if a WS ticket is available.
    // For MVP: polling (startPolling) is the primary mechanism.
  }, [simId, status]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const handleRun = async (portfolioId: string, horizonDays: number, numPaths: number) => {
    setStatus("pending");
    setProgress(0);
    setResult(null);
    setErrorMsg(null);

    try {
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`${API_URL}/simulations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ portfolio_id: portfolioId, horizon_days: horizonDays, num_paths: numPaths }),
      });

      if (resp.status === 429) {
        setStatus("failed");
        setErrorMsg("Rate limit exceeded: maximum 10 simulations per hour.");
        return;
      }
      if (resp.status === 409) {
        setStatus("failed");
        setErrorMsg("A simulation is already running for this portfolio. Please wait.");
        return;
      }
      if (!resp.ok) {
        const err = await resp.json();
        setStatus("failed");
        setErrorMsg(err.detail ?? "Failed to create simulation.");
        return;
      }

      const data: SimulationResponse = await resp.json();
      setSimId(data.id);
      setStatus("pending");
      startPolling(data.id);
    } catch (e) {
      setStatus("failed");
      setErrorMsg("Network error. Please try again.");
    }
  };

  return (
    <main className="min-h-screen bg-[#0d1117] text-white px-6 py-10 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
        Monte Carlo Simulation
      </h1>
      <p className="text-gray-400 mb-8 text-sm">
        Run a vectorized GBM simulation with Cholesky-correlated shocks, GARCH volatility, and antithetic variates.
      </p>

      {(status === "idle" || status === "complete" || status === "failed") && (
        <SimulationForm onRun={handleRun} disabled={status === "pending" || status === "running"} />
      )}

      {(status === "pending" || status === "running") && (
        <SimulationProgress progress={progress} status={status} />
      )}

      {status === "failed" && errorMsg && (
        <div className="mt-6 p-4 bg-red-900/40 border border-red-500/50 rounded-xl text-red-300">
          <p className="font-semibold mb-1">Simulation failed</p>
          <p className="text-sm">{errorMsg}</p>
          <button
            onClick={() => setStatus("idle")}
            className="mt-3 text-xs text-red-400 underline hover:text-red-300"
          >
            Try again
          </button>
        </div>
      )}

      {status === "complete" && result && (
        <>
          <SimulationResults result={result} />
          <button
            onClick={() => { setStatus("idle"); setResult(null); }}
            className="mt-6 text-sm text-gray-400 underline hover:text-gray-300"
          >
            Run another simulation
          </button>
        </>
      )}
    </main>
  );
}
