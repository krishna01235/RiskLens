"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import SimulationForm from "@/components/simulation/SimulationForm";
import SimulationProgress from "@/components/simulation/SimulationProgress";
import SimulationResults from "@/components/simulation/SimulationResults";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth-store";

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
  const [defaultPortfolioId, setDefaultPortfolioId] = useState<string>("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const token = useAuthStore.getState().accessToken;
        const res = await fetch(`${API_URL}/portfolios`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (data && data.length > 0) {
            setDefaultPortfolioId(data[0].id);
          }
        }
      } catch (err) {}
    }
    fetchPortfolio();
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const token = useAuthStore.getState().accessToken;
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
          // transient network error — keep polling
        }
      }, 2000);
    },
    [stopPolling],
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  const handleRun = async (
    portfolioId: string,
    horizonDays: number,
    numPaths: number,
  ) => {
    setStatus("pending");
    setProgress(0);
    setResult(null);
    setErrorMsg(null);

    try {
      const token = useAuthStore.getState().accessToken;
      const resp = await fetch(`${API_URL}/simulations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          portfolio_id: portfolioId,
          horizon_days: horizonDays,
          num_paths: numPaths,
        }),
      });

      if (resp.status === 429) {
        setStatus("failed");
        setErrorMsg("Rate limit exceeded: maximum 10 simulations per hour.");
        return;
      }
      if (resp.status === 409) {
        setStatus("failed");
        setErrorMsg(
          "A simulation is already running for this portfolio. Please wait.",
        );
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
    } catch {
      setStatus("failed");
      setErrorMsg("Network error. Please try again.");
    }
  };

  const isRunning = status === "pending" || status === "running";

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-brand-primary tracking-tight">
          Monte Carlo Simulation
        </h1>
        <p className="text-xs text-brand-tertiary mt-1">
          Vectorised GBM with Cholesky-correlated shocks, GARCH volatility, and antithetic variates.
        </p>
      </div>

      {/* Form */}
      {(status === "idle" || status === "complete" || status === "failed") && (
        <SimulationForm onRun={handleRun} disabled={isRunning} defaultPortfolioId={defaultPortfolioId} />
      )}

      {/* Progress */}
      {isRunning && (
        <SimulationProgress progress={progress} status={status} />
      )}

      {/* Error state */}
      {status === "failed" && errorMsg && (
        <div className="mt-6 flex items-start gap-0 overflow-hidden rounded-lg border border-brand-breach/30 bg-brand-elevated">
          <div className="w-1 self-stretch shrink-0 bg-brand-breach" />
          <div className="flex flex-col gap-2 px-4 py-3">
            <p className="text-sm font-semibold text-brand-primary">
              Simulation failed
            </p>
            <p className="text-sm text-brand-secondary">{errorMsg}</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStatus("idle")}
              className="self-start"
            >
              Try again
            </Button>
          </div>
        </div>
      )}

      {/* Results */}
      {status === "complete" && result && (
        <>
          <SimulationResults result={result} />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setStatus("idle"); setResult(null); }}
            className="mt-4"
          >
            Run another simulation
          </Button>
        </>
      )}
    </AppShell>
  );
}
