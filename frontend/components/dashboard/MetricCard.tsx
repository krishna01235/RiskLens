/**
 * MetricCard.tsx — Presentational dashboard metric card.
 *
 * Follows the existing slate-900 / backdrop-blur card style used across the
 * dashboard (see app/dashboard/page.tsx).
 */

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: "default" | "positive" | "negative";
}

export default function MetricCard({
  label,
  value,
  sub,
  accent = "default",
}: MetricCardProps) {
  const valueColor =
    accent === "positive"
      ? "text-emerald-400"
      : accent === "negative"
        ? "text-red-400"
        : "text-white";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 shadow-lg backdrop-blur-sm">
      <h2 className="mb-2 text-sm font-medium text-slate-400">{label}</h2>
      <div className={`text-3xl font-semibold tracking-tight ${valueColor}`}>
        {value}
      </div>
      {sub ? <p className="mt-2 text-xs text-slate-500">{sub}</p> : null}
    </div>
  );
}
