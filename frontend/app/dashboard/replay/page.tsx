"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter,
  ComposedChart,
} from "recharts";
import AppShell from "@/components/layout/AppShell";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";

type RiskState = "safe" | "watch" | "high" | "breached";

interface ReplayDailyState {
  id: string;
  trading_date: string;
  var_95: number;
  actual_return: number;
  risk_state: RiskState;
}

interface BacktestResult {
  passed: boolean;
  predicted_breach_rate: number;
  actual_breach_rate: number;
  kupiec_statistic: number;
  p_value: number;
}

interface ReplayResponse {
  id: string;
  portfolio_id: string;
  period_key: string;
  status: "pending" | "in_progress" | "complete" | "failed";
  daily_states: ReplayDailyState[];
  backtest_result: BacktestResult | null;
}

interface Portfolio {
  id: string;
  name: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ReplayPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [periodKey, setPeriodKey] = useState("demo_stress_period");
  const [replayData, setReplayData] = useState<ReplayResponse | null>(null);
  const [status, setStatus] = useState<ReplayResponse["status"] | "idle">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    fetch(`${API_URL}/portfolios`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then((data: Portfolio[]) => {
        setPortfolios(data);
        if (data.length > 0) setSelectedPortfolio(data[0].id);
      })
      .catch(() => undefined);
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
          const token = localStorage.getItem("access_token");
          const resp = await fetch(`${API_URL}/replays/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!resp.ok) return;
          const data: ReplayResponse = await resp.json();
          setReplayData(data);
          if (data.status === "complete" || data.status === "failed") {
            stopPolling();
          }
          setStatus(data.status);
        } catch {
          // keep polling
        }
      }, 2000);
    },
    [stopPolling],
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  const handleRun = async () => {
    if (!selectedPortfolio) return;
    setStatus("pending");
    setErrorMsg(null);
    setReplayData(null);

    try {
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`${API_URL}/replays`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          portfolio_id: selectedPortfolio,
          period_key: periodKey,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        setStatus("failed");
        setErrorMsg(err.detail ?? "Failed to create replay.");
        return;
      }

      const data: ReplayResponse = await resp.json();
      setReplayData(data);
      startPolling(data.id);
    } catch {
      setStatus("failed");
      setErrorMsg("Network error. Please try again.");
    }
  };

  const chartData =
    replayData?.daily_states.map((s) => {
      const isBreach = -s.actual_return > s.var_95;
      return {
        date: s.trading_date,
        actual_loss: -s.actual_return,
        var_95: s.var_95,
        breach: isBreach ? -s.actual_return : null,
      };
    }) ?? [];

  const isRunning = status === "pending" || status === "in_progress";
  const isComplete = status === "complete";

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-brand-primary tracking-tight">
          Historical Replay &amp; Kupiec POF
        </h1>
        <p className="text-xs text-brand-tertiary mt-1">
          Replay stress periods and validate the VaR model via the Kupiec
          Proportion of Failures backtest.
        </p>
      </div>

      {/* Controls */}
      <Card className="mb-6">
        <div className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1">
            <label
              htmlFor="replay-portfolio"
              className="block text-xs font-medium text-brand-secondary mb-1.5"
            >
              Portfolio
            </label>
            <select
              id="replay-portfolio"
              value={selectedPortfolio}
              onChange={(e) => setSelectedPortfolio(e.target.value)}
              className="w-full h-9 rounded-md border border-brand-border bg-brand-bg px-3 text-sm text-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-accent transition-colors"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1">
            <label
              htmlFor="replay-period"
              className="block text-xs font-medium text-brand-secondary mb-1.5"
            >
              Stress Period
            </label>
            <select
              id="replay-period"
              value={periodKey}
              onChange={(e) => setPeriodKey(e.target.value)}
              className="w-full h-9 rounded-md border border-brand-border bg-brand-bg px-3 text-sm text-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-accent transition-colors"
            >
              <option value="demo_stress_period">
                Covid-19 Crash (Feb – May 2020)
              </option>
            </select>
          </div>

          <Button
            id="run-replay-btn"
            variant="primary"
            loading={isRunning}
            disabled={isRunning || !selectedPortfolio}
            onClick={handleRun}
          >
            {isRunning ? "Running…" : "Run Replay"}
          </Button>
        </div>
      </Card>

      {/* Idle / empty state */}
      {status === "idle" && (
        <div className="rounded-lg border border-brand-border bg-brand-elevated p-10 text-center">
          <svg
            width="36"
            height="36"
            viewBox="0 0 36 36"
            fill="none"
            className="mx-auto mb-4 text-brand-tertiary"
            aria-hidden="true"
          >
            <path
              d="M6 18a12 12 0 1012-12H12"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <path
              d="M12 10L8 14l4 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="text-sm font-medium text-brand-secondary">
            No replay run yet
          </p>
          <p className="mt-1 text-xs text-brand-tertiary">
            Select a portfolio and stress period above, then click Run Replay.
          </p>
        </div>
      )}

      {/* Error */}
      {status === "failed" && errorMsg && (
        <div className="flex items-start gap-0 overflow-hidden rounded-lg border border-brand-breach/30 bg-brand-elevated mb-6">
          <div className="w-1 self-stretch shrink-0 bg-brand-breach" />
          <div className="px-4 py-3">
            <p className="text-sm font-semibold text-brand-primary">Replay failed</p>
            <p className="text-sm text-brand-secondary mt-1">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Running indicator */}
      {isRunning && (
        <div className="flex items-center gap-3 rounded-lg border border-brand-border bg-brand-elevated px-4 py-3 mb-6">
          <svg aria-label="Running" className="h-4 w-4 animate-spin text-brand-accent shrink-0" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 11-8 8z" />
          </svg>
          <p className="text-sm text-brand-secondary">Replaying historical data…</p>
        </div>
      )}

      {/* Chart + stats */}
      {replayData && (isComplete || status === "in_progress") && (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
            <h2 className="text-sm font-semibold text-brand-primary">
              Daily VaR vs Actual Loss
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-xs text-brand-tertiary hidden sm:inline">
                Missing symbols excluded from replay.
              </span>
              {replayData.backtest_result && (
                <span
                  className={`text-xs font-semibold px-3 py-1 rounded-full border ${
                    replayData.backtest_result.passed
                      ? "bg-brand-safe-m border-brand-safe/40 text-brand-safe"
                      : "bg-brand-breach-m border-brand-breach/40 text-brand-breach"
                  }`}
                  aria-label={`Kupiec POF: ${replayData.backtest_result.passed ? "PASS" : "FAIL"}`}
                >
                  Kupiec POF:{" "}
                  {replayData.backtest_result.passed ? "PASS" : "FAIL"}
                </span>
              )}
            </div>
          </div>

          <div className="h-72 w-full mb-6">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--color-border)"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  stroke="var(--color-text-tertiary)"
                  fontSize={11}
                  tickMargin={8}
                  tickFormatter={(val) =>
                    new Date(val).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  }
                />
                <YAxis
                  stroke="var(--color-text-tertiary)"
                  fontSize={11}
                  tickFormatter={(val) => `${(val * 100).toFixed(1)}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-bg-elevated)",
                    borderColor: "var(--color-border)",
                    borderRadius: "8px",
                    color: "var(--color-text-primary)",
                    fontSize: "12px",
                  }}
                  labelFormatter={(val) => new Date(val).toLocaleDateString()}
                  formatter={(val: number, name: string) => [
                    `${(val * 100).toFixed(2)}%`,
                    name === "var_95"
                      ? "95% VaR"
                      : name === "actual_loss"
                        ? "Actual Loss"
                        : "Breach",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="var_95"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={false}
                  name="var_95"
                />
                <Line
                  type="monotone"
                  dataKey="actual_loss"
                  stroke="var(--color-text-secondary)"
                  strokeWidth={1}
                  dot={false}
                  name="actual_loss"
                />
                <Scatter
                  dataKey="breach"
                  fill="var(--color-breach)"
                  name="breach"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Backtest stats */}
          {replayData.backtest_result && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                {
                  label: "Target Breach Rate",
                  value: `${(replayData.backtest_result.predicted_breach_rate * 100).toFixed(1)}%`,
                },
                {
                  label: "Actual Breach Rate",
                  value: `${(replayData.backtest_result.actual_breach_rate * 100).toFixed(2)}%`,
                },
                {
                  label: "Kupiec LR Statistic",
                  value: replayData.backtest_result.kupiec_statistic.toFixed(3),
                },
                {
                  label: "p-value",
                  value: replayData.backtest_result.p_value.toFixed(4),
                },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-md border border-brand-border bg-brand-bg p-3"
                >
                  <p className="text-xs text-brand-tertiary uppercase tracking-wide mb-1">
                    {stat.label}
                  </p>
                  <p className="text-base font-mono tabular-nums font-semibold text-brand-primary">
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </AppShell>
  );
}
