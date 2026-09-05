/**
 * Input.tsx — Single-line text input with label + inline error.
 *
 * Spec: 36 px height, 1 px border, 2 px accent focus ring (no glow),
 * label above, inline error below in --color-breach.
 */

import { forwardRef, InputHTMLAttributes, useId } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  /** Hint text displayed below the input (shown only when no error) */
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className = "", id: idProp, ...props }, ref) => {
    const generatedId = useId();
    const id = idProp ?? generatedId;
    const errorId = `${id}-error`;
    const hintId = `${id}-hint`;

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={id}
            className="text-sm font-medium text-brand-secondary"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          aria-invalid={!!error}
          aria-describedby={
            error ? errorId : hint ? hintId : undefined
          }
          className={[
            "h-9 w-full rounded-md border bg-brand-elevated px-3 text-sm text-brand-primary",
            "placeholder:text-brand-tertiary",
            "transition-colors duration-fast",
            error
              ? "border-brand-breach focus:outline-none focus:ring-2 focus:ring-brand-breach focus:ring-offset-0"
              : "border-brand-border focus:outline-none focus:ring-2 focus:ring-brand-accent focus:ring-offset-0",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            className,
          ]
            .filter(Boolean)
            .join(" ")}
          {...props}
        />
        {error && (
          <p id={errorId} className="text-xs text-brand-breach" role="alert">
            {error}
          </p>
        )}
        {!error && hint && (
          <p id={hintId} className="text-xs text-brand-tertiary">
            {hint}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

export default Input;
