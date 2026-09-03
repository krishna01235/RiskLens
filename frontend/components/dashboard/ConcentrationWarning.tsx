import { AlertTriangle } from "lucide-react";

export function ConcentrationWarning({
  correlationFlags,
}: {
  correlationFlags?: string[][];
}) {
  if (!correlationFlags || correlationFlags.length === 0) {
    return null;
  }

  return (
    <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 rounded-lg p-4 mb-6 animate-in fade-in slide-in-from-top-2">
      <div className="flex gap-3">
        <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-medium text-yellow-500/90">Concentration Risk Detected</h4>
          <p className="text-sm text-yellow-500/80">
            High correlation (&gt;0.7) found between the following assets. Your portfolio may be less diversified than it appears.
          </p>
          <ul className="list-disc list-inside text-sm text-yellow-500/80 pt-1">
            {correlationFlags.map((cluster, i) => (
              <li key={i}>{cluster.join(", ")}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
