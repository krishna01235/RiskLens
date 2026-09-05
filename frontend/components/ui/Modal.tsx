/**
 * Modal.tsx — Centered overlay modal.
 *
 * Spec:
 * - max-width 480 px for forms, 720 px for data-heavy content
 * - Closes on Escape key
 * - No click-outside dismiss (especially for destructive flows)
 * - Focus trap via autoFocus on first interactive element
 */

"use client";

import { useEffect, useRef, ReactNode } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  /** "sm" = 480 px (forms), "lg" = 720 px (data-heavy) */
  size?: "sm" | "lg";
  children: ReactNode;
  /** Prevent closing on Escape — use for destructive confirmations */
  preventEscapeClose?: boolean;
}

const SIZE_MAP = {
  sm: "max-w-[480px]",
  lg: "max-w-[720px]",
};

export default function Modal({
  open,
  onClose,
  title,
  size = "sm",
  children,
  preventEscapeClose = false,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!open || preventEscapeClose) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose, preventEscapeClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  const modal = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      aria-modal="true"
      role="dialog"
      aria-labelledby={title ? "modal-title" : undefined}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Panel */}
      <div
        ref={dialogRef}
        className={`relative z-10 w-full ${SIZE_MAP[size]} rounded-xl border border-brand-border bg-brand-elevated shadow-2xl`}
      >
        {title && (
          <div className="flex items-center justify-between border-b border-brand-border px-6 py-4">
            <h2
              id="modal-title"
              className="text-base font-semibold text-brand-primary"
            >
              {title}
            </h2>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="rounded-md p-1 text-brand-tertiary hover:text-brand-primary hover:bg-brand-hover transition-colors duration-fast focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M12 4L4 12M4 4l8 8"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
