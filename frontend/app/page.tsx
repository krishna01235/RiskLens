"use client";

/**
 * app/page.tsx — Public landing page.
 *
 * Session redirect: on mount, attempt silentRefresh() via the httpOnly cookie.
 * If a valid session exists, redirect to /dashboard immediately — a returning
 * logged-in user never sees the marketing page.
 *
 * MonteCarloFanChart is loaded via next/dynamic with { ssr: false } so it is
 * never bundled into any authenticated app route. Zero cost to the dashboard
 * bundle.
 */

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import LandingNav from "@/components/landing/LandingNav";
import HeroRiskScore from "@/components/landing/HeroRiskScore";
import FeatureSection from "@/components/landing/FeatureSection";
import AiPreview from "@/components/landing/AiPreview";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Lazy-load the fan-chart — never bundled into dashboard or any auth route
const MonteCarloFanChart = dynamic(
  () => import("@/components/landing/MonteCarloFanChart"),
  { ssr: false }
);

export default function LandingPage() {
  const router = useRouter();
  const [sessionChecked, setSessionChecked] = useState(false);
  const [p5Value, setP5Value] = useState<number | null>(null);

  // Silent session check — redirect logged-in users straight to dashboard
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!cancelled && resp.ok) {
          router.replace("/dashboard");
          return;
        }
      } catch {
        // No session — show landing page
      }
      if (!cancelled) setSessionChecked(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const handleP5Change = useCallback((val: number) => {
    setP5Value(val);
  }, []);

  // While checking session, show nothing (avoids flash of marketing for returning users)
  if (!sessionChecked) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "var(--color-bg)",
        }}
        aria-hidden="true"
      />
    );
  }

  return (
    <div style={{ backgroundColor: "var(--color-bg)", minHeight: "100vh" }}>
      {/* SEO */}
      <title>RiskLens — Quantitative Portfolio Risk Intelligence</title>

      <LandingNav />

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "var(--sp-12) var(--sp-6)",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "var(--sp-8)",
          alignItems: "center",
          minHeight: "calc(100vh - var(--topbar-height))",
        }}
        aria-label="Hero section"
      >
        {/* Left: live score */}
        <div>
          {/* Terminal-style label */}
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--text-xs)",
              color: "var(--color-text-tertiary)",
              letterSpacing: "0.08em",
              marginBottom: "var(--sp-4)",
            }}
          >
            <span style={{ color: "var(--color-safe)" }}>●</span> live simulation
            running
          </p>

          <HeroRiskScore externalScore={p5Value} />

          <p
            style={{
              fontFamily: "var(--font-ui)",
              fontSize: "var(--text-base)",
              color: "var(--color-text-secondary)",
              lineHeight: 1.7,
              maxWidth: 440,
              marginTop: "var(--sp-6)",
              marginBottom: "var(--sp-8)",
            }}
          >
            Continuous VaR, CVaR, Monte Carlo, GARCH volatility, and
            AI-explained alerts — recomputed in real time as markets move.
            This is what institutional risk desks use, productised for
            individual portfolios.
          </p>

          <div style={{ display: "flex", gap: "var(--sp-3)", flexWrap: "wrap" }}>
            <Link
              href="/register"
              id="hero-cta-primary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                height: 40,
                padding: "0 var(--sp-6)",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--color-accent)",
                color: "#fff",
                fontFamily: "var(--font-ui)",
                fontSize: "var(--text-sm)",
                fontWeight: "var(--fw-medium)",
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
              Try the demo portfolio →
            </Link>
            <Link
              href="/login"
              id="hero-cta-secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                height: 40,
                padding: "0 var(--sp-6)",
                borderRadius: "var(--radius-md)",
                backgroundColor: "transparent",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-secondary)",
                fontFamily: "var(--font-ui)",
                fontSize: "var(--text-sm)",
                fontWeight: "var(--fw-medium)",
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
          </div>
        </div>

        {/* Right: fan-chart */}
        <div
          style={{
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-xl)",
            overflow: "hidden",
            height: 360,
            backgroundColor: "var(--color-bg-elevated)",
            position: "relative",
          }}
          aria-label="Live Monte Carlo simulation fan-chart"
        >
          {/* Axis labels */}
          <div
            style={{
              position: "absolute",
              top: "var(--sp-3)",
              left: "var(--sp-4)",
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              color: "var(--color-text-tertiary)",
              zIndex: 1,
              pointerEvents: "none",
            }}
          >
            Monte Carlo · {/* path count from constant */}80 paths · 60-day horizon
          </div>
          <MonteCarloFanChart
            onP5Change={handleP5Change}
            className=""
          />
        </div>
      </section>

      {/* ── What it actually does ──────────────────────────────────────────── */}
      <div style={{ borderTop: "1px solid var(--color-border)" }}>
        <FeatureSection />
      </div>

      {/* ── AI preview ────────────────────────────────────────────────────── */}
      <AiPreview />

      {/* ── Final CTA ─────────────────────────────────────────────────────── */}
      <section
        style={{
          borderTop: "1px solid var(--color-border)",
          padding: "var(--sp-16) var(--sp-6)",
          textAlign: "center",
        }}
        aria-label="Call to action"
      >
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-xs)",
            color: "var(--color-text-tertiary)",
            letterSpacing: "0.08em",
            marginBottom: "var(--sp-4)",
          }}
        >
          No credit card. No configuration. Instant demo data.
        </p>
        <h2
          style={{
            fontFamily: "var(--font-ui)",
            fontSize: "var(--text-xl)",
            fontWeight: "var(--fw-semibold)",
            color: "var(--color-text-primary)",
            marginBottom: "var(--sp-6)",
            lineHeight: 1.3,
          }}
        >
          See your portfolio through a quant lens.
        </h2>
        <Link
          href="/register"
          id="footer-cta"
          style={{
            display: "inline-flex",
            alignItems: "center",
            height: 44,
            padding: "0 var(--sp-8)",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-accent)",
            color: "#fff",
            fontFamily: "var(--font-ui)",
            fontSize: "var(--text-base)",
            fontWeight: "var(--fw-medium)",
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
          Try the demo portfolio →
        </Link>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid var(--color-border)",
          padding: "var(--sp-6)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          maxWidth: 1100,
          margin: "0 auto",
          flexWrap: "wrap",
          gap: "var(--sp-4)",
        }}
        aria-label="Footer"
      >
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-xs)",
            color: "var(--color-text-tertiary)",
          }}
        >
          © 2026 RiskLens. Quant-grade portfolio risk.
        </p>
        <div style={{ display: "flex", gap: "var(--sp-4)" }}>
          {[
            { href: "/login", label: "Sign in" },
            { href: "/register", label: "Get started" },
          ].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              style={{
                fontFamily: "var(--font-ui)",
                fontSize: "var(--text-xs)",
                color: "var(--color-text-tertiary)",
                textDecoration: "none",
              }}
            >
              {label}
            </Link>
          ))}
        </div>
      </footer>
    </div>
  );
}
