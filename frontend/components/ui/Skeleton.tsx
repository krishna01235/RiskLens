/**
 * Skeleton.tsx — Shimmer skeleton placeholder.
 *
 * Used for loading states. Shape matches the real content so the
 * layout doesn't shift when data arrives (§4.5).
 */

interface SkeletonProps {
  /** Explicit width (e.g. "120px", "100%"). Defaults to 100%. */
  width?: string | number;
  /** Explicit height (e.g. "20px", "1rem"). Required. */
  height: string | number;
  className?: string;
}

export default function Skeleton({ width = "100%", height, className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`rounded-md skeleton-shimmer ${className}`}
      style={{ width, height }}
    />
  );
}

// ─── Convenience composite skeletons ──────────────────────────────────────

/** A skeleton that mimics a MetricCard */
export function MetricCardSkeleton() {
  return (
    <div className="rounded-lg border border-brand-border bg-brand-elevated p-6 space-y-3">
      <Skeleton height={13} width="60%" />
      <Skeleton height={32} width="80%" />
      <Skeleton height={12} width="50%" />
    </div>
  );
}

/** A row skeleton (e.g. risk contribution list) */
export function RowSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 py-1">
          <Skeleton height={12} width="30%" />
          <Skeleton height={8} className="flex-1" />
          <Skeleton height={12} width="15%" />
        </div>
      ))}
    </div>
  );
}
