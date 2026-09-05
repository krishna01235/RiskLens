/**
 * ActionCard.tsx — Onboarding path selection card, migrated to tokens.
 */

import Card from "@/components/ui/Card";
import { ReactNode } from "react";

interface ActionCardProps {
  title: string;
  description: string;
  icon: ReactNode;
  variant?: "demo" | "csv" | "manual";
  onClick: () => void;
}

const ACCENT_BORDER: Record<string, string> = {
  demo:   "hover:border-brand-accent/50",
  csv:    "hover:border-brand-accent/40",
  manual: "hover:border-brand-accent/30",
};

export default function ActionCard({
  title,
  description,
  icon,
  variant = "demo",
  onClick,
}: ActionCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left rounded-lg border border-brand-border bg-brand-elevated p-6 transition-colors duration-fast hover:bg-brand-hover ${ACCENT_BORDER[variant] ?? ""} focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]`}
    >
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-accent/10">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-brand-primary">{title}</h3>
      <p className="mt-1 text-xs text-brand-tertiary leading-relaxed">{description}</p>
    </button>
  );
}
