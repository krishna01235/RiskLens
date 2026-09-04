import { DecisionCandidate } from "@/hooks/useRiskSocket";
import { CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";

export function DecisionCard({ candidate }: { candidate: DecisionCandidate }) {
  const isBest = candidate.score === 100;
  
  return (
    <div className={`p-4 rounded-lg border flex flex-col gap-2 transition-all ${
      isBest 
        ? "bg-green-500/10 border-green-500/50 shadow-[0_0_15px_rgba(34,197,94,0.1)]" 
        : "bg-gray-800/50 border-gray-700 hover:border-gray-600"
    }`}>
      <div className="flex justify-between items-start">
        <h4 className="font-semibold text-gray-100">{candidate.label}</h4>
        {isBest && (
          <span className="flex items-center gap-1 text-xs font-bold text-green-400 bg-green-500/20 px-2 py-1 rounded-full uppercase tracking-wider">
            <CheckCircle2 className="w-3 h-3" />
            Recommended
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mt-2">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Expected Return</p>
          <p className={`text-lg font-mono ${candidate.expected_return >= 0 ? "text-green-400" : "text-red-400"}`}>
            {candidate.expected_return > 0 ? "+" : ""}{(candidate.expected_return * 100).toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">CVaR (95%)</p>
          <p className="text-lg font-mono text-gray-200">
            {(candidate.cvar * 100).toFixed(2)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Prob. Loss</p>
          <p className="text-lg font-mono text-gray-200">
            {(candidate.p_loss * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Score</p>
          <p className="text-lg font-mono text-gray-200">
            {candidate.score.toFixed(0)} / 100
          </p>
        </div>
      </div>

      {candidate.is_fallback && (
        <div className="mt-2 flex items-start gap-2 text-xs text-amber-500/80 bg-amber-500/10 p-2 rounded-md">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <p>Evaluation timed out. Score is based on deterministic mean-variance approximation rather than full Monte Carlo.</p>
        </div>
      )}
    </div>
  );
}
