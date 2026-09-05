"use client";

/**
 * LandingNav.tsx — Minimal public navigation for the landing page.
 *
 * Sticky top-bar with logo (same SVG as auth pages) + ghost "Sign in" button
 * + primary "Get started" button. Uses existing Button primitive exactly —
 * no custom nav styling invented.
 */

import Link from "next/link";

export default function LandingNav() {
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        borderBottom: "1px solid var(--color-border)",
        backgroundColor: "var(--color-bg)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
      }}
      aria-label="Main navigation"
    >
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
          padding: "0 var(--sp-6)",
          height: "var(--topbar-height)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Logo */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--sp-2)",
            textDecoration: "none",
          }}
          aria-label="RiskLens home"
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: "var(--radius-md)",
              border: "1px solid rgba(62,123,250,0.3)",
              backgroundColor: "rgba(62,123,250,0.10)",
              flexShrink: 0,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path
                d="M3 14L6.5 8L10 11L13.5 5L16 7"
                stroke="var(--color-accent)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-sm)",
              fontWeight: "var(--fw-semibold)",
              color: "var(--color-text-primary)",
              letterSpacing: "-0.01em",
            }}
          >
            RiskLens
          </span>
        </Link>

        {/* Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--sp-2)" }}>
          <Link
            href="/login"
            id="nav-signin"
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: 28,
              padding: "0 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid transparent",
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-xs)",
              fontWeight: "var(--fw-medium)",
              color: "var(--color-text-secondary)",
              textDecoration: "none",
              transition: "color 150ms, background-color 150ms",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-text-primary)";
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "var(--color-bg-elevated)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-text-secondary)";
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "transparent";
            }}
          >
            Sign in
          </Link>
          <Link
            href="/register"
            id="nav-get-started"
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: 28,
              padding: "0 12px",
              borderRadius: "var(--radius-md)",
              border: "1px solid transparent",
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-xs)",
              fontWeight: "var(--fw-medium)",
              color: "#fff",
              backgroundColor: "var(--color-accent)",
              textDecoration: "none",
              transition: "background-color 150ms",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "var(--color-accent-hover)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "var(--color-accent)";
            }}
          >
            Get started
          </Link>
        </div>
      </div>
    </nav>
  );
}
