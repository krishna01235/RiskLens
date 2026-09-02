"use client";

import { useEffect, useState } from "react";

interface Props {
  progress: number; // 0.0 to 1.0
  status: "pending" | "running";
}

export default function SimulationProgress({ progress, status }: Props) {
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? "." : d + ".")), 500);
    return () => clearInterval(t);
  }, []);

  const pct = Math.round(progress * 100);

  return (
    <div className="bg-[#161b22] border border-gray-800 rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-300">
          {status === "pending" ? `Queuing simulation${dots}` : `Running simulation${dots}`}
        </p>
        <span className="text-blue-400 text-sm font-mono font-bold">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
          style={{ width: `${Math.max(pct, status === "pending" ? 3 : pct)}%` }}
        />
      </div>

      <p className="text-xs text-gray-500">
        {status === "pending"
          ? "Job is queued — it will start momentarily."
          : "Running GBM paths with Cholesky-correlated shocks and antithetic variates."}
      </p>
    </div>
  );
}
