"use client";

/**
 * MonteCarloFanChart.tsx — Live animated GBM fan-chart for the landing page hero.
 *
 * Design decisions:
 * - Pure Canvas 2D — no react-three-fiber or extra npm packages.
 * - The animated path draw-in IS the loading state (diegetic reveal per spec).
 * - prefers-reduced-motion: detected via matchMedia; skips animation + re-sim.
 * - Calls onP5Change(value) after each draw so the parent can update the
 *   live risk score from the actual simulated distribution.
 * - All magic numbers imported from constants.ts — never hardcoded here.
 */

import { useRef, useEffect, useCallback } from "react";
import {
  HERO_PATH_COUNT,
  HERO_STEPS,
  HERO_VOLATILITY,
  HERO_DRIFT,
  HERO_RESIM_INTERVAL_MS,
  HERO_PATH_DRAW_DELAY_MS,
  CHART_LOWER_PERCENTILE,
  CHART_UPPER_PERCENTILE,
  CHART_MID_OPACITY,
  CHART_TAIL_OPACITY,
} from "./constants";

interface MonteCarloFanChartProps {
  onP5Change?: (p5NormalisedValue: number) => void;
  className?: string;
}

// ── Mulberry32 PRNG — deterministic, seedable, no Math.random() ──────────────
function makePrng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── GBM path generation ───────────────────────────────────────────────────────
function generatePaths(seed: number): number[][] {
  const rand = makePrng(seed);
  const paths: number[][] = [];
  for (let p = 0; p < HERO_PATH_COUNT; p++) {
    const path: number[] = [1.0]; // start at 1 (normalised)
    for (let t = 0; t < HERO_STEPS; t++) {
      // Box-Muller transform for gaussian noise
      const u1 = Math.max(1e-10, rand());
      const u2 = rand();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      const prev = path[path.length - 1];
      path.push(prev * Math.exp(HERO_DRIFT - 0.5 * HERO_VOLATILITY ** 2 + HERO_VOLATILITY * z));
    }
    paths.push(path);
  }
  return paths;
}

// ── CSS variable reader ───────────────────────────────────────────────────────
function cssVar(name: string): string {
  if (typeof window === "undefined") return "#3E7BFA";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ── Main component ────────────────────────────────────────────────────────────
export default function MonteCarloFanChart({
  onP5Change,
  className = "",
}: MonteCarloFanChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const seedRef = useRef(Date.now());
  const animFrameRef = useRef<number | null>(null);
  const resimTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const drawTimeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;

  const clearDrawTimeouts = useCallback(() => {
    drawTimeoutsRef.current.forEach(clearTimeout);
    drawTimeoutsRef.current = [];
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
  }, []);

  const drawPaths = useCallback(
    (animated: boolean) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const W = canvas.width;
      const H = canvas.height;
      const paths = generatePaths(seedRef.current);

      // Sort by final value to assign tail colours
      const sorted = [...paths].sort((a, b) => a[HERO_STEPS] - b[HERO_STEPS]);
      const lowerCut = Math.floor(HERO_PATH_COUNT * CHART_LOWER_PERCENTILE);
      const upperCut = Math.floor(HERO_PATH_COUNT * CHART_UPPER_PERCENTILE);

      // Compute P5 for the onP5Change callback
      const finalVals = paths.map((p) => p[HERO_STEPS]).sort((a, b) => a - b);
      const p5idx = Math.floor(finalVals.length * 0.05);
      if (onP5Change) {
        onP5Change(finalVals[p5idx]);
      }

      const colorAccent = cssVar("--color-accent") || "#3E7BFA";
      const colorBreach = cssVar("--color-breach") || "#D9483D";
      const colorSafe = cssVar("--color-safe") || "#2FA96B";

      // Normalise path values for canvas coordinates
      const allVals = paths.flat();
      const minV = Math.min(...allVals);
      const maxV = Math.max(...allVals);
      const range = maxV - minV || 1;

      const toX = (t: number) => (t / HERO_STEPS) * W;
      const toY = (v: number) => H - ((v - minV) / range) * H * 0.8 - H * 0.1;

      ctx.clearRect(0, 0, W, H);

      const drawSinglePath = (path: number[], rank: number) => {
        const isTail =
          sorted.indexOf(path) < lowerCut || sorted.indexOf(path) >= upperCut;
        const isLower = sorted.indexOf(path) < lowerCut;
        const opacity = isTail ? CHART_TAIL_OPACITY : CHART_MID_OPACITY;
        const color = isTail
          ? isLower
            ? colorBreach
            : colorSafe
          : colorAccent;

        ctx.beginPath();
        ctx.moveTo(toX(0), toY(path[0]));
        for (let t = 1; t <= HERO_STEPS; t++) {
          ctx.lineTo(toX(t), toY(path[t]));
        }
        ctx.strokeStyle = color;
        ctx.globalAlpha = opacity;
        ctx.lineWidth = isTail ? 1.5 : 0.8;
        ctx.stroke();
        ctx.globalAlpha = 1;
        void rank; // used only to satisfy sort ordering
      };

      if (animated && !prefersReducedMotion) {
        clearDrawTimeouts();
        paths.forEach((path, i) => {
          const tid = setTimeout(() => {
            drawSinglePath(path, i);
          }, i * HERO_PATH_DRAW_DELAY_MS);
          drawTimeoutsRef.current.push(tid);
        });
      } else {
        // Immediate: draw all at once (reduced motion or re-sim)
        paths.forEach((path, i) => drawSinglePath(path, i));
      }
    },
    [onP5Change, prefersReducedMotion, clearDrawTimeouts]
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Set canvas pixel size to match display size
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * (window.devicePixelRatio || 1);
      canvas.height = rect.height * (window.devicePixelRatio || 1);
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
      drawPaths(false); // immediate on resize
    };

    resize();

    // Initial animated draw-in
    drawPaths(true);

    // Periodic re-simulation (skip if reduced motion)
    if (!prefersReducedMotion) {
      resimTimerRef.current = setInterval(() => {
        seedRef.current = Date.now();
        drawPaths(false); // re-sim: immediate, no draw animation
      }, HERO_RESIM_INTERVAL_MS);
    }

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    return () => {
      clearDrawTimeouts();
      if (resimTimerRef.current) clearInterval(resimTimerRef.current);
      ro.disconnect();
    };
  }, [drawPaths, prefersReducedMotion, clearDrawTimeouts]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ display: "block", width: "100%", height: "100%" }}
      aria-label="Monte Carlo simulation fan-chart showing portfolio return distribution"
      role="img"
    />
  );
}
