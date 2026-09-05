/**
 * ConcentrationWarning.tsx — Left-accent-bar warning, migrated to tokens.
 *
 * Uses --color-watch for the WATCH-level semantic colour.
 * Text label always accompanies the colour signal (accessibility).
 */

export function ConcentrationWarning({
  correlationFlags,
}: {
  correlationFlags?: string[][];
}) {
  if (!correlationFlags || correlationFlags.length === 0) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-0 overflow-hidden rounded-lg border border-brand-watch/30 bg-brand-elevated mb-2"
    >
      {/* Left accent bar */}
      <div aria-hidden="true" className="w-1 self-stretch shrink-0 bg-brand-watch" />

      <div className="flex items-start gap-3 px-4 py-3">
        {/* Warning icon */}
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          className="shrink-0 mt-0.5 text-brand-watch"
        >
          <path
            d="M8 2L14.5 13H1.5L8 2Z"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
          <path d="M8 6.5v3M8 11h.01" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>

        <div className="space-y-1">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-brand-watch">
            Concentration Risk
          </h4>
          <p className="text-sm text-brand-primary">
            High correlation (&gt;0.7) detected between these assets — your
            portfolio may be less diversified than it appears.
          </p>
          <ul className="list-disc list-inside text-sm text-brand-secondary pt-0.5 space-y-0.5">
            {correlationFlags.map((cluster, i) => (
              <li key={i} className="font-mono text-xs">
                {cluster.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
