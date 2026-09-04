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
  ComposedChart
} from "recharts";

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
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>("");
  const [periodKey, setPeriodKey] = useState<string>("demo_stress_period");
  const [replayId, setReplayId] = useState<string | null>(null);
  const [replayData, setReplayData] = useState<ReplayResponse | null>(null);
  const [status, setStatus] = useState<ReplayResponse["status"] | "idle">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Fetch portfolios
    const token = localStorage.getItem("access_token");
    if (!token) return;
    fetch(`${API_URL}/portfolios`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => res.json())
      .then((data) => {
        setPortfolios(data);
        if (data.length > 0) setSelectedPortfolio(data[0].id);
      })
      .catch(console.error);
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
            setStatus(data.status);
          } else {
            setStatus(data.status);
          }
        } catch {
          // keep polling
        }
      }, 2000);
    },
    [stopPolling]
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
        body: JSON.stringify({ portfolio_id: selectedPortfolio, period_key: periodKey }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        setStatus("failed");
        setErrorMsg(err.detail ?? "Failed to create replay.");
        return;
      }

      const data: ReplayResponse = await resp.json();
      setReplayId(data.id);
      setReplayData(data);
      startPolling(data.id);
    } catch (e) {
      setStatus("failed");
      setErrorMsg("Network error. Please try again.");
    }
  };

  const chartData = replayData?.daily_states.map(s => {
    const isBreach = (-s.actual_return > s.var_95);
    return {
      date: s.trading_date,
      actual_loss: -s.actual_return,
      var_95: s.var_95,
      breach: isBreach ? -s.actual_return : null
    };
  }) || [];

  return (
    <main className="min-h-screen bg-[#0d1117] text-white px-6 py-10 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
        Historical Replay & Kupiec POF
      </h1>
      <p className="text-gray-400 mb-8 text-sm">
        Replay historical stress periods and validate the VaR model using the Kupiec Proportion of Failures backtest.
      </p>

      {/* Form Section */}
      <div className="bg-[#161b22] border border-gray-800 rounded-xl p-6 mb-8 shadow-lg">
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-400 mb-2">Portfolio</label>
            <select
              value={selectedPortfolio}
              onChange={(e) => setSelectedPortfolio(e.target.value)}
              className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 transition-colors"
            >
              {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-400 mb-2">Stress Period</label>
            <select
              value={periodKey}
              onChange={(e) => setPeriodKey(e.target.value)}
              className="w-full bg-[#0d1117] border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-purple-500 transition-colors"
            >
              <option value="demo_stress_period">Covid-19 Crash (Feb - May 2020)</option>
            </select>
          </div>
          <button
            onClick={handleRun}
            disabled={status === "pending" || status === "in_progress"}
            className="h-10 px-6 rounded-lg font-medium text-sm transition-all duration-200 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white shadow-[0_0_15px_rgba(147,51,234,0.3)] hover:shadow-[0_0_25px_rgba(147,51,234,0.5)]"
          >
            {status === "pending" || status === "in_progress" ? "Running..." : "Run Replay"}
          </button>
        </div>
      </div>

      {status === "failed" && (
        <div className="p-4 bg-red-900/40 border border-red-500/50 rounded-xl text-red-300 mb-8">
          <p className="font-semibold mb-1">Replay failed</p>
          <p className="text-sm">{errorMsg}</p>
        </div>
      )}

      {/* Chart Section */}
      {replayData && (status === "complete" || status === "in_progress") && (
        <div className="bg-[#161b22] border border-gray-800 rounded-xl p-6 shadow-lg mb-8">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-gray-100">Daily VaR vs Actual Loss</h2>
            <div className="flex items-center gap-4">
              <span className="text-xs text-gray-400 max-w-xs text-right hidden md:inline-block">
                Note: The dataset covers the demo portfolios. Missing symbols are excluded from the replay.
              </span>
              {replayData.backtest_result && (
              <div className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${
                replayData.backtest_result.passed 
                  ? 'bg-green-900/30 border-green-500/50 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)]' 
                  : 'bg-red-900/30 border-red-500/50 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]'
              }`}>
                Kupiec POF: {replayData.backtest_result.passed ? "PASS" : "FAIL"}
              </div>
            )}
          </div>
          
          <div className="h-80 w-full mb-6">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#718096" 
                  fontSize={12} 
                  tickMargin={10} 
                  tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                />
                <YAxis 
                  stroke="#718096" 
                  fontSize={12} 
                  tickFormatter={(val) => `${(val * 100).toFixed(1)}%`}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a202c', borderColor: '#2d3748', borderRadius: '8px', color: '#e2e8f0' }}
                  labelFormatter={(val) => new Date(val).toLocaleDateString()}
                  formatter={(val: number, name: string) => [
                    `${(val * 100).toFixed(2)}%`,
                    name === 'var_95' ? '95% VaR (Prediction)' : name === 'actual_loss' ? 'Actual Loss' : 'Breach'
                  ]}
                />
                <Line 
                  type="monotone" 
                  dataKey="var_95" 
                  stroke="#a78bfa" 
                  strokeWidth={2} 
                  dot={false}
                  name="var_95"
                />
                <Line 
                  type="monotone" 
                  dataKey="actual_loss" 
                  stroke="#60a5fa" 
                  strokeWidth={1} 
                  dot={false}
                  name="actual_loss"
                />
                <Scatter 
                  dataKey="breach" 
                  fill="#ef4444" 
                  name="breach"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Stats Grid */}
          {replayData.backtest_result && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#0d1117] p-4 rounded-lg border border-gray-800">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Target Breach Rate</p>
                <p className="text-lg font-semibold text-gray-200">
                  {(replayData.backtest_result.predicted_breach_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-[#0d1117] p-4 rounded-lg border border-gray-800">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Actual Breach Rate</p>
                <p className="text-lg font-semibold text-gray-200">
                  {(replayData.backtest_result.actual_breach_rate * 100).toFixed(2)}%
                </p>
              </div>
              <div className="bg-[#0d1117] p-4 rounded-lg border border-gray-800">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Kupiec LR Statistic</p>
                <p className="text-lg font-semibold text-gray-200">
                  {replayData.backtest_result.kupiec_statistic.toFixed(3)}
                </p>
              </div>
              <div className="bg-[#0d1117] p-4 rounded-lg border border-gray-800">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">p-value</p>
                <p className="text-lg font-semibold text-gray-200">
                  {replayData.backtest_result.p_value.toFixed(4)}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
