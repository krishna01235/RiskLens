/**
 * constants.ts — Named constants for the public landing page components.
 *
 * All magic numbers are defined here as a single source of truth.
 * Components must import from here; never hardcode these values inline.
 */

// ── Hero Monte Carlo fan-chart ────────────────────────────────────────────────

/** Number of GBM paths drawn in the hero fan-chart. */
export const HERO_PATH_COUNT = 80;

/** Number of time steps (days) simulated per path. */
export const HERO_STEPS = 60;

/** Daily volatility used for GBM path generation (illustrative). */
export const HERO_VOLATILITY = 0.018;

/** Daily drift used for GBM path generation (illustrative). */
export const HERO_DRIFT = 0.0003;

/** Milliseconds between automatic re-simulations of the fan-chart. */
export const HERO_RESIM_INTERVAL_MS = 4000;

/** Delay per path during the initial animated draw-in (ms). */
export const HERO_PATH_DRAW_DELAY_MS = 18;

// ── Hero risk score ticker ────────────────────────────────────────────────────

/** Milliseconds between risk-score updates. */
export const SCORE_TICK_INTERVAL_MS = 1800;

/** Starting portfolio risk score (illustrative). */
export const SCORE_INITIAL = 64;

/** Pool of illustrative scores the ticker cycles through. */
export const SCORE_SEQUENCE = [64, 71, 58, 67, 73, 61, 69, 55, 74, 62];

// ── Fan-chart visual thresholds ───────────────────────────────────────────────

/** Percentile threshold below which paths are colored in the "breach" tone. */
export const CHART_LOWER_PERCENTILE = 0.1;

/** Percentile threshold above which paths are colored in the "safe" tone. */
export const CHART_UPPER_PERCENTILE = 0.9;

/** Opacity for mid-range paths. */
export const CHART_MID_OPACITY = 0.18;

/** Opacity for tail paths. */
export const CHART_TAIL_OPACITY = 0.55;
