"use client";

interface RiskBudget {
  max_cvar: number;
  watch_threshold: number;
  high_threshold: number;
  breach_threshold: number;
}

interface Props {
  budget: RiskBudget | null;
  currentCvar: number | null;
  onConfigureClick: () => void;
}

const STATE_CONFIG = {
  SAFE:   { label: "SAFE",   color: "bg-emerald-500", text: "text-emerald-400", border: "border-emerald-500/30" },
  WATCH:  { label: "WATCH",  color: "bg-yellow-500",  text: "text-yellow-400",  border: "border-yellow-500/30" },
  HIGH:   { label: "HIGH",   color: "bg-orange-500",  text: "text-orange-400",  border: "border-orange-500/30" },
  BREACH: { label: "BREACH", color: "bg-red-500",     text: "text-red-400",     border: "border-red-500/30"   },
} as const;

function getState(util: number, b: RiskBudget): keyof typeof STATE_CONFIG {
  if (util >= b.breach_threshold) return "BREACH";
  if (util >= b.high_threshold)   return "HIGH";
  if (util >= b.watch_threshold)  return "WATCH";
  return "SAFE";
}

export default function RiskBudgetBar({ budget, currentCvar, onConfigureClick }: Props) {
  if (!budget) {
    return (
      <div className="bg-[#161b22] border border-gray-800 rounded-xl p-4 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400 font-medium">Risk Budget</p>
          <p className="text-xs text-gray-600 mt-0.5">No budget configured</p>
        </div>
        <button
          id="configure-budget-btn"
          onClick={onConfigureClick}
          className="text-xs text-blue-400 border border-blue-500/40 rounded-lg px-3 py-1.5 hover:bg-blue-500/10 transition-colors"
        >
          Configure
        </button>
      </div>
    );
  }

  const util = currentCvar != null && budget.max_cvar > 0
    ? currentCvar / budget.max_cvar
    : 0;
  const state = getState(util, budget);
  const cfg = STATE_CONFIG[state];
  const pct = Math.min(util * 100, 100);

  return (
    <div className={`bg-[#161b22] border ${cfg.border} rounded-xl p-4`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <p className="text-sm text-gray-300 font-medium">Risk Budget</p>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-opacity-20 ${cfg.text}`}>
            {cfg.label}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-gray-400">
            {(util * 100).toFixed(1)}% of budget
          </span>
          <button
            id="edit-budget-btn"
            onClick={onConfigureClick}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Edit
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="relative w-full h-3 bg-gray-800 rounded-full overflow-hidden">
        {/* Threshold markers */}
        <div
          className="absolute top-0 h-full w-px bg-yellow-500/60 z-10"
          style={{ left: `${budget.watch_threshold * 100}%` }}
          title={`Watch: ${(budget.watch_threshold * 100).toFixed(0)}%`}
        />
        <div
          className="absolute top-0 h-full w-px bg-orange-500/60 z-10"
          style={{ left: `${budget.high_threshold * 100}%` }}
          title={`High: ${(budget.high_threshold * 100).toFixed(0)}%`}
        />
        {/* Utilization fill */}
        <div
          className={`h-full ${cfg.color} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs text-gray-600 mt-1.5">
        <span>0</span>
        <span className="text-yellow-600">{(budget.watch_threshold * 100).toFixed(0)}%</span>
        <span className="text-orange-600">{(budget.high_threshold * 100).toFixed(0)}%</span>
        <span>Max CVaR: ${budget.max_cvar.toLocaleString()}</span>
      </div>
    </div>
  );
}
