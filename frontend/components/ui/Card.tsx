/**
 * Card.tsx — Shared card container.
 *
 * Spec: 8 px radius, 1 px border (not shadow-based), 16/24 px internal padding.
 */

import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Use `elevated` for nested cards or panels that sit on top of a card. */
  elevated?: boolean;
  padding?: "sm" | "md" | "lg";
}

const PADDING = {
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

export default function Card({
  elevated = false,
  padding = "lg",
  className = "",
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-lg border border-brand-border ${
        elevated ? "bg-brand-elevated" : "bg-brand-elevated"
      } ${PADDING[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
