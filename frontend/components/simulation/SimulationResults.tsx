"use client";

interface SimResult {
  prob_profit: number;
  prob_loss: number;
  expected_pnl: number;
  pnl_p5: number;
  pnl_p50: number;
  pnl_p95: number;
  num_paths: number;
}

interface Props {
  result: SimResult;
}

function fmt(n: number) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })}`;
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

export default function SimulationResults({ result }: Props) {
  const range = result.pnl_p95 - result.pnl_p5;
  const barWidth = (v: number) => {
    if (range === 0) return 50;
    return Math.max(5, Math.min(95, ((v - result.pnl_p5) / range) * 100));
  };

  return (
    <div className="mt-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-200">Simulation Results</h2>
      <p className="text-xs text-gray-500">{result.num_paths.toLocaleString()} paths</p>

      {/* Probability row */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">{pct(result.prob_profit)}</p>
          <p className="text-xs text-gray-400 mt-1">Probability of Profit</p>
        </div>
        <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-red-400">{pct(result.prob_loss)}</p>
          <p className="text-xs text-gray-400 mt-1">Probability of Loss</p>
        </div>
      </div>

      {/* Expected P&L */}
      <div className={`border rounded-xl p-4 ${result.expected_pnl >= 0 ? "bg-blue-900/20 border-blue-500/30" : "bg-orange-900/20 border-orange-500/30"}`}>
        <p className="text-xs text-gray-400 mb-1">Expected P&L</p>
        <p className={`text-3xl font-bold ${result.expected_pnl >= 0 ? "text-blue-300" : "text-orange-300"}`}>
          {fmt(result.expected_pnl)}
        </p>
      </div>

      {/* Percentile range bar */}
      <div className="bg-[#161b22] border border-gray-800 rounded-xl p-4 space-y-3">
        <p className="text-xs text-gray-400 font-medium">P&L Range (5th – 95th Percentile)</p>
        <div className="relative h-8 bg-gray-800 rounded-lg overflow-hidden">
          {/* Fill between P5 and P95 */}
          <div
            className="absolute top-0 h-full bg-gradient-to-r from-orange-500/60 to-blue-500/60 rounded-lg"
            style={{ left: "5%", width: "90%" }}
          />
          {/* Median marker */}
          <div
            className="absolute top-0 h-full w-0.5 bg-white/80"
            style={{ left: `${barWidth(result.pnl_p50)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 font-mono">
          <span className="text-orange-400">P5: {fmt(result.pnl_p5)}</span>
          <span className="text-gray-300">P50: {fmt(result.pnl_p50)}</span>
          <span className="text-blue-400">P95: {fmt(result.pnl_p95)}</span>
        </div>
      </div>
    </div>
  );
}
