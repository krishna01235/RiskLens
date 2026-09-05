/**
 * Toast.tsx — Bottom-right notification toasts.
 *
 * Spec:
 * - Bottom-right, auto-dismiss 5 s except BREACH-level (persists)
 * - Left-accent-bar coloured by risk state
 * - Animate in with toast-in keyframe
 *
 * Usage: import { useToast, ToastProvider } from "@/components/ui/Toast"
 * Wrap the app with <ToastProvider />; call toast() anywhere.
 */

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";

type Severity = "safe" | "watch" | "high" | "breach" | "info";

interface ToastItem {
  id: string;
  message: string;
  severity: Severity;
  /** Default: auto-dismiss 5 s. BREACH never auto-dismisses unless forced. */
  persist?: boolean;
}

interface ToastContextValue {
  toast: (message: string, severity?: Severity, persist?: boolean) => void;
}

const ToastContext = createContext<ToastContextValue>({
  toast: () => undefined,
});

export function useToast() {
  return useContext(ToastContext);
}

// ── Colour map per severity ────────────────────────────────────────────────
const ACCENT: Record<Severity, string> = {
  safe:   "bg-brand-safe",
  watch:  "bg-brand-watch",
  high:   "bg-brand-high",
  breach: "bg-brand-breach",
  info:   "bg-brand-accent",
};

const LABEL: Record<Severity, string> = {
  safe:   "SAFE",
  watch:  "WATCH",
  high:   "HIGH",
  breach: "BREACH",
  info:   "INFO",
};

const LABEL_COLOR: Record<Severity, string> = {
  safe:   "text-brand-safe",
  watch:  "text-brand-watch",
  high:   "text-brand-high",
  breach: "text-brand-breach",
  info:   "text-brand-accent",
};

// ── Single toast card ──────────────────────────────────────────────────────
function ToastCard({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: string) => void;
}) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const shouldAutoDismiss =
    !item.persist && item.severity !== "breach";

  useEffect(() => {
    if (shouldAutoDismiss) {
      timerRef.current = setTimeout(() => onDismiss(item.id), 5000);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [item.id, shouldAutoDismiss, onDismiss]);

  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex w-80 items-start gap-0 overflow-hidden rounded-lg border border-brand-border bg-brand-elevated shadow-lg animate-toast-in"
    >
      {/* Left accent bar */}
      <div className={`w-1 self-stretch shrink-0 ${ACCENT[item.severity]}`} />
      <div className="flex flex-1 items-start gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <p
            className={`text-xs font-semibold uppercase tracking-wide ${LABEL_COLOR[item.severity]}`}
          >
            {LABEL[item.severity]}
          </p>
          <p className="mt-0.5 text-sm text-brand-primary leading-snug">
            {item.message}
          </p>
        </div>
        <button
          onClick={() => onDismiss(item.id)}
          aria-label="Dismiss notification"
          className="mt-0.5 shrink-0 rounded p-0.5 text-brand-tertiary hover:text-brand-primary transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M11 3L3 11M3 3l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Provider ───────────────────────────────────────────────────────────────
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, severity: Severity = "info", persist?: boolean) => {
      const id = `${Date.now()}-${Math.random()}`;
      const autoPersist = severity === "breach";
      setToasts((prev) => [
        ...prev,
        { id, message, severity, persist: persist ?? autoPersist },
      ]);
    },
    [],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast stack — bottom-right */}
      <div
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end"
      >
        {toasts.map((item) => (
          <ToastCard key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export type { Severity, ToastItem };
