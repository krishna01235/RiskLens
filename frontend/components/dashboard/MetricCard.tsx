/**
 * MetricCard.tsx — Dashboard metric card, migrated to design tokens.
 *
 * Changes from Phase 10 original:
 * - Uses <Card> primitive instead of ad-hoc Tailwind
 * - Value text uses font-mono (JetBrains Mono) for proper numeral alignment
 * - Number-update flash micro-animation (150 ms flash-green / flash-red)
 *   fires whenever `value` prop changes
 */

"use client";

import { useEffect, useRef, useState } from "react";
import Card from "@/components/ui/Card";

type Accent = "default" | "positive" | "negative";

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: Accent;
}

const VALUE_COLOR: Record<Accent, string> = {
  default:  "text-brand-primary",
  positive: "text-brand-safe",
  negative: "text-brand-breach",
};

export default function MetricCard({
  label,
  value,
  sub,
  accent = "default",
}: MetricCardProps) {
  const prevValue = useRef<string>(value);
  const [flashClass, setFlashClass] = useState<string>("");

  // Micro-animation: flash green on positive change, red on negative change
  useEffect(() => {
    if (prevValue.current === value) return;

    const oldNum = parseFloat(prevValue.current.replace(/[^0-9.-]/g, ""));
    const newNum = parseFloat(value.replace(/[^0-9.-]/g, ""));
    prevValue.current = value;

    if (Number.isNaN(oldNum) || Number.isNaN(newNum)) return;

    const cls = newNum >= oldNum ? "animate-flash-green" : "animate-flash-red";
    setFlashClass(cls);
    const t = setTimeout(() => setFlashClass(""), 200);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <Card>
      <h2 className="mb-2 text-xs font-medium text-brand-secondary">{label}</h2>
      <div
        className={`text-3xl font-semibold tracking-tight font-mono tabular-nums rounded-sm transition-colors ${VALUE_COLOR[accent]} ${flashClass}`}
      >
        {value}
      </div>
      {sub && (
        <p className="mt-2 text-xs text-brand-tertiary">{sub}</p>
      )}
    </Card>
  );
}
