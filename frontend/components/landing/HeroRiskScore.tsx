"use client";

/**
 * HeroRiskScore.tsx — Live monospaced risk-score number for the landing hero.
 *
 * Reuses the EXACT same number-update flash micro-interaction from
 * MetricCard.tsx (§4.5): useRef to track previous value, useEffect to
 * compare and apply animate-flash-green / animate-flash-red.
 *
 * Not reinvented — identical pattern, just a standalone component for the
 * landing page context where MetricCard's Card wrapper is not appropriate.
 */

import { useEffect, useRef, useState } from "react";
import { SCORE_TICK_INTERVAL_MS, SCORE_SEQUENCE, SCORE_INITIAL } from "./constants";

interface HeroRiskScoreProps {
  /** Override the displayed score (driven by fan-chart P5). When not set,
   *  the component self-drives from SCORE_SEQUENCE. */
  externalScore?: number | null;
}

export default function HeroRiskScore({ externalScore }: HeroRiskScoreProps) {
  const [score, setScore] = useState(SCORE_INITIAL);
  const seqIdxRef = useRef(0);

  // Self-drive from sequence when no external score is provided
  useEffect(() => {
    if (externalScore != null) return; // driven externally — skip ticker
    const id = setInterval(() => {
      seqIdxRef.current = (seqIdxRef.current + 1) % SCORE_SEQUENCE.length;
      setScore(SCORE_SEQUENCE[seqIdxRef.current]);
    }, SCORE_TICK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [externalScore]);

  // Sync to external score when provided
  useEffect(() => {
    if (externalScore == null) return;
    // Map P5 normalised value (0.8–1.2 range) to a 0–100 risk score
    const mapped = Math.round(Math.max(0, Math.min(100, (2 - externalScore) * 55)));
    setScore(mapped);
  }, [externalScore]);

  // ── Number-update flash — identical to MetricCard.tsx ──────────────────────
  const prevScore = useRef(score);
  const [flashClass, setFlashClass] = useState("");

  useEffect(() => {
    if (prevScore.current === score) return;
    const cls = score < prevScore.current ? "flash-green" : "flash-red";
    prevScore.current = score;
    setFlashClass(cls);
    const t = setTimeout(() => setFlashClass(""), 200);
    return () => clearTimeout(t);
  }, [score]);

  return (
    <div style={{ display: "inline-block" }}>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--color-text-secondary)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: "var(--sp-2)",
        }}
      >
        Portfolio Risk Score
      </p>
      <div
        className={flashClass}
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "clamp(3rem, 8vw, 5.5rem)",
          fontWeight: "var(--fw-semibold)",
          color: score > 70 ? "var(--color-breach)" : score > 55 ? "var(--color-watch)" : "var(--color-safe)",
          lineHeight: 1,
          letterSpacing: "-0.02em",
          display: "inline-block",
          borderRadius: "var(--radius-sm)",
          padding: "2px 4px",
          transition: "color 300ms ease",
          fontVariantNumeric: "tabular-nums",
        }}
        aria-live="polite"
        aria-label={`Portfolio risk score: ${score}`}
      >
        {score}
      </div>
      <p
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-xs)",
          color: "var(--color-text-tertiary)",
          marginTop: "var(--sp-2)",
        }}
      >
        {score > 70 ? "HIGH RISK" : score > 55 ? "WATCH" : "SAFE"} ·{" "}
        simulated portfolio
      </p>
    </div>
  );
}
