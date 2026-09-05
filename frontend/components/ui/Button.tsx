/**
 * Button.tsx — Three-variant button primitive.
 *
 * Variants: primary (filled accent), secondary (outline), ghost (text only).
 * Spec: 6 px radius, no gradient, focus-visible ring, disabled opacity.
 */

import { forwardRef, ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] disabled:pointer-events-none disabled:opacity-50 select-none";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-accent hover:bg-brand-accent-h text-white border border-transparent",
  secondary:
    "bg-transparent border border-brand-border text-brand-primary hover:bg-brand-elevated",
  ghost:
    "bg-transparent border border-transparent text-brand-secondary hover:text-brand-primary hover:bg-brand-elevated",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-7 px-3 text-xs",
  md: "h-9 px-4 text-sm",
  lg: "h-10 px-5 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      className = "",
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
        {...props}
      >
        {loading && (
          <svg
            aria-hidden="true"
            className="h-3.5 w-3.5 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 11-8 8z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";

export default Button;
