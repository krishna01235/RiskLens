"use client";

import { ReactNode } from "react";

interface ActionCardProps {
  title: string;
  description: string;
  icon: ReactNode;
  variant: "demo" | "csv" | "manual";
  onClick: () => void;
}

export default function ActionCard({
  title,
  description,
  icon,
  variant,
  onClick,
}: ActionCardProps) {
  const variantStyles = {
    demo: "border-blue-500/30 hover:border-blue-500 hover:shadow-blue-500/20",
    csv: "border-violet-500/30 hover:border-violet-500 hover:shadow-violet-500/20",
    manual: "border-teal-500/30 hover:border-teal-500 hover:shadow-teal-500/20",
  };

  const accentColors = {
    demo: "bg-blue-500",
    csv: "bg-violet-500",
    manual: "bg-teal-500",
  };

  return (
    <button
      onClick={onClick}
      className={`group relative flex w-full flex-col items-start rounded-xl border bg-slate-900/50 p-6 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-lg ${variantStyles[variant]}`}
    >
      <div
        className={`absolute left-0 top-0 h-full w-1 rounded-l-xl opacity-0 transition-opacity duration-300 group-hover:opacity-100 ${accentColors[variant]}`}
      />
      <div className="mb-4 text-3xl">{icon}</div>
      <h3 className="mb-2 text-lg font-semibold text-slate-100">{title}</h3>
      <p className="text-sm text-slate-400">{description}</p>
    </button>
  );
}
