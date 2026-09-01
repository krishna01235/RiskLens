# RiskLens — Implementation Master Plan

**Version:** 1.0
**Status:** Source of truth for engineering execution
**Scope:** Empty repository → production-ready, deployed application

---

## Table of Contents

1. Project Overview
2. Assumptions & Decisions
3. Product Requirements
4. UI/UX Design System
5. Application Architecture
6. Technology Stack
7. API Design
8. Database Design
9. Folder Structure & Naming Conventions
10. Code Architecture & Standards
11. Security
12. Performance & Scalability
13. Testing Strategy
14. Git & Development Strategy (Phases 1–24)
15. Phase Dependency Map
16. Project-Wide Definition of Done
17. Production Readiness Checklist
18. Developer Experience
19. Engineering Principle
20. Final Implementation Roadmap
21. Feature → Phase Mapping
22. Architecture Summary
23. Final Project Checklist

---

## 1. Project Overview

### What the product is

**RiskLens** is a full-stack, event-driven quantitative risk platform. It continuously watches a user's investment portfolio, quantifies risk in real time (VaR, CVaR, volatility, drawdown, correlation concentration), detects when risk crosses an acceptable threshold, explains *why* in plain language via a tool-calling AI layer, and recommends ranked, non-executing actions to reduce risk. A historical replay mode proves the system would have flagged real past market stress events before the resulting drawdown occurred.

RiskLens is **not** a portfolio dashboard and **not** a trading bot. It is a **risk decision layer** that sits on top of a portfolio.

### The problem it solves

Existing retail-facing tools (Portfolio Visualizer, Nitrogen/Riskalyze, broker analytics tabs) are **pull-based**: a user must remember to open the tool and manually re-run a calculation. They also stop at a number ("your CVaR is ₹48,000") without telling the user what to do about it, and they show *allocation* percentages rather than *risk contribution*, which hides concentrated bets inside seemingly diversified portfolios.

RiskLens solves a narrower, real, and currently under-served problem: **continuous, proactive risk monitoring with an actionable, explained response** — for a specific audience, not the general retail investor population.

### Target users

- Active/self-directed traders who already think in risk terms
- Quant-curious retail investors
- Small independent analysts / portfolio managers who want a lightweight continuous-monitoring layer

### Core value proposition

> "A system that watches your portfolio continuously and pushes a risk alert plus a ranked action recommendation the moment something changes — instead of a dashboard you have to remember to check."

### Major capabilities

- Real-time, event-driven risk recalculation as market prices move
- Risk budget definition and automatic breach detection (SAFE / WATCH / HIGH / BREACH)
- Hidden correlation / concentration detection (risk contribution, not just allocation)
- Monte Carlo simulation (GBM + correlated shocks) run as an async job with live progress
- Extreme Value Theory (EVT) tail-risk estimate shown alongside Monte Carlo, for a second, more honest worst-case view
- GARCH(1,1) time-varying volatility feeding the simulation engine
- Ledoit-Wolf covariance shrinkage for a stable, well-conditioned risk-model input
- Hidden Markov Model (HMM) market-regime detection (calm vs. stressed, as a probability, not a hard label)
- Kupiec proportion-of-failures backtest to validate that the risk model's own confidence claims are honest
- A decision engine that ranks 2–3 concrete actions (do nothing / reduce a position / increase cash) by risk/return trade-off
- A tool-calling AI layer that **explains** risk and answers **what-if** questions, but never performs financial calculations itself
- Historical replay against real past market stress periods, ending in a Kupiec-validated "would have warned you" moment
- A second client (Slack bot) proving the backend is a real, reusable API, not a UI-coupled monolith
- CSV portfolio import with a broker-format normalization layer, plus manual entry and a zero-friction demo portfolio

### Important constraints

- **Advisory only.** The system never executes trades. All recommendations require explicit user action outside the system.
- **No broker credentials are ever stored.** Portfolio data enters via CSV upload, manual entry, or a seeded demo — never via storing a broker password.
- **AI never calculates.** All numeric outputs (VaR, CVaR, Monte Carlo, decision-engine metrics) come from the deterministic quant engine. The AI only calls tools and narrates results in plain language.
- **Single-region, single-instance MVP scale.** The architecture is designed to scale (documented upgrade paths throughout), but the MVP is built and deployed for a small number of concurrent demo users, not 100K concurrent users. Do not introduce infrastructure (Kubernetes, multi-region Kafka clusters) that this scale does not need.

### Key product principles

1. Push, not pull — the system tells the user something changed; the user does not go looking.
2. Numbers are computed, never guessed — especially by the AI layer.
3. Every claim of confidence (e.g. "95% VaR") must be backed by a way to check whether that confidence was honest (the Kupiec backtest).
4. Advisory, never autonomous — the system ranks options, the human decides.
5. Every architectural decision must have a stated reason and a stated scaling story, even if the MVP itself doesn't need to scale yet.

---

## 2. Assumptions & Decisions

Where prior discussion did not pin down an exact choice, the following decisions are made and should be treated as final unless explicitly revisited:

| # | Topic | Decision | Reasoning |
|---|---|---|---|
| A1 | Event backbone | **Redis Streams**, not Kafka | Kafka's operational overhead (broker cluster, Zookeeper/KRaft, partition management) is disproportionate to this project's scale. Redis Streams gives consumer groups, at-least-once delivery, and persistence, and reuses infrastructure already needed for caching/pub-sub. Documented as a swappable component — see §5. |
| A2 | Async job queue (Monte Carlo) | **`arq`** (async Redis queue) | The backend is asyncio-native (FastAPI + async SQLAlchemy). `arq` is built for asyncio and reuses the same Redis instance, avoiding the operational weight of Celery + a separate broker. |
| A3 | Market data provider | **Finnhub** (free tier WebSocket) | Real-time-with-15-min-delay-on-free-tier trade stream is sufficient to prove the event-driven architecture. Documented as swappable — production would use a paid low-latency feed (e.g. Polygon.io) or a broker market-data feed for Indian equities (e.g. Kite Connect) with no architectural change beyond the ingestion worker. |
| A4 | Equity universe | **US large-cap equities** for MVP demo (NVDA, AMD, AAPL, MSFT, GOOG, cash) | Best free real-time data coverage. Currency formatting is abstracted (see Database Design) so INR/Indian-equities support is a data-source swap, not a rewrite. |
| A5 | Auth | **Custom JWT (access + refresh token)** with email/password; Google OAuth added as a Phase 4 stretch task | Keeps the MVP dependency-light and fully understood by the developer, while leaving room for OAuth without redesigning the user table. |
| A6 | AI provider | **Anthropic Claude API**, orchestrated via **LangGraph** | Matches existing developer experience (LangGraph used in a prior project), strong native tool-calling support, and LangGraph gives a clean, swappable tool-registration pattern. OpenAI GPT-4o is documented as a drop-in alternative if cost or availability requires it. |
| A7 | Frontend framework | **Next.js 14 (App Router) + TypeScript + Tailwind CSS** | Industry-standard, strong ecosystem for WebSocket + chart-heavy dashboards, deployable to Vercel with zero configuration. |
| A8 | Second client | **Slack bot** (Slack Bolt SDK), not a browser extension | Equivalent "multi-client architecture" resume/portfolio value at a fraction of the engineering cost of a Chrome Manifest V3 extension with its own auth/build pipeline. |
| A9 | Deployment target | **Render** for backend services + PostgreSQL + Redis; **Vercel** for the Next.js frontend | Render supports multiple long-running services (API + workers) plus managed Postgres/Redis from one dashboard with Docker support; Vercel is the best-supported host for Next.js. Both have free/low-cost tiers suitable for a demo deployment. This is a recommendation, not a hard external dependency — the Docker Compose setup in Phase 2 works identically on any container host. |
| A10 | Historical replay dataset | A **static, checked-in CSV dataset** of daily OHLC prices for the demo symbols covering at least one real historical stress period (e.g. 2022 rate-shock window) | Avoids paying for or rate-limiting against a historical-data API for a bounded, known demo dataset. Documented as swappable for a live historical-data API call in a future iteration. |
| A11 | Notifications | **In-app (WebSocket-pushed) and Slack only** for MVP | Email/SMS alerting is explicitly out of scope for MVP; the architecture's alert-publishing step (Redis pub/sub) makes adding an email channel later a new subscriber, not a redesign. |

---

## 3. Product Requirements

### 3.1 Feature Inventory (Core)

| ID | Feature | Priority |
|---|---|---|
| F1 | Authentication (register/login/refresh/logout) | Core |
| F2 | Portfolio ingestion — demo seed, CSV import, manual entry | Core |
| F3 | Symbol → portfolio reverse index & dynamic Finnhub subscription management | Core |
| F4 | Real-time tick ingestion & fan-out (fast path) | Core |
| F5 | Slow-path risk recompute (VaR, CVaR, volatility, drawdown, Sharpe, risk contribution) | Core |
| F6 | Ledoit-Wolf covariance shrinkage | Core |
| F7 | GARCH(1,1) volatility modeling | Core |
| F8 | Monte Carlo simulation (async, progress-streamed) | Core |
| F9 | EVT / Peaks-Over-Threshold tail risk | Core |
| F10 | Risk budget configuration & breach detection/alerting | Core |
| F11 | Hidden correlation / concentration detector | Core |
| F12 | HMM market regime detection | Core |
| F13 | Kupiec backtest (model validation) | Core |
| F14 | Decision engine (ranked actions) | Core |
| F15 | AI risk analyst — explain + what-if (tool-calling only) | Core |
| F16 | Historical replay | Core |
| F17 | Slack bot second client | Core |
| F18 | Frontend dashboard (all screens) | Core |
| F19 | Docker Compose local dev environment | Core |
| F20 | CI/CD pipeline | Core |
| F21 | Email/SMS notification channel | Out of scope (documented extension point) |
| F22 | Portfolio optimization (mean-variance / Black-Litterman) | Out of scope (documented extension point) |
| F23 | Broker OAuth live integration | Out of scope (documented extension point) |
| F24 | Copula-based tail-dependence modeling | Out of scope (documented as future work) |

### 3.2 Detailed Feature Specifications

Each feature below follows: **What / Why / User Flow / Frontend / Backend / API / Database / Edge Cases / Errors / Security.**

---

#### F1 — Authentication

- **What:** Email/password registration and login issuing a short-lived JWT access token and a long-lived refresh token (httpOnly cookie).
- **Why:** Every portfolio, alert, and simulation must be scoped to exactly one user; this is a financial-adjacent app and must not allow cross-user data access.
- **User Flow:** Register → auto-login → land on onboarding (F2). Subsequent visits: login → dashboard. Access token expires silently in the background; a refresh call renews it without interrupting the user.
- **Frontend:** Login/register forms with inline validation (email format, password length ≥ 8). Auth state held in a React context/Zustand store; Axios/fetch interceptor auto-attaches the access token and retries once on 401 after a silent refresh.
- **Backend:** `passlib[bcrypt]` for password hashing, `python-jose` for JWT signing. Access token TTL 15 minutes, refresh token TTL 7 days, refresh token stored httpOnly + `Secure` + `SameSite=Lax`.
- **API:** `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`.
- **Database:** `users` table (see §8).
- **Edge Cases:** duplicate email on register; expired refresh token (force re-login); concurrent refresh requests (idempotent — return same new pair or reject race losers gracefully).
- **Errors:** 409 on duplicate email, 401 on bad credentials or expired/invalid token, 422 on validation failure.
- **Security:** rate-limit `/auth/login` (see §11); never log passwords or tokens; refresh tokens are single-use and rotated on every refresh (old one invalidated).

---

#### F2 — Portfolio Ingestion

- **What:** Three entry paths — instant demo portfolio, CSV upload with format normalization, manual entry form.
- **Why:** Zero-friction demo path is required for the pitch; CSV import is the realistic "bring your real portfolio" path without broker OAuth complexity.
- **User Flow:** Onboarding screen shows three buttons. Demo → instant dashboard. CSV → upload → column-mapping confirmation screen ("we detected 'Qty' as quantity — correct?") → import → dashboard. Manual → symbol autocomplete + quantity + avg price rows → submit → dashboard.
- **Frontend:** File drop-zone with client-side size/type check; a mapping-confirmation table pre-filled with best-guess column matches, editable via dropdowns before final submit.
- **Backend:** CSV parsed with `pandas`; header names fuzzy-matched (case-insensitive substring + Levenshtein distance fallback) against canonical fields (`symbol`, `quantity`, `average_price`, `currency`); confirmed mapping applied; each row validated (symbol exists via a cached symbol master list, quantity/price > 0, no duplicate symbols — duplicates are merged by weighted-average cost).
- **API:** `POST /portfolios/demo`, `POST /portfolios/import/preview` (returns detected mapping for confirmation), `POST /portfolios/import/confirm`, `POST /portfolios/holdings` (manual add), `GET /portfolios/{id}`.
- **Database:** `portfolios`, `holdings` tables.
- **Edge Cases:** empty CSV; CSV with unrecognized broker format (fall back to manual column mapping, never silently guess wrong); symbol not found in market data provider (flagged, excluded, reported to user); portfolio with zero holdings after import.
- **Errors:** 400 on unparseable file, 422 on validation failures with a per-row error list, 413 on oversized file.
- **Security:** file size capped (e.g. 2 MB); file type restricted to `.csv`; holdings are always written scoped to `request.user.id`, checked at the query layer, not just the route layer.

---

#### F3 — Symbol Reverse Index & Dynamic Subscription

- **What:** A Redis-backed mapping of `symbol → set of portfolio_ids currently holding it`, and a `symbol → subscriber_count` counter that drives whether the ingestion worker is subscribed to that symbol on Finnhub.
- **Why:** A tick must only trigger recomputation for portfolios that actually hold that symbol, and the ingestion worker must not subscribe to symbols nobody holds.
- **User Flow:** Invisible to the user — triggered automatically whenever holdings are added/removed/imported.
- **Frontend:** N/A (backend-internal).
- **Backend:** On holding create/delete: update `reverse_index:{symbol}` (Redis set) and `subscriber_count:{symbol}` (Redis integer, `INCR`/`DECR`). On transition 0→1, publish a "subscribe" command to the ingestion worker's control channel; on transition 1→0, publish "unsubscribe."
- **API:** No direct external API — internal service function called from F2's write paths.
- **Database:** Reverse index lives primarily in Redis; a `symbol_subscriptions` Postgres table is kept as an audit/recovery source of truth (rebuildable Redis index on worker restart).
- **Edge Cases:** worker restart (rebuild Redis index from Postgres on boot); symbol delisted (removed from all portfolios' index, subscription dropped).
- **Errors:** log and continue if a Finnhub subscribe/unsubscribe call fails — the reverse index update itself must never fail the user-facing holdings request.
- **Security:** N/A (internal).

---

#### F4 — Real-Time Tick Ingestion & Fast Path

- **What:** A persistent Finnhub WebSocket connection ingesting trade ticks, publishing them to a Redis Stream, consumed by a fast-path worker that updates price/P&L only, fanned out to browsers over WebSocket via Redis pub/sub.
- **Why:** This is the architectural core of the "continuous, not manual" value proposition.
- **User Flow:** User has the dashboard open; portfolio value and P&L update live with no user action.
- **Frontend:** One WebSocket connection per session; on load, sends `{"subscribe": portfolio_id}`; listens for `price_update` and `risk_update` messages; updates React state directly (no polling).
- **Backend:** `ingestion_worker` (standalone process) holds the Finnhub WS connection, publishes raw ticks to Redis Stream `market:ticks`. `fast_path_worker` (standalone process, Redis Streams consumer group) reads `market:ticks`, looks up affected portfolios via F3's reverse index, recomputes `portfolio_value` and `daily_pnl` (a weighted sum — O(number of holdings), cheap), writes to `risk_state:{portfolio_id}` in Redis, publishes to `risk_updates:{portfolio_id}` pub/sub channel. `ws_server` (part of the FastAPI app, or a dedicated process) holds browser connections, subscribes to each connected portfolio's pub/sub channel, forwards messages to the correct socket only.
- **API:** `WS /ws` (upgrade endpoint; auth via short-lived ticket token passed as a query param, exchanged for a validated session).
- **Database:** No writes on the fast path — Redis only, by design, for latency.
- **Edge Cases:** tick for a symbol with no active subscribers (reverse index empty — no-op); duplicate tick delivery (idempotency key = `(symbol, trade_timestamp)`, last-write-wins on out-of-order arrival by comparing timestamps before overwrite); WebSocket disconnect/reconnect (client resubscribes; server has no session state that survives beyond the pub/sub subscription itself).
- **Errors:** Finnhub WS disconnect triggers automatic reconnect with exponential backoff in the ingestion worker; browser WS disconnect is a normal, expected event, not logged as an error.
- **Security:** the browser-facing WS ticket token is short-lived (60s) and single-use, preventing token replay from a leaked URL; portfolio subscription is validated against the authenticated user's ownership before the server allows a channel subscription.

---

#### F5 — Slow-Path Risk Recompute

- **What:** A debounced, batched recomputation of VaR, CVaR, volatility, max drawdown, Sharpe ratio, and per-asset risk contribution, running on a bounded cadence (not every tick).
- **Why:** These calculations are covariance-matrix-dependent and computationally heavier; recomputing on every tick would not improve accuracy meaningfully and would waste compute.
- **User Flow:** Same dashboard screen as F4 — the risk-metric section of the UI updates every few seconds rather than instantly, visibly distinct from the instant price ticker.
- **Frontend:** Same WebSocket channel; a separate `risk_update` message type updates the risk-metrics panel with a subtle "last updated Xs ago" indicator.
- **Backend:** `slow_path_worker` consumes the same `market:ticks` stream via a separate consumer group, but instead of acting per-tick, batches ticks into a rolling window (e.g. every 2 seconds or every 20 ticks, whichever comes first) per affected portfolio, then runs the full quant engine (see F6) once per window using the latest price snapshot. Result written to `risk_state:{portfolio_id}` (merged with F4's fields) and published to the same pub/sub channel.
- **API:** N/A (internal worker), surfaced via the same WS channel as F4 and via `GET /portfolios/{id}/risk` for initial page load / non-WS clients (e.g. the Slack bot, F17).
- **Database:** Periodic snapshots written to `risk_snapshots` (append-only, for the historical/audit trail and for F16's replay comparisons) — not on every recompute, but on a coarser interval (e.g. every 5 minutes) to avoid table bloat.
- **Edge Cases:** batching window with zero portfolios affected (skip); a portfolio with insufficient price history for covariance estimation (fall back to a flat "insufficient data" state, shown explicitly in the UI rather than a silently wrong number).
- **Errors:** a computation exception for one portfolio must not crash the worker loop for others — wrap per-portfolio computation in isolated try/except with structured logging.
- **Security:** N/A beyond standard data-ownership checks on the REST fallback endpoint.

---

#### F6 — Ledoit-Wolf Covariance Shrinkage

- **What:** Replace the raw sample covariance matrix with a Ledoit-Wolf shrinkage estimate before it feeds VaR, Monte Carlo correlation structure, and risk contribution.
- **Why:** With a small number of historical observations relative to assets, the raw sample covariance matrix's most extreme entries are dominated by estimation noise, which then gets amplified by any downstream optimization or risk decomposition. Shrinkage produces a better-conditioned, more stable estimate with no manual tuning.
- **User Flow:** Invisible — improves the reliability of every downstream risk number.
- **Frontend:** N/A directly; documented in the "Methodology" info tooltip next to the risk panel.
- **Backend:** `sklearn.covariance.LedoitWolf().fit(returns_matrix).covariance_` used everywhere a covariance matrix is required.
- **API:** N/A (internal to the quant engine module).
- **Database:** N/A (computed on demand from cached historical returns, not persisted as a matrix).
- **Edge Cases:** fewer than ~20 historical return observations (below this, flag "insufficient data for reliable risk estimate" rather than returning a shrinkage estimate on too little data).
- **Errors:** numerical instability (e.g. singular matrix pre-shrinkage) — Ledoit-Wolf's whole purpose is to prevent this, but guard with a fallback to a diagonal covariance matrix if fitting still fails.
- **Security:** N/A.

---

#### F7 — GARCH(1,1) Volatility Modeling

- **What:** Per-asset conditional volatility estimated via a GARCH(1,1) model, refit on a scheduled cadence (not per tick), feeding Monte Carlo's per-step volatility instead of a flat historical standard deviation.
- **Why:** Volatility clusters in real markets (calm periods, then bursts); a constant-volatility assumption materially understates risk during and after a volatility spike.
- **User Flow:** Invisible directly, but drives more realistic Monte Carlo/EVT outputs.
- **Frontend:** N/A directly.
- **Backend:** `garch_worker` (scheduled, e.g. every 15 minutes, or triggered on a significant new-data event) refits `arch.arch_model(returns, vol='Garch', p=1, q=1)` per held symbol, writes the latest conditional volatility estimate to `symbol_volatility:{symbol}` in Redis.
- **API:** N/A (internal); surfaced indirectly through Monte Carlo/EVT results.
- **Database:** Latest fitted parameters optionally persisted to `garch_fits` for audit/debugging, not required for runtime.
- **Edge Cases:** insufficient history to fit (fewer than ~100 return observations recommended) — fall back to simple historical standard deviation with a "using historical volatility" flag.
- **Errors:** fit non-convergence — catch and fall back per the above; never crash the worker.
- **Security:** N/A.

---

#### F8 — Monte Carlo Simulation

- **What:** A user-triggered simulation (horizon: 1D/7D/30D/90D; paths: 10K/50K/100K) using GBM per asset with Cholesky-decomposed, Ledoit-Wolf-covariance-derived correlated shocks and GARCH-derived volatility, run as an async background job with live progress, using antithetic variates for variance reduction.
- **Why:** This is the platform's headline quantitative feature and the basis for the EVT comparison (F9) and decision engine (F14).
- **User Flow:** User picks horizon + path count on the Simulation panel → clicks Run → sees a live progress bar → sees final distribution (probability of profit/loss, expected P&L, 95% range).
- **Frontend:** Form + progress bar driven by WS `simulation_progress` messages; results rendered as a histogram/range chart (Recharts).
- **Backend:** `POST /simulations` creates a DB row (`status=pending`) and enqueues an `arq` job; the worker runs the simulation in NumPy-vectorized batches (not a Python loop per path), publishing progress every N batches to `simulation_progress:{job_id}`; on completion, writes results to the `simulations` row and publishes a final `simulation_complete` message.
- **API:** `POST /simulations` (create/enqueue), `GET /simulations/{id}` (poll fallback for non-WS clients), `WS` progress via the existing portfolio channel.
- **Database:** `simulations` table (params, status, results JSON, timestamps).
- **Edge Cases:** user requests 100K paths on a portfolio with 1 asset (still valid, just a degenerate covariance case — single-variance GBM); user closes tab mid-simulation (job continues server-side; result available on next load via `GET /simulations/{id}`).
- **Errors:** job failure (e.g. OOM on 100K paths with too many assets) caught, status set to `failed`, user-facing message shown; never leave a job stuck in `pending` — implement a job timeout.
- **Security:** rate-limit simulation creation per user (e.g. max 1 concurrent + 10/hour) to prevent resource exhaustion.

---

#### F9 — EVT / Peaks-Over-Threshold Tail Risk

- **What:** A second, independent tail-risk estimate — fit a Generalized Pareto Distribution to the worst historical daily portfolio returns beyond a chosen threshold (POT method), and derive VaR/CVaR from that fit, shown alongside the Monte Carlo estimate.
- **Why:** Monte Carlo under GBM assumes approximately log-normal returns, which understates the frequency and severity of extreme moves. EVT is designed specifically to model the tail without assuming a shape for the whole distribution.
- **User Flow:** Appears on the same Simulation panel as F8, as a second row: "Monte Carlo CVaR: ₹48K · EVT tail estimate: ₹71K."
- **Frontend:** Simple side-by-side stat display, no new screen.
- **Backend:** `scipy.stats.genpareto.fit()` on exceedances over a threshold (e.g. the 90th/95th percentile of historical losses) from the portfolio's historical return series; VaR/CVaR derived analytically from the fitted GPD parameters.
- **API:** Included in the same simulation result payload as F8 (`GET /simulations/{id}` response includes both `monte_carlo` and `evt` sub-objects) — computed synchronously alongside the Monte Carlo job since it is far cheaper.
- **Database:** Stored alongside the Monte Carlo result in the same `simulations.results` JSON field.
- **Edge Cases:** too few exceedances above the threshold for a stable GPD fit (lower the threshold percentile automatically, or flag "insufficient tail data").
- **Errors:** fit failure falls back to reporting only the Monte Carlo estimate with an explicit "EVT estimate unavailable" note, never a silently wrong number.
- **Security:** N/A.

---

#### F10 — Risk Budget & Breach Detection

- **What:** User-configured maximum acceptable CVaR (the "risk budget"); continuous evaluation of `utilization = current_CVaR / budget`, mapped to SAFE (0–60%) / WATCH (60–80%) / HIGH (80–100%) / BREACH (>100%); a state-change (not every recompute) triggers a push alert.
- **Why:** This converts a static number into the platform's core "proactive" behavior.
- **User Flow:** User sets a budget once during onboarding (with a sensible default pre-filled, editable in settings). Any time the slow-path recompute (F5) results in a *state transition* (e.g. SAFE→WATCH), a real-time alert fires.
- **Frontend:** A persistent progress-bar-style utilization indicator on the dashboard, colored by state; a toast/banner appears on state transition; clicking it opens the AI explain panel (F15) with the alert's context pre-loaded.
- **Backend:** State thresholds are configurable per-user (stored, defaulting to the documented values); the slow-path worker (F5) computes the new state after each recompute and compares to the previously stored state — only a *change* publishes an `alert` message (never fires the same alert repeatedly for an unchanged state).
- **API:** `PUT /portfolios/{id}/risk-budget`, `GET /alerts?portfolio_id=`.
- **Database:** `risk_budgets` (one per portfolio), `alerts` (append-only log of fired alerts, for history and for the historical replay comparison in F16).
- **Edge Cases:** no budget configured yet (dashboard shows a prompt to set one, no alerts fire); rapid oscillation across a threshold (add a small hysteresis band or a minimum time-between-alerts to avoid alert spam — document this as a configurable guard).
- **Errors:** N/A beyond standard.
- **Security:** budget values are scoped to the owning user only.

---

#### F11 — Hidden Correlation / Concentration Detector

- **What:** Per-asset **risk contribution** (`RC_i = w_i · MCR_i` where `MCR_i = (Σw)_i / σ_p`), shown next to plain allocation weight, plus a correlation-cluster flag when two or more held assets exceed a correlation threshold (e.g. 0.7).
- **Why:** Distinguishes "I own 18% of NVDA" from "NVDA is responsible for 24% of my portfolio's risk" — the single most differentiated, demo-worthy quant feature in the product.
- **User Flow:** Displayed as a horizontal bar list on the dashboard ("Technology 42%, NVDA 14%, ..."); a warning banner appears when a correlation cluster is detected ("⚠ Hidden Semiconductor Concentration: NVDA/AMD/AVGO correlation 0.84").
- **Frontend:** Bar chart / list component; a dismissible warning card for detected clusters.
- **Backend:** Computed as part of the slow-path recompute (F5), using the Ledoit-Wolf covariance matrix (F6); cluster detection via simple thresholding on pairwise correlation extracted from the same covariance matrix.
- **API:** Included in `GET /portfolios/{id}/risk` response.
- **Database:** Included in the `risk_snapshots` JSON payload, not a separate table.
- **Edge Cases:** single-asset portfolio (no meaningful correlation — section hidden, not shown as an error).
- **Errors:** N/A beyond the shared quant-engine error handling in F5.
- **Security:** N/A.

---

#### F12 — HMM Market Regime Detection

- **What:** A background worker that fits a 2-state (calm/stressed) Hidden Markov Model on a rolling window of market returns/volatility and reports the current **filtered (forward) probability** of each regime — not a smoothed, whole-history Viterbi label — since the product needs "what's happening right now," not a retrospective label.
- **Why:** Gives risk-budget alerting a smoother, earlier signal than a hard VaR-threshold breach alone, and is a visible, demo-worthy "the system understands market context" feature.
- **User Flow:** A small dashboard indicator: "Market regime: 78% stressed." Feeds into F10's alert logic as an additional signal a user can optionally weight.
- **Frontend:** Small badge/indicator component with a tooltip explaining the number.
- **Backend:** `regime_worker` (scheduled, e.g. every 5 minutes) fits `hmmlearn.hmm.GaussianHMM(n_components=2)` on the relevant market index/benchmark return series (not per-portfolio — one shared regime signal reused across all portfolios), computes the forward probability at the latest timestep, writes to `market_regime` (a single shared Redis key + Postgres history row).
- **API:** `GET /market/regime`.
- **Database:** `regime_states` (timestamp, calm_probability, stressed_probability).
- **Edge Cases:** model relabeling between refits (HMM component labels are not guaranteed stable across independent fits — resolve by always labeling the state with the *higher* variance as "stressed" post-fit, never relying on raw component index).
- **Errors:** fit failure — keep serving the last known-good regime state with a staleness flag rather than blocking.
- **Security:** N/A (shared, non-user-specific data).

---

#### F13 — Kupiec Backtest (Model Validation)

- **What:** A statistical test comparing the *claimed* VaR breach rate (e.g. "5% of days should exceed 95% VaR") against the *actual* breach rate observed over the historical replay window (F16), reported as a pass/fail with the underlying counts.
- **Why:** Proves the risk model is honest about its own accuracy — a genuinely industry-standard practice (regulators require this class of test for real risk models) that almost no student project includes.
- **User Flow:** Shown as a badge on the Historical Replay screen: "Model backtest: PASSED — 4.8% actual breach rate vs. 5% predicted."
- **Frontend:** Simple badge/stat component, colored green/red by pass/fail.
- **Backend:** Standard Kupiec proportion-of-failures likelihood-ratio test computed over the replay's daily VaR-vs-actual-loss comparison; implemented directly (no external library required — it's a closed-form log-likelihood-ratio statistic compared against a chi-squared critical value).
- **API:** Included in the `GET /replays/{id}` response.
- **Database:** Stored in `backtest_results`, linked to the replay run that produced it.
- **Edge Cases:** too few days in the replay window for a statistically meaningful test (flag "insufficient sample size" rather than a misleading pass/fail).
- **Errors:** N/A beyond standard.
- **Security:** N/A.

---

#### F14 — Decision Engine

- **What:** On a risk-budget breach (F10), automatically evaluates 2–3 candidate actions (do nothing / reduce the largest risk-contributing position by a configurable amount / increase cash allocation) against expected return, CVaR, and P(loss > threshold) — reusing the Monte Carlo engine (F8) for each candidate — and ranks them.
- **Why:** This is what turns the product from "a dashboard that shows numbers" into "a system that recommends what to do," the second most differentiated feature after F11.
- **User Flow:** Appears automatically below a breach alert; three cards side by side; user can dismiss or manually act (outside the system) — no execution happens.
- **Frontend:** Card-comparison component (already-designed pattern in the app's component library — see §4).
- **Backend:** `decision_engine_worker` triggered on a breach state transition (same signal as F10); constructs 2–3 hypothetical portfolio weight vectors, runs a (smaller, e.g. 10K-path) Monte Carlo for each synchronously since these need to complete quickly to accompany the alert, ranks by a simple objective (e.g. expected return − λ·CVaR, λ configurable).
- **API:** Included in the `alert` payload published over WS; also `GET /portfolios/{id}/decisions/latest`.
- **Database:** `decisions` table linked to the triggering `alerts` row.
- **Edge Cases:** breach on a portfolio with no clear "largest risk contributor" (e.g. already well diversified) — the "reduce position" candidate is simply omitted, only "do nothing" and "increase cash" are shown.
- **Errors:** if the candidate-evaluation Monte Carlo run fails, fall back to a simpler deterministic estimate (mean-variance approximation) rather than blocking the alert from displaying.
- **Security:** N/A — advisory only, no execution path exists in the system at all (not just disabled).

---

#### F15 — AI Risk Analyst (Explain + What-If)

- **What:** A LangGraph agent, backed by the Claude API, with exactly two tool-calling capabilities: (1) explain a given risk state in plain language using already-computed numbers, (2) parse a natural-language "what if" question into a structured scenario object, send it to the quant engine, and narrate the real result back.
- **Why:** Makes the quantitative output accessible, while the strict tool-calling boundary prevents financial hallucination — the architecture point most worth defending in an interview.
- **User Flow:** A chat-style panel pre-filled with the auto-generated explanation of the alert the user clicked; a text input for follow-up "what if" questions; suggested-question chips for common scenarios.
- **Frontend:** Chat UI component (message list + input), rendering both the user's question and the AI's narrated response; numeric results are rendered from the structured API response, not parsed out of the AI's text.
- **Backend:** `POST /ai/explain` (given a `risk_snapshot_id` or `alert_id`, returns computed numbers + AI narration); `POST /ai/what-if` (given free text, the LangGraph agent's first tool call parses it into `{"symbol": "NVDA", "shock_pct": -0.20}` structured JSON, which is sent to a **deterministic** scenario-evaluation function in the quant engine — never generated by the LLM — and the result is passed back into the agent only for narration).
- **API:** `POST /ai/explain`, `POST /ai/what-if`.
- **Database:** `ai_conversations` (message history per portfolio, for context continuity across a session).
- **Edge Cases:** ambiguous what-if input ("what if the market crashes") — the agent should ask a clarifying follow-up rather than guessing a magnitude, or apply a documented default (e.g. "market" maps to a diversified −10% shock across all holdings) and state the assumption explicitly in its narration.
- **Errors:** LLM API failure/timeout — the panel shows the raw computed numbers with "AI explanation unavailable" rather than blocking the numeric result the user actually needs.
- **Security:** the LLM must never receive another user's data; scenario evaluation always re-validates portfolio ownership before running; no user-supplied text is ever executed as code — the parsed scenario is a fixed, typed schema (Pydantic model), rejected if it doesn't validate.

---

#### F16 — Historical Replay

- **What:** Replays the checked-in historical dataset (A10) day-by-day through the *current* portfolio's holdings and the *current* quant engine, plotting the resulting risk score/CVaR over time and marking the exact day the risk-budget threshold would have been breached, compared against the actual subsequent drawdown.
- **Why:** The single most convincing demo moment — it proves the system works predictively, not just computationally.
- **User Flow:** User selects a historical period from a dropdown (e.g. "2022 rate shock") → clicks "Replay" → a day-by-day animated chart plays, highlighting the breach day → the Kupiec backtest badge (F13) appears at the end.
- **Frontend:** Animated line chart (Recharts) with a marker annotation on the breach day; a "play/pause/scrub" control.
- **Backend:** `POST /replays` (async job, similar pattern to F8): iterates the historical dataset day by day, applies the current portfolio's holdings to each day's prices, runs the full quant engine (F5, F6) per day, records the daily risk state and any threshold-crossing, and finally computes the Kupiec test (F13) over the whole run.
- **API:** `POST /replays`, `GET /replays/{id}`.
- **Database:** `replays` (params, status), `replay_daily_states` (one row per simulated day), `backtest_results` (F13, linked).
- **Edge Cases:** portfolio holds a symbol not present in the checked-in historical dataset (excluded from the replay with an explicit note, not silently dropped).
- **Errors:** same async-job failure handling pattern as F8.
- **Security:** N/A beyond standard ownership checks.

---

#### F17 — Slack Bot (Second Client)

- **What:** A Slack app (Slack Bolt SDK) exposing `/risklens status`, `/risklens whatif <symbol> <pct>`, and `/risklens alerts` slash commands, calling the **same REST endpoints** as the web frontend.
- **Why:** Proves the backend is a genuine, reusable API rather than logic embedded in the frontend — real multi-client architecture value at low build cost.
- **User Flow:** User types a slash command in Slack → bot calls the RiskLens API using a linked account token → formats the JSON response as a Slack message block.
- **Frontend:** N/A (Slack is the client).
- **Backend:** A thin, separate service (`slack_bot`) using Slack Bolt, holding a stored API token per Slack user (linked once via an `/risklens login` flow that issues a long-lived API token, distinct from the browser's JWT flow, scoped read/what-if only — no write/import capability from Slack for MVP).
- **API:** Reuses `GET /portfolios/{id}/risk`, `POST /ai/what-if`, `GET /alerts`; adds one new endpoint `POST /auth/api-tokens` (issue a long-lived, revocable token for non-browser clients).
- **Database:** `api_tokens` table (user_id, token_hash, scopes, created_at, revoked_at).
- **Edge Cases:** unlinked Slack account (bot responds with a link-account prompt instead of an error stack).
- **Errors:** API downtime — bot responds with a friendly "RiskLens is temporarily unavailable" rather than a raw error.
- **Security:** API tokens are scoped (read + what-if only, never import/write), hashed at rest exactly like passwords, and individually revocable.

---

#### F18 — Frontend Dashboard (All Screens)

Covered fully in §4 (UI/UX Design System) — screens: Onboarding, Live Dashboard, Risk Event/Alert, AI Explain/What-If Panel, Monte Carlo/EVT Panel, Decision Engine Panel, Historical Replay.

---

### 3.3 Non-Functional Requirements

- **Real-time behavior:** price/P&L updates within ~1s of a tick; full risk recompute within the batching window (2–5s); Monte Carlo/replay run asynchronously with progress, never blocking the request thread.
- **Background processing:** ingestion, fast-path, slow-path, GARCH refit, HMM regime, Monte Carlo jobs, decision-engine evaluation, and replay jobs are all separate worker processes — never inline in an API request handler.
- **Analytics:** out of scope for MVP; the append-only `alerts` and `risk_snapshots` tables are structured so a future analytics/reporting feature can be built on top without a schema change.
- **Admin functionality:** out of scope for MVP; documented as a future phase (a `role` column already exists on `users` — see §8 — to make this a low-friction addition later).

---

## 4. UI/UX Design System

The UI must read as a deliberate, restrained financial product — closer to **Stripe Dashboard, Linear, and Vercel** than a generic "AI startup" template. No unexplained gradients, no glassmorphism, no purple/blue AI-aesthetic defaults, no decorative animation.

### 4.1 Design Principles

1. **Numbers are the hero.** Typography and spacing exist to make numbers scannable at a glance — this is a data product, not a marketing page.
2. **Color carries meaning, not decoration.** Color is reserved for risk-state signaling (SAFE/WATCH/HIGH/BREACH) and semantic states (success/error). Nothing else uses saturated color.
3. **Motion is informational, not decorative.** Animation is used only to communicate a state change (a number ticking up, a progress bar filling, an alert sliding in) — never for its own sake.
4. **Density over whitespace-for-its-own-sake.** Financial dashboards reward information density; avoid oversized cards with one metric floating in a sea of padding.
5. **Consistency over novelty.** One card style, one table style, one modal style, reused everywhere.

### 4.2 Color System

Base neutral palette (used for ~90% of the UI):

```
--color-bg: #0B0D10            /* app background, dark mode default */
--color-bg-elevated: #14171B   /* cards, panels */
--color-border: #23272D
--color-text-primary: #E6E8EB
--color-text-secondary: #9AA0A6
--color-text-tertiary: #6B7178
```

Semantic / risk-state colors (used *only* for their designated meaning, nowhere else):

```
--color-safe: #2FA96B     /* risk state: SAFE */
--color-watch: #D9A441    /* risk state: WATCH */
--color-high: #E08A3C     /* risk state: HIGH */
--color-breach: #D9483D   /* risk state: BREACH / error */
--color-accent: #3E7BFA   /* interactive elements only: links, primary buttons */
```

Light mode uses the same semantic mapping against a light neutral scale (`#FFFFFF` / `#F5F6F7` / `#111417` text) — implemented via CSS custom properties so no component hardcodes a literal hex value.

### 4.3 Typography

- **Font:** Inter (UI text), JetBrains Mono or IBM Plex Mono (all numeric values — prices, percentages, currency figures always render in a monospaced numeral style so figures align in columns).
- **Scale:** 12 / 13 / 14 (body) / 16 / 20 / 24 / 32px, no arbitrary in-between sizes.
- **Weight:** 400 body, 500 for labels, 600 for headline metrics — never 700+/black weights, which read as "marketing," not "terminal."

### 4.4 Spacing & Grid

- 4px base unit; spacing scale: 4, 8, 12, 16, 24, 32, 48, 64.
- 12-column responsive grid, 24px gutters on desktop, 16px on mobile.
- Dashboard content max-width 1440px, centered, with the sidebar fixed at 240px (collapsible to 64px icon rail).

### 4.5 Component Design

- **Buttons:** three variants only — primary (filled, accent color), secondary (outline), ghost (text only). No gradient buttons, no oversized rounded pill shapes — 6px border radius standard.
- **Inputs:** single-line height 36px, 1px border, focus state = accent-colored 2px ring, never a glow/shadow effect.
- **Forms:** label above input, inline validation message below in `--color-breach`, never a toast for field-level validation.
- **Tables:** dense rows (36–40px height), right-aligned numeric columns, sticky header on scroll, zebra-striping avoided (use a subtle border instead — cleaner for a dark theme).
- **Cards:** 8px radius, 1px border (not shadow-based elevation — shadows are avoided per the anti-"AI template" requirement), consistent 16/24px internal padding.
- **Modals:** centered, max-width 480px for forms / 720px for data-heavy content (e.g. CSV mapping confirmation), dismiss via explicit button or Escape, never click-outside-to-dismiss for destructive flows.
- **Dropdowns:** native-feeling, 6px radius, matches input styling exactly.
- **Navigation / Sidebar:** icon + label, active item indicated by a left accent-colored bar (2px) plus a subtly elevated background — not a filled pill.
- **Topbar:** portfolio switcher (if multiple portfolios exist) + user menu + connection-status indicator (small dot: green connected / gray reconnecting).
- **Tabs:** underline style, not filled/pill style — matches the "Linear" reference more than a "SaaS template" reference.
- **Toasts:** bottom-right, auto-dismiss 5s except BREACH-level alerts, which persist until manually dismissed.
- **Alerts (risk banners):** left-accent-bar style (colored by risk state), not full-background-colored — keeps the dark theme readable.
- **Tooltips:** small, dark, appear on hover after a 300ms delay, used for methodology explanations (e.g. "what is CVaR").
- **Loading states:** skeleton screens matching the exact shape of the real content (never a centered spinner for a whole page) for the dashboard; a determinate progress bar (not a spinner) for Monte Carlo/replay jobs, since real progress is available.
- **Empty states:** short explanatory text + a single clear primary action (e.g. no portfolio yet → "Try demo" / "Import CSV" buttons, not just blank space).
- **Error states:** inline, specific, actionable ("Couldn't parse this CSV — check that it has a quantity column" beats "Something went wrong").
- **Responsive behavior:** sidebar collapses to a bottom tab bar under 768px; the risk-metrics grid reflows from 4 columns → 2 → 1; the AI panel becomes a full-screen sheet on mobile rather than a side panel.
- **Accessibility:** all interactive elements keyboard-reachable and focus-visible; color is never the sole signal (risk-state badges always carry a text label, not just color); minimum 4.5:1 contrast ratio enforced by the token palette above.
- **Dark/Light mode:** dark is the default (financial-terminal convention); light mode is a full token swap, not a separate stylesheet.
- **Micro-interactions:** a number that updates plays a brief (150ms) color flash (green/red tint) to draw the eye without being distracting; the risk-budget utilization bar animates its width change over 300ms ease-out.

### 4.6 Screen-by-Screen Specification

#### Screen: Onboarding
- **Purpose:** Get a portfolio into the system with zero friction.
- **Layout:** Centered card, three large action buttons stacked (Try Demo / Import CSV / Add Manually).
- **Components:** `ActionCard` × 3, `FileDropzone` (revealed on CSV selection), `ColumnMappingTable` (revealed after upload).
- **User actions:** click demo (instant redirect to dashboard); drag/select CSV → review mapping → confirm; or fill manual entry rows.
- **States:** empty (default) / uploading (progress) / mapping-review / error (bad file) / success (redirect).
- **Responsive:** buttons stack full-width on mobile.

#### Screen: Live Dashboard
- **Purpose:** Primary home screen — glanceable risk state plus live-updating numbers.
- **Layout (desktop, rough wireframe):**
```
┌────────────────────────────────────────────────────────┐
│ Sidebar │  Portfolio Value   Today's P&L   Regime Badge │
│         │  ──────────────────────────────────────────  │
│         │  Risk Score  |  VaR  |  CVaR  |  Budget Bar   │
│         │  ──────────────────────────────────────────  │
│         │  Risk Contribution (bar list)                │
│         │  ⚠ Concentration warning (if any)             │
│         │  ──────────────────────────────────────────  │
│         │  [Run Monte Carlo]   [Replay History]         │
└────────────────────────────────────────────────────────┘
```
- **Components:** `MetricCard`, `RiskBudgetBar`, `RiskContributionList`, `RegimeBadge`, `ConcentrationWarning`, `ConnectionStatusDot`.
- **User actions:** click any metric for a tooltip explanation; click a risk-contribution row to open the AI explain panel scoped to that asset.
- **States:** loading (skeleton), live (normal), stale (WS disconnected — numbers dim slightly, "reconnecting" shown), insufficient-data (new portfolio, not enough history yet).
- **Responsive:** metrics grid reflows to 2 then 1 column; sidebar becomes bottom nav.

#### Screen: Risk Event / Alert
- **Purpose:** Surface a state-change without requiring the user to be looking.
- **Layout:** Slide-in banner from the top of the dashboard, left-accent-bar colored by severity; expands on click to show the Decision Engine cards beneath it.
- **Components:** `AlertBanner`, `DecisionCard` × up to 3.
- **User actions:** click to expand/read AI explanation; dismiss; click a decision card to see its full metrics.
- **States:** collapsed / expanded / dismissed.

#### Screen: AI Explain / What-If Panel
- **Purpose:** Plain-language reasoning layer over computed numbers.
- **Layout:** Right-side sliding panel (full-screen sheet on mobile) — chat-style message list, text input pinned to bottom, suggested-question chips above the input.
- **Components:** `ChatMessageList`, `SuggestedChip`, `ChatInput`.
- **User actions:** type a what-if question; click a suggested chip; close panel.
- **States:** loading (typing indicator), error (AI unavailable — numeric fallback shown), normal.

#### Screen: Monte Carlo / EVT Panel
- **Purpose:** Run and visualize the simulation.
- **Layout:** Form (horizon, path count) → determinate progress bar → results (probability bars, range chart, EVT comparison row).
- **Components:** `SimulationForm`, `ProgressBar`, `DistributionChart`, `EVTComparisonRow`.
- **States:** idle / running (with live % progress) / complete / failed.

#### Screen: Historical Replay
- **Purpose:** The demo-closing proof-of-value screen.
- **Layout:** Period dropdown → play control → animated line chart with a breach-day marker → Kupiec backtest badge below the chart.
- **Components:** `ReplaySelector`, `ReplayChart`, `PlayScrubControl`, `BacktestBadge`.
- **States:** idle / running / complete.


---

## 5. Application Architecture

### 5.1 Overall Architecture

RiskLens is a **service-oriented monolith-of-workers**: one FastAPI application handles synchronous HTTP/WebSocket requests, and a small set of independently-deployable, independently-scalable background worker processes handle everything continuous or heavy. This is deliberately *not* a single-process monolith (background work would block/compete with request handling) and deliberately *not* a full microservices split (unnecessary network hops and deployment complexity for this scale) — it sits at the right point on that spectrum for a project this size while still demonstrating real separation of concerns.

```
                              ┌──────────────────┐
                              │   Next.js Web     │
                              └─────────┬─────────┘
                                        │ HTTPS + WSS
                              ┌─────────▼─────────┐
                              │   FastAPI (API +   │
                              │   WebSocket server)│
                              └─────────┬─────────┘
                                        │
                 ┌──────────────────────┼───────────────────────┐
                 ▼                      ▼                       ▼
          ┌─────────────┐       ┌─────────────┐         ┌─────────────┐
          │ PostgreSQL  │       │    Redis     │         │  Slack Bot  │
          │ (durable)   │◄─────►│ (cache, pub/ │◄───────►│  (separate  │
          └─────────────┘       │  sub, streams,│        │   process)  │
                                 │  arq queue)   │        └─────────────┘
                                 └──────┬───────┘
                 ┌──────────────────────┼────────────────────────────┐
                 ▼                      ▼                            ▼
        ┌────────────────┐   ┌──────────────────┐          ┌──────────────────┐
        │ Ingestion       │   │ Fast-Path Worker  │          │ Slow-Path Worker  │
        │ Worker (Finnhub │──►│ (price/PnL, every │          │ (VaR/CVaR/corr,   │
        │ WS → Redis      │   │ tick)             │          │ batched, debounced)│
        │ Stream)         │   └──────────────────┘          └──────────────────┘
        └────────────────┘
                 │                      ┌──────────────────┐   ┌──────────────────┐
                 │                      │ GARCH Worker      │   │ HMM Regime Worker │
                 │                      │ (scheduled refit) │   │ (scheduled refit) │
                 │                      └──────────────────┘   └──────────────────┘
                 │
                 │              ┌──────────────────┐   ┌──────────────────┐
                 └─────────────►│ arq Job Worker    │   │ Decision Engine   │
                                │ (Monte Carlo,      │   │ Worker (on breach) │
                                │  Historical Replay)│   └──────────────────┘
                                └──────────────────┘
```

### 5.2 Frontend Architecture

Next.js App Router, organized by route + a shared component library. Server Components used for static/initial-load content (e.g. onboarding), Client Components for anything WebSocket-driven or interactive (dashboard, AI panel). TanStack Query manages server-state caching for REST calls (simulations, replays); a thin custom hook (`useRiskSocket`) manages the single WebSocket connection and dispatches typed messages into React state.

### 5.3 Backend Architecture

FastAPI app organized by **domain module** (`auth`, `portfolios`, `risk`, `simulations`, `ai`, `alerts`, `replays`), each with its own `router.py`, `schemas.py` (Pydantic), `service.py` (business logic), and `models.py` (SQLAlchemy) — see §9 for the exact tree. The quant engine (`quant/`) is a standalone, framework-agnostic Python package with no FastAPI or database imports, so it can be unit-tested in isolation and reused identically by the API, the workers, and (in principle) a future CLI.

### 5.4 Database Architecture

PostgreSQL as the single source of durable truth. Redis is explicitly a **cache and messaging layer, not a database** — anything in Redis must be reconstructable from Postgres (the reverse index, the current risk state) except genuinely ephemeral data (WebSocket connection routing, job progress percentages).

### 5.5 API Architecture

A single REST + WebSocket API, versioned via an `/api/v1` prefix from day one (even though there is only one version at launch) so a breaking v2 change never requires a client rewrite. Internal worker-to-worker communication happens exclusively via Redis (Streams for data flow, pub/sub for fan-out, direct keys for state) — workers never call the FastAPI HTTP API to talk to each other.

### 5.6 Authentication & Authorization Architecture

JWT access tokens (stateless, verified via signature + expiry, no DB lookup on every request) plus a refresh token stored server-side (hashed, in `refresh_tokens` table) enabling revocation (logout-everywhere). Authorization is **row-level ownership**, enforced in the service layer (never trust a route-level check alone) — every query that touches `portfolios`, `holdings`, `alerts`, `simulations`, etc. is scoped by `WHERE user_id = :current_user_id` at the repository/service function, not only at the router's dependency-injection layer.

### 5.7 External Services

| Service | Purpose | Failure Handling |
|---|---|---|
| Finnhub WebSocket | Real-time trade ticks | Auto-reconnect with exponential backoff; on prolonged outage, dashboard shows "market data delayed" rather than freezing silently |
| Anthropic Claude API | AI explain/what-if narration | Timeout → return computed numbers without narration, explicit "AI unavailable" UI state |
| Slack API | Bot commands | Standard Slack Bolt retry/ack semantics; API downtime → bot returns a friendly unavailable message |

### 5.8 Background Jobs

See §5.1 diagram. Each worker is a separate `python -m app.workers.<name>` entrypoint, containerized separately (§6), independently restartable, independently scalable (e.g. running two `slow_path_worker` replicas behind the same Redis Streams consumer group is a configuration change, not a code change).

### 5.9 Caching

Redis caches: current risk state per portfolio (`risk_state:{id}`), symbol volatility (`symbol_volatility:{symbol}`), market regime (`market_regime`), the symbol→portfolio reverse index, and simulation job progress. Every cached key has a defined owner (exactly one worker writes it) to avoid write races, and a defined TTL or explicit-invalidation rule — nothing is cached indefinitely without a refresh path.

### 5.10 File Storage

CSV uploads are processed in-memory/transiently (never persisted to disk or object storage) — only the resulting normalized `holdings` rows are stored. This sidesteps file-storage infrastructure entirely for MVP and is a stronger privacy default. If original-file retention is ever required, the documented extension point is S3-compatible object storage (e.g. Cloudflare R2 or AWS S3) referenced by a `source_file_url` column added to `portfolios`.

### 5.11 Logging

Structured JSON logging (`structlog`) with a consistent schema (`timestamp, level, service, event, user_id?, portfolio_id?, request_id`) across the API and all workers, so a single request/event can be traced across process boundaries via `request_id` propagation. No secrets, tokens, or full request bodies containing sensitive data are ever logged.

### 5.12 Monitoring

MVP: Render's built-in service metrics (CPU/memory/uptime) plus a `/health` endpoint per service (API and each worker) checked by the platform's health-check mechanism. Documented upgrade path: Prometheus + Grafana or a hosted APM (e.g. Sentry for errors, already included — see below) once real user traffic exists.

### 5.13 Error Handling & Error Tracking

Sentry (free tier) integrated in both frontend and backend for unhandled exception capture with source maps / stack traces. All API errors return a consistent envelope: `{"error": {"code": "...", "message": "...", "details": {...}}}`, never a raw stack trace to the client.

### 5.14 Configuration Management

All configuration via environment variables, loaded through a single typed `Settings` object (`pydantic-settings`) per service — no scattered `os.environ.get()` calls. `.env.example` checked into the repo documents every required variable with a placeholder value; `.env` itself is gitignored.

### 5.15 Deployment Architecture

Local: Docker Compose runs all services (API, all workers, Postgres, Redis, and the frontend dev server) with one command. Production: each backend service (API + each worker) deployed as a separate Render service from the same monorepo using per-service Dockerfiles/build commands; managed Render Postgres and Redis; frontend deployed separately to Vercel, configured with the Render API's public URL as its API base URL environment variable.

---

## 6. Technology Stack

| Layer | Technology | Why | Alternative considered | Why not chosen |
|---|---|---|---|---|
| Frontend framework | Next.js 14 (App Router) | Best-in-class DX for a WebSocket+chart-heavy dashboard; zero-config Vercel deploy | Vite + React Router | Next.js's built-in routing/SSR conventions reduce boilerplate for this scope |
| Language (frontend) | TypeScript | Type safety across API contracts (shared types generated from Pydantic schemas) | Plain JavaScript | Loses compile-time safety on a data-heavy app where a wrong field name is easy to miss |
| Styling | Tailwind CSS | Enforces the token-based design system in §4 directly in markup, fast iteration | CSS Modules | More boilerplate for the same outcome at this scale |
| Server state | TanStack Query | Purpose-built caching/retry/loading-state handling for REST calls | Manual `useEffect` fetching | TanStack Query eliminates a whole class of stale-data and race-condition bugs |
| Client state | Zustand | Minimal boilerplate for the small amount of genuinely client-only state (auth, active portfolio, WS connection status) | Redux Toolkit | Overkill for this app's actual state surface |
| Charts | Recharts | Good React ergonomics, sufficient for line/bar/histogram needs here | D3 directly | Recharts covers 100% of this project's chart needs with far less code |
| Backend framework | FastAPI | Native async, automatic OpenAPI schema (powers the shared TS types), first-class WebSocket support, Pydantic validation | Django + DRF | Django's sync-first ORM and heavier conventions fight the async, worker-heavy architecture here |
| Language (backend) | Python 3.11+ | Required for the quant/ML stack (NumPy, SciPy, scikit-learn, arch, hmmlearn) — no serious alternative | Node.js backend | Would require reimplementing or shelling out to Python for every quant computation anyway |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Industry standard, explicit async support, mature migration tooling | Raw SQL / Tortoise ORM | SQLAlchemy's maturity and Alembic's migration ergonomics outweigh Tortoise's simplicity at this complexity level |
| DB driver | `asyncpg` | Fastest async Postgres driver, required for the async SQLAlchemy engine | `psycopg2` | Sync-only, would block the event loop |
| Database | PostgreSQL 15 | Relational integrity for financial/ownership data, mature, free-tier available on Render | MongoDB | No natural benefit from a document model here; relational integrity (foreign keys, transactions) matters more |
| Cache / event backbone | Redis 7 | Cache + pub/sub + Streams + `arq` broker, all from one piece of infrastructure (see Assumption A1) | Kafka | Operationally heavier than this project's scale justifies |
| Async job queue | `arq` | Asyncio-native, Redis-backed, minimal operational surface | Celery | Celery's sync-first design and separate broker/result-backend setup add complexity without added benefit here |
| Market data | Finnhub (WebSocket, free tier) | Real-time-with-delay data, real WebSocket, generous free tier for a demo (see Assumption A3) | Polygon.io | Paid; documented as the production upgrade path |
| Quant / stats | NumPy, Pandas, SciPy, scikit-learn | Standard numerical Python stack; `LedoitWolf` (scikit-learn), `genpareto` (SciPy) used directly | Custom implementations | Reinventing well-tested numerical routines is a correctness risk with no benefit |
| Volatility modeling | `arch` (Python GARCH library) | The standard, well-maintained Python GARCH implementation | Custom GARCH via SciPy optimizer | `arch` is purpose-built, tested, and avoids a hand-rolled MLE implementation |
| Regime detection | `hmmlearn` | Standard scikit-learn-compatible HMM implementation | `pomegranate` | `hmmlearn`'s API is simpler and sufficient for a 2-state Gaussian HMM |
| AI orchestration | LangGraph | Matches existing developer experience; clean tool-registration and state-graph model | Raw API tool-calling loop | LangGraph's graph abstraction makes the explain/what-if control flow explicit and testable |
| AI provider | Anthropic Claude API | Strong native tool-calling; matches prior project experience | OpenAI GPT-4o | Documented as a drop-in alternative behind the same LangGraph tool interface |
| Auth | Custom JWT (`python-jose`, `passlib[bcrypt]`) | Full understanding and control for a learning-focused, resume-facing project | Auth0 / Clerk | Adds an external dependency and cost for a capability that's genuinely simple to build correctly at this scale |
| Slack integration | Slack Bolt SDK (Python) | Official SDK, handles signature verification and slash-command routing | Raw webhook handling | Bolt eliminates a class of security/verification bugs |
| Testing (backend) | Pytest + `pytest-asyncio` + `httpx` (test client) | Standard, async-compatible | unittest | Pytest's fixtures and async support are a better fit |
| Testing (frontend) | Vitest + React Testing Library + Playwright (E2E) | Standard modern stack, fast, good Next.js support | Jest + Cypress | Vitest is faster and shares config with Vite-based tooling; Playwright has better modern browser/WebSocket testing support |
| CI/CD | GitHub Actions | Free for public/small private repos, native GitHub integration | GitLab CI / CircleCI | No reason to introduce a second platform when the repo is on GitHub |
| Deployment (backend) | Render | Multi-service (API + workers) + managed Postgres/Redis from one place, Docker-native | Railway / Fly.io | Comparable; Render chosen for its clean multi-service dashboard — documented as a decision point, either is a valid substitute with no architecture change |
| Deployment (frontend) | Vercel | Best-in-class Next.js hosting, zero-config | Render (static) | Vercel's Next.js-specific optimizations (edge caching, image optimization) are a strict improvement for this framework choice |
| Error tracking | Sentry | Free tier, both frontend and backend SDKs, source-map support | Rollbar | Sentry's free tier and ecosystem maturity are sufficient reasons |
| Containerization | Docker + Docker Compose | Required deliverable; standard | — | — |


---

## 7. API Design

All endpoints are prefixed `/api/v1`. Authenticated endpoints require `Authorization: Bearer <access_token>` unless noted. Responses follow a consistent envelope on error: `{"error": {"code", "message", "details"}}`; success responses return the resource directly (not double-wrapped).

### 7.1 Auth

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | No | Create account. Body: `{email, password}`. Returns `{access_token}`, sets refresh cookie. 201 on success, 409 if email exists, 422 on invalid input. |
| POST | `/auth/login` | No | Body: `{email, password}`. Same response shape as register. 200 / 401 on bad credentials. Rate-limited (5/min/IP). |
| POST | `/auth/refresh` | Refresh cookie | No body. Returns new `{access_token}`, rotates refresh cookie. 401 if refresh token invalid/expired/revoked. |
| POST | `/auth/logout` | Yes | Revokes the current refresh token. 204. |
| POST | `/auth/api-tokens` | Yes | Body: `{scopes: ["read","whatif"]}`. Issues a long-lived token for the Slack bot (F17). Returns the raw token once (never retrievable again, only its hash is stored). |

### 7.2 Portfolios

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/portfolios/demo` | Yes | Seeds and returns a demo portfolio for the current user. |
| POST | `/portfolios/import/preview` | Yes | Multipart CSV upload. Returns detected column mapping + parsed row preview (no DB write yet). |
| POST | `/portfolios/import/confirm` | Yes | Body: confirmed mapping + rows (from the preview step). Writes portfolio + holdings. 201. Per-row validation errors returned as a `details.rows` array on 422. |
| POST | `/portfolios/{id}/holdings` | Yes | Manual add. Body: `{symbol, quantity, average_price, currency}`. |
| DELETE | `/portfolios/{id}/holdings/{holding_id}` | Yes | Remove a holding; triggers reverse-index update (F3). |
| GET | `/portfolios/{id}` | Yes | Portfolio summary + holdings list. |
| GET | `/portfolios/{id}/risk` | Yes | Current cached risk state (F5, F11) — used for initial page load and by the Slack bot. |
| PUT | `/portfolios/{id}/risk-budget` | Yes | Body: `{max_cvar, currency}`. Sets/updates the risk budget (F10). |

### 7.3 Simulations & Replays

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/simulations` | Yes | Body: `{portfolio_id, horizon, num_paths}`. Enqueues a Monte Carlo job (F8/F9). Returns `{id, status: "pending"}`. 202. Rate-limited (10/hour/user, 1 concurrent). |
| GET | `/simulations/{id}` | Yes | Poll/fetch result. Includes both `monte_carlo` and `evt` sub-objects. |
| POST | `/replays` | Yes | Body: `{portfolio_id, period}`. Enqueues a historical replay job (F16). |
| GET | `/replays/{id}` | Yes | Fetch replay result, including the Kupiec backtest (F13). |

### 7.4 Alerts & Decisions

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/alerts` | Yes | Query param `portfolio_id`. Paginated (cursor-based), newest first. |
| GET | `/portfolios/{id}/decisions/latest` | Yes | Latest decision-engine ranking (F14), if any. |

### 7.5 AI

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/ai/explain` | Yes | Body: `{portfolio_id, alert_id?}`. Returns computed numbers + AI narration. |
| POST | `/ai/what-if` | Yes | Body: `{portfolio_id, question}`. Parses → evaluates → narrates. Returns the structured scenario used, the quant result, and the narration — never narration alone, so the frontend can always render real numbers even if narration fails. |

### 7.6 Market (shared, non-user-scoped)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/market/regime` | Yes | Current HMM regime state (F12). |
| GET | `/market/symbols?query=` | Yes | Symbol autocomplete for manual entry (F2), backed by a cached local symbol master list, not a live Finnhub call per keystroke. |

### 7.7 WebSocket

`WS /ws?ticket={short_lived_ticket}` — the ticket is obtained via `POST /ws/ticket` (authenticated, returns a 60-second single-use token) to avoid putting a long-lived JWT in a URL/query string. Client sends `{"action": "subscribe", "portfolio_id": "..."}` after connecting; server validates ownership before subscribing the socket to that portfolio's Redis pub/sub channel. Server → client message types: `price_update`, `risk_update`, `alert`, `simulation_progress`, `simulation_complete`, `replay_progress`.

### 7.8 Third-Party APIs — Summary

| Service | Auth mechanism | Failure/retry | Rate limits | Cost |
|---|---|---|---|---|
| Finnhub | API key (WS query param) | Exponential backoff reconnect, max 5 attempts before alerting via logs | Free tier: 60 REST calls/min (WS pushes are not counted the same way) | Free tier for MVP |
| Anthropic Claude API | API key (header) | 1 retry on 5xx/timeout, then graceful fallback (numbers without narration) | Per Anthropic's published tier limits for the account in use | Pay-per-token; budget-capped via a per-user monthly call count guard |
| Slack API | Bot token + signing secret (Bolt handles verification) | Bolt's built-in retry/ack handling | Slack's standard per-workspace rate limits | Free (Slack app, not a paid tier) |

---

## 8. Database Design

### 8.1 Entities

```
users ──< portfolios ──< holdings
   │            │
   │            ├──< risk_budgets (1:1)
   │            ├──< alerts ──< decisions
   │            ├──< risk_snapshots
   │            ├──< simulations
   │            ├──< replays ──< replay_daily_states
   │            │                    └──< backtest_results
   │            └──< ai_conversations ──< ai_messages
   ├──< refresh_tokens
   └──< api_tokens

symbol_subscriptions   (audit copy of the Redis reverse index)
garch_fits             (audit copy of latest per-symbol GARCH params)
regime_states          (shared, not user-scoped — HMM output history)
```

### 8.2 Table Definitions (key tables)

```sql
users
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  email             CITEXT UNIQUE NOT NULL
  password_hash     TEXT NOT NULL
  role              TEXT NOT NULL DEFAULT 'user'   -- future-proofs admin functionality
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()

refresh_tokens
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
  token_hash        TEXT NOT NULL
  expires_at        TIMESTAMPTZ NOT NULL
  revoked_at        TIMESTAMPTZ
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
  INDEX (user_id)

api_tokens
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
  token_hash        TEXT NOT NULL
  scopes            TEXT[] NOT NULL DEFAULT '{}'
  revoked_at        TIMESTAMPTZ
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()

portfolios
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE
  name              TEXT NOT NULL DEFAULT 'My Portfolio'
  source            TEXT NOT NULL          -- 'demo' | 'csv' | 'manual'
  currency          TEXT NOT NULL DEFAULT 'USD'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
  INDEX (user_id)

holdings
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  symbol            TEXT NOT NULL
  quantity          NUMERIC(18,6) NOT NULL CHECK (quantity > 0)
  average_price     NUMERIC(18,6) NOT NULL CHECK (average_price > 0)
  added_at          TIMESTAMPTZ NOT NULL DEFAULT now()
  UNIQUE (portfolio_id, symbol)
  INDEX (symbol)                            -- supports reverse-index rebuild queries

risk_budgets
  portfolio_id      UUID PRIMARY KEY REFERENCES portfolios(id) ON DELETE CASCADE
  max_cvar          NUMERIC(18,2) NOT NULL
  watch_threshold   NUMERIC(5,4) NOT NULL DEFAULT 0.60
  high_threshold    NUMERIC(5,4) NOT NULL DEFAULT 0.80
  breach_threshold  NUMERIC(5,4) NOT NULL DEFAULT 1.00
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()

risk_snapshots
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  captured_at       TIMESTAMPTZ NOT NULL DEFAULT now()
  var_95            NUMERIC(18,2) NOT NULL
  cvar_95           NUMERIC(18,2) NOT NULL
  volatility        NUMERIC(9,6) NOT NULL
  max_drawdown      NUMERIC(9,6) NOT NULL
  sharpe            NUMERIC(9,4)
  risk_state        TEXT NOT NULL           -- SAFE | WATCH | HIGH | BREACH
  risk_contribution JSONB NOT NULL          -- {symbol: pct, ...}
  correlation_flags JSONB NOT NULL DEFAULT '[]'
  INDEX (portfolio_id, captured_at DESC)

alerts
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  risk_snapshot_id  UUID NOT NULL REFERENCES risk_snapshots(id)
  from_state        TEXT NOT NULL
  to_state          TEXT NOT NULL
  fired_at          TIMESTAMPTZ NOT NULL DEFAULT now()
  dismissed_at      TIMESTAMPTZ
  INDEX (portfolio_id, fired_at DESC)

decisions
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  alert_id          UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE
  candidates        JSONB NOT NULL          -- [{label, expected_return, cvar, p_loss}, ...]
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()

simulations
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  horizon_days      INT NOT NULL
  num_paths         INT NOT NULL
  status            TEXT NOT NULL DEFAULT 'pending'   -- pending | running | complete | failed
  results           JSONB
  error_message     TEXT
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
  completed_at      TIMESTAMPTZ
  INDEX (portfolio_id, created_at DESC)

replays
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  period_key        TEXT NOT NULL           -- e.g. '2022_rate_shock'
  status            TEXT NOT NULL DEFAULT 'pending'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
  completed_at      TIMESTAMPTZ

replay_daily_states
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  replay_id         UUID NOT NULL REFERENCES replays(id) ON DELETE CASCADE
  trading_date      DATE NOT NULL
  var_95            NUMERIC(18,2) NOT NULL
  actual_return     NUMERIC(9,6) NOT NULL
  risk_state        TEXT NOT NULL
  INDEX (replay_id, trading_date)

backtest_results
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  replay_id         UUID NOT NULL REFERENCES replays(id) ON DELETE CASCADE
  predicted_breach_rate NUMERIC(6,4) NOT NULL
  actual_breach_rate    NUMERIC(6,4) NOT NULL
  kupiec_statistic      NUMERIC(12,6) NOT NULL
  p_value               NUMERIC(9,6) NOT NULL
  passed                BOOLEAN NOT NULL

ai_conversations
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  portfolio_id      UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE
  started_at        TIMESTAMPTZ NOT NULL DEFAULT now()

ai_messages
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  conversation_id   UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE
  role              TEXT NOT NULL            -- user | assistant
  content           TEXT NOT NULL
  structured_scenario JSONB                  -- present only for what-if messages
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()

symbol_subscriptions
  symbol            TEXT PRIMARY KEY
  subscriber_count  INT NOT NULL DEFAULT 0

garch_fits
  symbol            TEXT PRIMARY KEY
  omega             NUMERIC, alpha NUMERIC, beta NUMERIC
  fitted_at         TIMESTAMPTZ NOT NULL DEFAULT now()

regime_states
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
  captured_at       TIMESTAMPTZ NOT NULL DEFAULT now()
  calm_probability      NUMERIC(6,4) NOT NULL
  stressed_probability  NUMERIC(6,4) NOT NULL
  INDEX (captured_at DESC)
```

### 8.3 Normalization, Indexing, Integrity

- Schema is in 3NF; the only intentional denormalization is `risk_snapshots.risk_contribution`/`correlation_flags` as JSONB, since this is a computed, versioned snapshot rather than queryable relational state — storing it as JSON avoids a volatile, per-asset-row table that would need constant migration as the asset universe changes.
- All foreign keys `ON DELETE CASCADE` from `portfolios` downward — deleting a portfolio cleanly removes its entire history, appropriate for a personal-data product with no cross-user shared references.
- Indexes are placed on every foreign key plus every column used in a `WHERE`/`ORDER BY` on a hot path (`captured_at DESC`, `fired_at DESC`, `created_at DESC` for pagination; `symbol` on `holdings` for reverse-index rebuilds).
- Soft deletion is **not** used for portfolios/holdings (hard delete via cascade is correct for a personal-data product and simplifies every downstream query); it **is** used conceptually for `refresh_tokens`/`api_tokens` via `revoked_at` (kept for audit, excluded by a `WHERE revoked_at IS NULL` filter at validation time).
- Migrations via Alembic, one migration per schema-changing PR, autogenerated from model diffs then hand-reviewed before commit — never hand-written blind.
- Seed data: a `scripts/seed_demo_portfolio.py` script inserts the fixed demo portfolio (Assumption A4's symbol list) for any new user's `POST /portfolios/demo` call, and a separate `scripts/seed_historical_dataset.py` loads the checked-in CSV (Assumption A10) into a queryable historical-prices table used only by the replay engine.
- Concurrency: the reverse-index counter updates (`subscriber_count` INCR/DECR) happen in Redis (atomic by construction); the corresponding Postgres audit row update uses a single `UPDATE ... SET subscriber_count = subscriber_count + 1` statement (atomic at the row level, no read-modify-write race).


---

## 9. Folder Structure & Naming Conventions

```text
risklens/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, router registration
│   │   ├── config.py                  # pydantic-settings Settings object
│   │   ├── database.py                # async engine/session setup
│   │   ├── redis_client.py            # shared Redis connection pool
│   │   ├── deps.py                    # shared FastAPI dependencies (get_current_user, etc.)
│   │   ├── auth/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── portfolios/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   └── csv_normalizer.py
│   │   ├── risk/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── simulations/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── replays/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── alerts/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── models.py
│   │   ├── ai/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── agent.py               # LangGraph graph definition
│   │   │   ├── tools.py               # explain / what-if tool implementations
│   │   │   └── models.py
│   │   ├── ws/
│   │   │   ├── router.py
│   │   │   └── connection_manager.py
│   │   └── market/
│   │       ├── router.py
│   │       └── symbol_master.py
│   ├── quant/                          # framework-agnostic, no FastAPI/DB imports
│   │   ├── __init__.py
│   │   ├── covariance.py               # Ledoit-Wolf wrapper
│   │   ├── returns.py                  # return series utilities
│   │   ├── risk_metrics.py             # VaR, CVaR, Sharpe, drawdown, risk contribution
│   │   ├── garch.py                    # GARCH(1,1) fit/forecast
│   │   ├── monte_carlo.py              # GBM + Cholesky + antithetic variates
│   │   ├── evt.py                      # POT / GPD tail risk
│   │   ├── regime.py                   # HMM fit/forward-probability
│   │   ├── backtest.py                 # Kupiec test
│   │   └── scenarios.py                # what-if scenario evaluation (deterministic)
│   ├── workers/
│   │   ├── ingestion_worker.py
│   │   ├── fast_path_worker.py
│   │   ├── slow_path_worker.py
│   │   ├── garch_worker.py
│   │   ├── regime_worker.py
│   │   ├── decision_engine_worker.py
│   │   └── job_worker.py               # arq worker entrypoint (simulations, replays)
│   ├── slack_bot/
│   │   ├── app.py
│   │   └── commands.py
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── scripts/
│   │   ├── seed_demo_portfolio.py
│   │   └── seed_historical_dataset.py
│   ├── data/
│   │   └── historical/                 # checked-in historical CSV dataset (Assumption A10)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (auth)/register/page.tsx
│   │   ├── onboarding/page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── dashboard/simulate/page.tsx
│   │   ├── dashboard/replay/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                         # design-system primitives: Button, Card, Input, Modal...
│   │   ├── dashboard/                  # MetricCard, RiskBudgetBar, RiskContributionList...
│   │   ├── ai/                         # ChatMessageList, SuggestedChip...
│   │   └── simulation/                 # SimulationForm, DistributionChart...
│   ├── hooks/
│   │   ├── useRiskSocket.ts
│   │   ├── useAuth.ts
│   │   └── usePortfolio.ts
│   ├── lib/
│   │   ├── api-client.ts               # typed fetch wrapper
│   │   └── types.ts                    # generated from backend OpenAPI schema
│   ├── store/
│   │   └── auth-store.ts               # Zustand
│   ├── styles/
│   │   └── tokens.css                  # design-system CSS custom properties (§4)
│   ├── tests/
│   │   ├── unit/
│   │   └── e2e/
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── docker-compose.override.yml         # local-dev-only overrides (hot reload, exposed ports)
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── docs/
│   ├── implementation.md               # this document
│   ├── architecture.md                 # diagram-only quick reference, generated from §5
│   └── setup.md
└── README.md
```

### Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Python files/modules | `snake_case` | `csv_normalizer.py` |
| Python classes | `PascalCase` | `PortfolioService` |
| Python functions/variables | `snake_case` | `compute_risk_contribution()` |
| SQLAlchemy models | Singular `PascalCase` class, plural `snake_case` table | `class Holding` → `holdings` |
| Pydantic schemas | `PascalCase` with purpose suffix | `PortfolioCreateRequest`, `PortfolioResponse` |
| TS/React components | `PascalCase` file + export | `RiskBudgetBar.tsx` |
| TS hooks | `camelCase`, `use` prefix | `useRiskSocket.ts` |
| TS types/interfaces | `PascalCase` | `RiskSnapshot` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_RISK_THRESHOLDS` |
| API routes | plural nouns, kebab/lowercase | `/portfolios/{id}/risk-budget` |
| Git branches | `type/short-description` | `feat/monte-carlo-engine` |

---

## 10. Code Architecture & Standards

- **Separation of concerns:** every router function is a thin adapter (parse request → call one service function → return response); all business logic lives in `service.py`; all persistence lives behind repository-style functions in `models.py`/a `repository.py` where a module grows past a couple of query patterns.
- **Small, focused functions:** a function should do one thing describable in its name without "and." A quant function (e.g. `compute_var`) never also fetches data from the database — it receives a NumPy array and returns a result, making it trivially unit-testable.
- **Strong typing:** Pydantic models for every request/response; SQLAlchemy 2.0 typed models; TypeScript `strict: true`; the frontend's API types are generated from the backend's OpenAPI schema (`openapi-typescript`) as a CI-checked step, so the two can never silently drift.
- **Reusable components:** the `quant/` package (backend) and `components/ui/` (frontend) are the two reuse boundaries — nothing outside them is assumed reusable, and nothing inside them may import from outside their own boundary (enforced by code review, not tooling, at this project size).
- **Error handling:** backend raises typed domain exceptions (`PortfolioNotFoundError`, `InsufficientDataError`, etc.) caught by a single FastAPI exception-handler middleware that maps them to the standard error envelope (§7) — routers never construct raw `HTTPException` error bodies ad hoc.
- **Comments:** short, non-obvious-logic only. Example of the expected style:
```python
# Filtered (forward) probability, not the Viterbi path — we need "now," not a retrospective label.
stressed_prob = hmm_forward_probabilities[-1][STRESSED_STATE]
```
Not:
```python
# Loop through the list
for item in items:
```
- **Extensibility pattern (explicitly required by the brief):** the quant engine, decision-engine strategies, and AI tools are each implemented behind a small interface so new ones can be added without modifying existing code:
```python
class RiskModel(Protocol):
    def estimate(self, returns: pd.DataFrame) -> RiskEstimate: ...

# EVT and Monte Carlo both implement RiskModel; the simulation endpoint
# runs every registered RiskModel and returns all results side by side.
# Adding a third tail-risk method later means writing one new class
# and adding it to REGISTERED_RISK_MODELS — no other file changes.
REGISTERED_RISK_MODELS: list[RiskModel] = [MonteCarloModel(), EVTModel()]
```
The same registry pattern is used for `DecisionCandidateGenerator` (F14) and for LangGraph tools (F15), so adding a new decision candidate or a new AI capability is additive, not invasive — directly satisfying the "should be able to add or change features easily" requirement.


---

## 11. Security

- **Authentication:** bcrypt (cost factor 12) password hashing; JWT access tokens signed with a rotatable secret (`HS256` for MVP, documented upgrade to `RS256` if the API is ever split across services with independent verification needs); refresh tokens stored hashed, rotated on every use, individually revocable.
- **Authorization:** row-level ownership checks in the service layer on every data access (§5.6) — never rely on the frontend to only request its own data.
- **Session management:** refresh token in an `httpOnly`, `Secure`, `SameSite=Lax` cookie; access token held in memory on the frontend (not `localStorage`), to reduce XSS token-theft exposure.
- **CSRF:** `SameSite=Lax` cookies plus the fact that state-changing requests require the `Authorization` header (not solely the cookie) mitigates classic CSRF — the cookie alone cannot authorize a request.
- **XSS:** React's default escaping handles most of this; the AI narration text is rendered as plain text (never `dangerouslySetInnerHTML`) since it is model-generated content.
- **SQL injection:** SQLAlchemy's parameterized queries throughout; no raw string-interpolated SQL anywhere in the codebase (enforced by code review + a lint rule flagging f-string SQL).
- **Input validation:** Pydantic schemas validate every request body/query param at the API boundary before it reaches a service function; the CSV normalizer additionally validates every parsed row before insertion (F2).
- **API abuse / rate limiting:** `slowapi` (Redis-backed) rate limits: login (5/min/IP), simulation creation (10/hour/user, 1 concurrent), AI what-if (30/hour/user) — protecting both cost (LLM calls) and compute (Monte Carlo jobs).
- **Secrets management:** all secrets via environment variables, never committed; `.env.example` documents required keys with placeholder values; production secrets set directly in Render/Vercel's secret store.
- **CORS:** the API allows only the deployed frontend origin (and `localhost` in development) — not a wildcard.
- **File upload security:** CSV upload capped at 2 MB, MIME/extension-checked, parsed in-memory only (never written to disk), never executed or evaluated as anything other than tabular text.
- **Dependency vulnerabilities:** `pip-audit` (backend) and `npm audit`/Dependabot (frontend) run in CI (Phase 22/23); flagged high-severity vulnerabilities block merge.
- **Logging sensitive information:** passwords, tokens, and full AI prompts containing portfolio-identifying detail are never logged; structured logs redact known-sensitive field names centrally.
- **Data privacy:** no broker credentials are ever requested or stored (Constraint in §1); CSV files are not retained after processing; a user can delete their account, cascading to all owned data.
- **Third-party API key protection:** Finnhub/Anthropic/Slack keys live only in backend environment variables, never sent to or exposed in the frontend bundle.

---

## 12. Performance & Scalability

### Now (MVP)
- Fast-path/slow-path split (F4/F5) is implemented from day one — this is core architecture, not an optimization to defer.
- NumPy-vectorized Monte Carlo (batch matrix operations, not per-path Python loops) and antithetic variates for variance reduction at a given path count.
- Redis caching of current risk state so a page load/reconnect never triggers a synchronous recompute.
- Database indexes on every hot-path query column (§8.3) from the first migration, not added reactively.
- Pagination (cursor-based) on `/alerts` and any other potentially-growing list endpoint from day one.
- Debounced/batched slow-path recomputation (§ F5) rather than naive per-tick full recompute.

### Deferred until actual scale requires it (explicitly not built for MVP)
- Horizontal scaling of workers behind Redis Streams consumer groups (the code is already structured to support this — running two replicas is a deployment config change) — not needed until concurrent user count justifies it.
- Swapping Redis Streams for Kafka (Assumption A1) — only if throughput genuinely exceeds a single Redis instance's capacity.
- A CDN/edge cache layer for the frontend beyond what Vercel provides by default.
- Read replicas for PostgreSQL — unnecessary at demo/portfolio-project scale.
- Kubernetes/container orchestration beyond Render's managed service model — explicitly called out in the brief as something to avoid introducing "merely for resume keywords."

### Frontend performance
- Code-split routes (Next.js does this by default per route segment); charts (Recharts) lazy-loaded only on the screens that use them; skeleton loading states prevent layout shift.

### Database optimization
- All list queries paginated; JSONB columns (`risk_snapshots.risk_contribution`, etc.) are read-mostly and never filtered/joined on their internal keys, avoiding the need for GIN indexes at this scale.

---

## 13. Testing Strategy

### Unit Tests (backend, `tests/unit/`)
- Every `quant/` function tested against known analytical results or reference values (e.g. VaR on a synthetic normal return series checked against a closed-form expectation; Ledoit-Wolf shrinkage output checked for positive-definiteness; Kupiec statistic checked against a textbook worked example).
- CSV normalizer tested against each supported broker's sample column layout plus malformed/edge-case inputs.
- JWT issuance/verification, password hashing round-trip.

### Integration Tests (backend, `tests/integration/`)
- Full request/response cycles via `httpx` async test client against a test Postgres + Redis (Docker Compose test profile): register → login → import CSV → get risk → set budget.
- Worker logic tested with a fake/mock Redis Stream producing synthetic ticks, asserting correct portfolio-level recompute and correct alert firing on a state transition.

### API Tests
- Every endpoint in §7 has at least: one happy-path test, one 401/403 (auth/ownership) test, one 422 (validation) test.

### Component Tests (frontend, Vitest + RTL)
- `RiskBudgetBar` renders correct color/label per state; `ChatMessageList` renders both roles correctly; `SimulationForm` validates path-count/horizon selection.

### End-to-End Tests (Playwright)
Critical journeys:
1. Register → onboarding → demo portfolio → dashboard shows non-empty risk metrics.
2. CSV import → mapping confirmation → dashboard reflects imported holdings.
3. Trigger a Monte Carlo simulation → progress bar reaches 100% → results render, including the EVT row.
4. Run a historical replay → breach marker and Kupiec badge render.
5. Ask an AI what-if question → structured result renders with narration.

### Edge Cases (explicitly covered across the above)
- Empty portfolio, single-asset portfolio, insufficient historical data, WebSocket disconnect/reconnect, expired access token mid-session, duplicate tick delivery, simulation job failure, AI API timeout, oversized/malformed CSV.

### Manual QA Checklist (pre-release, see also §17)
- All screens in §4.6 walked through on desktop and a mobile viewport.
- Dark and light mode both checked for contrast/legibility.
- Network throttled (Chrome DevTools) to confirm loading/skeleton states appear correctly, not just on a fast connection.
- Kill the ingestion worker mid-session and confirm the dashboard shows a "stale/reconnecting" state rather than freezing silently.


---

## 14. Git & Development Strategy

The project is built across **24 phases**. Each phase results in a clean, reviewable Git milestone. Commits follow Conventional Commits (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`) with a scope, e.g. `feat(auth): implement JWT login flow`.

---

### Phase 1 — Project Foundation & Tooling

**Objective:** An empty repository becomes a structured monorepo with backend and frontend skeletons, linting/formatting, and a README, but no real features yet.

**Why This Phase Exists:** Every later phase needs a consistent place to put code and a consistent quality bar (lint/format) enforced from commit one, not retrofitted later.

**Dependencies:** None — this is the starting phase.

**What Has Already Been Completed:** Nothing (empty repo).

**What Needs To Be Done:**
- Initialize the monorepo folder structure from §9 (empty directories with `.gitkeep` where needed).
- Backend: `pyproject.toml` with FastAPI, Uvicorn, Pydantic, SQLAlchemy, dev dependencies (`ruff`, `black`, `mypy`, `pytest`); a minimal `app/main.py` returning `{"status": "ok"}` on `GET /health`.
- Frontend: `npx create-next-app` (TypeScript, Tailwind, App Router); strip the default template content; add `eslint`, `prettier`.
- Root: `.gitignore` (Python + Node + `.env`), `README.md` with project description and a placeholder setup section (filled in fully in Phase 20/24).
- Configure `ruff` + `black` (backend) and `eslint` + `prettier` (frontend) with project-standard rules; add a `pre-commit` config running both.

**Files/Directories To Create:** `backend/app/main.py`, `backend/pyproject.toml`, `backend/.env.example`, `frontend/` (Next.js scaffold), `.gitignore`, `README.md`, `.pre-commit-config.yaml`.

**Files/Directories To Modify:** N/A (all new).

**Database Changes:** None.

**API Changes:** `GET /health` only.

**UI Changes:** Default Next.js page replaced with a placeholder "RiskLens" landing text.

**Implementation Details:** Keep this phase deliberately minimal — the goal is a clean, lintable, runnable skeleton, not any real feature.

**Acceptance Criteria:** `uvicorn app.main:app` runs and `GET /health` returns 200; `npm run dev` serves the placeholder frontend page; `ruff check` / `eslint` run clean on the skeleton.

**Testing:** A single smoke test asserting `GET /health` returns `{"status": "ok"}`.

**Manual Verification:** Both dev servers start without errors; lints pass.

**Git Commit Strategy:**
```
chore(repo): initialize monorepo structure
chore(backend): scaffold FastAPI app with health endpoint
chore(frontend): scaffold Next.js app
chore(tooling): configure lint/format/pre-commit
```

**Git Checkpoint:** A runnable, empty-but-structured monorepo.

**Known Risks:** Over-scaffolding (adding folders/files for features not yet built) — keep to what §9 specifies, resist the urge to add more.

**Definition of Done:** Both apps run locally; lint/format configured; README exists.

---

### Phase 2 — Docker & Local Dev Environment

**Objective:** The entire stack (API, all future workers, Postgres, Redis, frontend) runs with a single `docker compose up`.

**Why This Phase Exists:** Every subsequent phase should be developed and verified against the same environment that will eventually run in production — building this early avoids "works on my machine" drift.

**Dependencies:** Phase 1.

**What Has Already Been Completed:** Backend/frontend skeletons.

**What Needs To Be Done:**
- `backend/Dockerfile` (API) and `backend/Dockerfile.worker` (shared base for all worker entrypoints, parameterized by `CMD`).
- `frontend/Dockerfile` (multi-stage: build, then a minimal `next start` runtime image) — used for local parity; actual production frontend hosting is Vercel (Phase 23), not this image.
- Root `docker-compose.yml`: `postgres`, `redis`, `api` services; a placeholder `worker` service (real workers added incrementally as their phases land, this phase just proves one worker container pattern works with a trivial no-op script).
- `docker-compose.override.yml`: bind-mounts for hot reload in local dev, exposed ports.
- `.env.example` at the root documenting every variable Compose expects.

**Files/Directories To Create:** `docker-compose.yml`, `docker-compose.override.yml`, `backend/Dockerfile`, `backend/Dockerfile.worker`, `frontend/Dockerfile`.

**Files/Directories To Modify:** `backend/app/config.py` introduced now to read `DATABASE_URL`/`REDIS_URL` from environment.

**Database Changes:** None yet (Postgres container running, empty).

**API Changes:** None.

**UI Changes:** None.

**Implementation Details:** Use official `postgres:15` and `redis:7` images; healthchecks on both so `api` waits for readiness before starting.

**Acceptance Criteria:** `docker compose up` brings up Postgres, Redis, API (health check passes), and the frontend, all networked together, from a clean checkout with only `.env` filled in.

**Testing:** A CI smoke job (introduced fully in Phase 23, referenced here) that runs `docker compose up -d && curl api:8000/health`.

**Manual Verification:** Full stack starts from a fresh clone with no manual steps beyond copying `.env.example` to `.env`.

**Git Commit Strategy:**
```
chore(docker): add backend and worker Dockerfiles
chore(docker): add frontend Dockerfile
chore(docker): add docker-compose for local development
```

**Git Checkpoint:** Full stack runnable via Compose.

**Known Risks:** Port collisions with other local services — document overridable ports in `.env.example`.

**Definition of Done:** Fresh clone + `.env` copy + `docker compose up` produces a fully running (if still feature-empty) stack.

---

### Phase 3 — Database Foundation

**Objective:** All core SQLAlchemy models and the first Alembic migration exist; the schema from §8 is live in Postgres.

**Why This Phase Exists:** Nearly every later phase needs persistent storage; establishing the full schema early (even for tables not yet used by any endpoint) avoids repeated migration churn.

**Dependencies:** Phase 2 (Postgres running).

**What Has Already Been Completed:** Dockerized Postgres; empty `app/database.py`.

**What Needs To Be Done:**
- `app/database.py`: async engine + session factory (`asyncpg`).
- SQLAlchemy models for every table in §8.2 (added now even though most features land later — this is a deliberate schema-first decision to avoid painful incremental migrations mid-project).
- Alembic initialized (`alembic init`), first autogenerated migration capturing the full schema.
- `scripts/seed_demo_portfolio.py` and `scripts/seed_historical_dataset.py` stubbed (real logic added in Phases 5 and 19 respectively) with a runnable no-op so the script entrypoints exist from the start.

**Files/Directories To Create:** `app/database.py`, one `models.py` per domain module (§9), `alembic/`, `scripts/seed_demo_portfolio.py`, `scripts/seed_historical_dataset.py`.

**Files/Directories To Modify:** `app/config.py` (add `DATABASE_URL`).

**Database Changes:** Full schema from §8.2 created via the first migration.

**API Changes:** None.

**UI Changes:** None.

**Implementation Details:** Use `Mapped[]`/`mapped_column()` SQLAlchemy 2.0 typed style throughout, not the legacy `Column()` style, for consistency with the "strong typing" standard in §10.

**Acceptance Criteria:** `alembic upgrade head` against a clean database creates every table in §8.2 with correct foreign keys/indexes; running it twice is idempotent (no error on re-run of an already-applied migration).

**Testing:** A test asserting all expected tables exist after migration, via `information_schema.tables`.

**Manual Verification:** Inspect the schema with `psql \dt` and `\d <table>` for a few key tables, confirm indexes/FKs match §8.2.

**Git Commit Strategy:**
```
feat(db): add SQLAlchemy models for all domain entities
feat(db): add initial Alembic migration
chore(scripts): stub seed scripts
```

**Git Checkpoint:** Full schema live in the Dockerized Postgres instance.

**Known Risks:** Autogenerated migrations sometimes miss `CHECK` constraints or `CITEXT` extension setup — hand-review the generated migration file before committing, don't blindly trust the autogenerate.

**Definition of Done:** Migration applies cleanly on a fresh database; all models importable without circular-import errors.

---

### Phase 4 — Authentication & Authorization

**Objective:** Full register/login/refresh/logout flow (F1) working end-to-end, with row-level ownership enforcement scaffolding in place for every future domain module.

**Why This Phase Exists:** Every other feature is scoped to a user; auth must exist before any user-owned resource (portfolios, alerts, etc.) can be built meaningfully.

**Dependencies:** Phase 3 (`users`, `refresh_tokens` tables exist).

**What Has Already Been Completed:** Full DB schema (unused so far beyond `users`/`refresh_tokens`).

**What Needs To Be Done:**
- `app/auth/service.py`: register (hash password, create user), login (verify password, issue access + refresh token pair), refresh (validate + rotate refresh token), logout (revoke).
- `app/auth/router.py`: the four endpoints from §7.1 (`api-tokens` endpoint deferred to Phase 21 when it's first needed).
- `app/deps.py`: `get_current_user` dependency (decodes/validates the access token) used by every future protected router.
- Rate limiting (`slowapi`) added to `/auth/login` now, as the pattern for all future rate-limited endpoints.
- Frontend: login/register pages, an Axios/fetch wrapper with auto-attach + silent-refresh-on-401 interceptor, a Zustand `auth-store`.

**Files/Directories To Create:** `app/auth/*`, `frontend/app/(auth)/login/page.tsx`, `frontend/app/(auth)/register/page.tsx`, `frontend/store/auth-store.ts`, `frontend/lib/api-client.ts`.

**Files/Directories To Modify:** `app/main.py` (register the auth router), `app/deps.py`.

**Database Changes:** None beyond what Phase 3 already created.

**API Changes:** `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` (§7.1) go live.

**UI Changes:** Login/register screens.

**Implementation Details:** Access token payload: `{sub: user_id, exp}` only — no sensitive data in the JWT body, since it is not encrypted, only signed.

**Acceptance Criteria:** A user can register, is auto-logged-in, can log out, log back in, and a refresh cycle silently renews the access token without the frontend visibly interrupting the session.

**Testing:** Unit tests for password hashing/verification and JWT encode/decode; integration tests for the full register → login → refresh → logout cycle including a 401 test for an invalid/expired token and a 409 test for duplicate email.

**Manual Verification:** Register a user in the browser, confirm the refresh cookie is `httpOnly` (DevTools → Application → Cookies), confirm logging out actually revokes (a reused refresh token after logout must fail).

**Git Commit Strategy:**
```
feat(auth): implement registration and login
feat(auth): implement refresh token rotation and logout
feat(auth): add current-user dependency for protected routes
feat(ui): build login and register pages
test(auth): add auth flow coverage
```

**Git Checkpoint:** A user can fully register/login/logout; every future protected endpoint can depend on `get_current_user`.

**Known Risks:** Refresh-token rotation race (two tabs refreshing simultaneously) — mitigate with a short grace window accepting the immediately-prior token once, documented as a known, acceptable MVP simplification.

**Definition of Done:** All four auth endpoints pass their tests; frontend auth flow works end-to-end in the browser against the Dockerized stack.

---

### Phase 5 — Portfolio Ingestion

**Objective:** F2 fully implemented — demo seed, CSV import with mapping confirmation, manual entry.

**Why This Phase Exists:** No risk calculation is possible without portfolio data; this is the first real domain feature and the "front door" of the product.

**Dependencies:** Phase 4 (auth), Phase 3 (`portfolios`, `holdings` tables).

**What Has Already Been Completed:** Auth; empty `portfolios`/`holdings` tables.

**What Needs To Be Done:**
- `app/portfolios/csv_normalizer.py`: header fuzzy-matching against canonical fields, confidence-scored mapping suggestion.
- `app/portfolios/service.py`: create demo portfolio (fixed seed list, Assumption A4), preview/confirm CSV import, manual holding CRUD.
- `app/portfolios/router.py`: all endpoints from §7.2 except `/risk` and `/risk-budget` (added in Phases 10/14).
- Fill in `scripts/seed_demo_portfolio.py` for real.
- Frontend: onboarding screen (three-path UI from §4.6), CSV dropzone + mapping-confirmation table, manual-entry form with symbol autocomplete (calling the not-yet-built `/market/symbols` — stub with a small static list for now, replaced properly in Phase 6).

**Files/Directories To Create:** `app/portfolios/*`, `frontend/app/onboarding/page.tsx`, `frontend/components/onboarding/*`.

**Files/Directories To Modify:** `app/main.py` (register router), `scripts/seed_demo_portfolio.py`.

**Database Changes:** None beyond Phase 3's schema — this phase populates it.

**API Changes:** `/portfolios/demo`, `/portfolios/import/preview`, `/portfolios/import/confirm`, `/portfolios/{id}/holdings` (POST/DELETE), `/portfolios/{id}` (GET).

**UI Changes:** Full onboarding screen per §4.6.

**Implementation Details:** The mapping-confirmation step must show the user's *actual* detected mapping before any DB write — never silently guess and import.

**Acceptance Criteria:** All three ingestion paths result in a correctly populated `portfolios`/`holdings` pair, scoped to the authenticated user.

**Testing:** Unit tests for the normalizer against several synthetic broker CSV layouts (including one deliberately malformed one); integration tests for all new endpoints including ownership (user A cannot see user B's portfolio).

**Manual Verification:** Manually upload a real broker CSV export format, confirm the detected mapping is sensible, confirm holdings appear correctly after confirm.

**Git Commit Strategy:**
```
feat(portfolios): implement demo portfolio seeding
feat(portfolios): implement CSV import with column normalization
feat(portfolios): implement manual holding entry
feat(ui): build onboarding flow
test(portfolios): add ingestion path coverage
```

**Git Checkpoint:** A user can get a real portfolio into the system via any of the three paths.

**Known Risks:** Broker CSV formats vary more than the normalizer's fuzzy-matching may anticipate — document this as an acceptable MVP limitation with the manual-mapping-override always available as a fallback.

**Definition of Done:** Demo/CSV/manual all tested and working; onboarding screen fully functional against the live backend.

---

### Phase 6 — Market Data Ingestion Service

**Objective:** A standalone `ingestion_worker` holds a live Finnhub WebSocket connection and publishes ticks to a Redis Stream (F4's data-source half).

**Why This Phase Exists:** This is the first piece of the event-driven core — without it, nothing downstream (fast path, slow path, alerts) has real data to react to.

**Dependencies:** Phase 2 (Redis running), Phase 5 (at least one portfolio/symbol exists to have something meaningful to subscribe to).

**What Has Already Been Completed:** Portfolios with holdings exist; Redis is running but unused for streaming so far.

**What Needs To Be Done:**
- `workers/ingestion_worker.py`: connects to Finnhub WS, subscribes to a starting symbol set (initially: all symbols currently in `symbol_subscriptions` with `subscriber_count > 0`, computed properly in Phase 7 — for this phase, subscribe to a fixed demo symbol list to prove the pipeline end-to-end), publishes each trade tick to Redis Stream `market:ticks` (`XADD`) with fields `{symbol, price, timestamp}`.
- Automatic reconnect with exponential backoff on WS drop.
- A `market/symbol_master.py` static list (curated large-cap symbols) backing `GET /market/symbols` autocomplete (replacing Phase 5's placeholder).
- Add the real `worker` service definition to `docker-compose.yml` (replacing the Phase 2 placeholder), running this file.

**Files/Directories To Create:** `workers/ingestion_worker.py`, `app/market/symbol_master.py`, `app/market/router.py`.

**Files/Directories To Modify:** `docker-compose.yml` (real ingestion worker service), `app/main.py` (register market router).

**Database Changes:** None yet (this phase is Redis-only for tick flow).

**API Changes:** `GET /market/symbols?query=`.

**UI Changes:** Onboarding's manual-entry autocomplete now hits the real endpoint.

**Implementation Details:** Store the Finnhub API key only in the worker's environment, never in the API service's environment (principle of least privilege between processes).

**Acceptance Criteria:** With the worker running, `XLEN market:ticks` in Redis grows over time during market hours; a WS drop (simulated by killing network access briefly) results in automatic reconnection within the backoff window, verified in worker logs.

**Testing:** Unit test for the reconnect/backoff logic using a mocked WebSocket client; a smoke integration test asserting at least one message lands in the Redis Stream within a bounded wait when connected to Finnhub's sandbox/live feed.

**Manual Verification:** Watch worker logs during market hours, confirm ticks are being received and published.

**Git Commit Strategy:**
```
feat(ingestion): implement Finnhub WebSocket ingestion worker
feat(ingestion): publish ticks to Redis Stream with reconnect/backoff
feat(market): add symbol master list and autocomplete endpoint
```

**Git Checkpoint:** Live market ticks flowing into Redis continuously.

**Known Risks:** Finnhub free-tier data is delayed ~15 minutes and may have thin coverage outside US market hours — document this explicitly in the demo script so it isn't mistaken for a bug; outside market hours, seed a "replay mode" fallback (documented, built properly in Phase 19) for demoing the live-update UI convincingly at any time.

**Definition of Done:** Ticks flow continuously into `market:ticks` whenever the worker runs; reconnect logic verified.


---

### Phase 7 — Symbol Reverse Index & Dynamic Subscription Routing

**Objective:** F3 fully implemented — the ingestion worker subscribes only to symbols actually held by at least one portfolio, and ticks can be routed to the correct set of portfolios.

**Why This Phase Exists:** Without this, the ingestion worker either subscribes to a hardcoded list (Phase 6's stopgap) or, worse, to every symbol anyone has ever mentioned — this phase makes subscription genuinely demand-driven and makes tick routing efficient (O(portfolios holding this symbol), not O(all portfolios)).

**Dependencies:** Phase 5 (holdings CRUD exists), Phase 6 (ingestion worker exists).

**What Has Already Been Completed:** Ingestion worker with a fixed demo symbol list; holdings CRUD without any index side effect yet.

**What Needs To Be Done:**
- A shared internal service function `update_symbol_index(symbol, portfolio_id, delta)` called from every holding create/delete path (Phase 5's endpoints, modified now): updates the Redis reverse-index set and the `subscriber_count` (Redis + the `symbol_subscriptions` Postgres audit row) atomically.
- On a 0→1 transition, publish a `{"action": "subscribe", "symbol": ...}` message on a Redis pub/sub control channel; the ingestion worker subscribes to this channel and adjusts its live Finnhub subscription accordingly (replacing Phase 6's fixed list).
- On worker boot, rebuild the in-memory Finnhub subscription set from `symbol_subscriptions` (Postgres) where `subscriber_count > 0`, so a worker restart doesn't lose subscriptions or require replaying every historical holding-change event.

**Files/Directories To Create:** `app/portfolios/reverse_index_service.py`.

**Files/Directories To Modify:** `app/portfolios/service.py` (call the index service on add/remove holding), `workers/ingestion_worker.py` (subscribe to the control channel, remove the fixed demo list).

**Database Changes:** None beyond the already-existing `symbol_subscriptions` table (Phase 3) — this phase is the first to actually write to it.

**API Changes:** None (internal).

**UI Changes:** None.

**Implementation Details:** Use a Redis `MULTI`/pipeline for the set-update + counter-update pair to avoid a partial-update race; the Postgres audit row update uses the atomic `subscriber_count = subscriber_count + 1` pattern from §8.3.

**Acceptance Criteria:** Adding a holding for a previously-unwatched symbol results in the ingestion worker subscribing to it on Finnhub within a few seconds (observable in worker logs); removing the last portfolio holding a symbol results in an unsubscribe.

**Testing:** Integration test: add holding → assert control-channel message published and `subscriber_count` incremented; remove holding → assert decrement and, at zero, an unsubscribe message.

**Manual Verification:** Add a new symbol via the manual-entry UI, watch the ingestion worker's logs subscribe to it live.

**Git Commit Strategy:**
```
feat(portfolios): implement symbol reverse index service
feat(ingestion): subscribe dynamically based on reverse index
```

**Git Checkpoint:** Subscriptions are fully demand-driven and survive worker restarts correctly.

**Known Risks:** A brief window between a holding being added and the Finnhub subscription taking effect (a few seconds) — acceptable for MVP, documented rather than engineered away.

**Definition of Done:** Dynamic subscribe/unsubscribe verified working; worker restart correctly rebuilds its subscription set from Postgres.

---

### Phase 8 — Core Quant Engine (Returns, Ledoit-Wolf Covariance, Base Risk Metrics)

**Objective:** The framework-agnostic `quant/` package (F6 plus the foundational metrics behind F5/F11) is built and unit-tested in isolation, with no database or FastAPI dependency.

**Why This Phase Exists:** This is the mathematical core of the entire product; building and testing it in isolation before wiring it into any worker means every later phase (fast/slow path, Monte Carlo, EVT, decision engine) consumes a already-correct, already-tested engine rather than debugging math and plumbing simultaneously.

**Dependencies:** None beyond Phase 1 (project skeleton) — this phase can technically be developed in parallel with Phases 4–7, since it has no dependency on auth, portfolios, or ingestion. It is sequenced here because Phase 9 needs it immediately.

**What Has Already Been Completed:** Project skeleton only, as far as this package is concerned.

**What Needs To Be Done:**
- `quant/returns.py`: compute simple/log daily returns from a price series; portfolio return series from weighted holdings.
- `quant/covariance.py`: `estimate_covariance(returns_df) -> np.ndarray` wrapping `sklearn.covariance.LedoitWolf`, with a documented fallback (diagonal covariance) below the minimum-observation threshold (F6's edge case).
- `quant/risk_metrics.py`: portfolio volatility (`sqrt(w^T Σ w)`), historical VaR/CVaR at a configurable confidence level, Sharpe ratio, max drawdown, and risk contribution (`MCR_i = (Σw)_i / σ_p`, `RC_i = w_i · MCR_i`) per §1's formulas.
- Every function takes plain NumPy/Pandas structures in and returns plain, typed dataclasses out — zero I/O inside this package.

**Files/Directories To Create:** `quant/returns.py`, `quant/covariance.py`, `quant/risk_metrics.py`, `tests/unit/test_quant_*.py`.

**Files/Directories To Modify:** None.

**Database Changes:** None.

**API Changes:** None (not wired to any endpoint yet — that happens in Phase 10).

**UI Changes:** None.

**Implementation Details:** Validate the Ledoit-Wolf output is positive-semidefinite as a unit-test assertion, not just trusted from the library; validate risk-contribution values sum to total portfolio volatility (a correctness invariant worth asserting directly in tests).

**Acceptance Criteria:** All quant functions produce numerically correct results against hand-computed or reference-library values on synthetic fixtures; 100% of `quant/` has unit test coverage before this phase is considered complete (this package is the one place in the codebase where that bar is enforced strictly, given it is the mathematical foundation of the whole product).

**Testing:** Extensive unit tests — this phase is disproportionately testing-heavy relative to its "feature" surface, deliberately, since correctness here underlies every visible feature later.

**Manual Verification:** Spot-check VaR/CVaR/Sharpe against a manually computed example in a scratch notebook.

**Git Commit Strategy:**
```
feat(quant): implement return series utilities
feat(quant): implement Ledoit-Wolf covariance estimation
feat(quant): implement core risk metrics (VaR, CVaR, Sharpe, drawdown, risk contribution)
test(quant): add comprehensive unit coverage for risk metrics
```

**Git Checkpoint:** A fully correct, fully tested, standalone quant package, unused by any endpoint yet.

**Known Risks:** It is tempting to skip deep testing here to "get to the visible feature faster" — resist this; a subtle bug in this package silently corrupts every downstream number in the product.

**Definition of Done:** All quant functions implemented and unit-tested; package has zero imports from `app/` (verified by a simple import-graph check).

---

### Phase 9 — Fast-Path Real-Time Pipeline & WebSocket Fan-Out

**Objective:** F4 fully implemented — ticks from Redis Stream `market:ticks` update portfolio price/P&L and push to connected browsers with sub-second latency.

**Why This Phase Exists:** This is the first end-to-end proof of the "continuous, not manual" value proposition and the foundation every later real-time feature (alerts, regime badge, decision engine push) builds on.

**Dependencies:** Phase 6/7 (ticks flowing, reverse index routing), Phase 4 (auth, for the WS ticket flow).

**What Has Already Been Completed:** Ticks in Redis Stream; reverse index; authenticated users.

**What Needs To Be Done:**
- `workers/fast_path_worker.py`: Redis Streams consumer group on `market:ticks`; for each tick, look up affected portfolios via the reverse index, recompute `portfolio_value`/`daily_pnl` (cheap weighted sum), write to `risk_state:{portfolio_id}` in Redis, publish to `risk_updates:{portfolio_id}` pub/sub with idempotency-by-timestamp (F4's edge case — never let an older tick overwrite a newer computed state).
- `app/ws/connection_manager.py` + `app/ws/router.py`: `POST /ws/ticket` (issue short-lived ticket), `WS /ws` (validate ticket, handle `subscribe` message, validate portfolio ownership, subscribe the socket to the matching Redis pub/sub channel, forward messages).
- Frontend: `hooks/useRiskSocket.ts` (connect, request ticket, subscribe, dispatch typed messages into state); the dashboard page wired to render live `portfolio_value`/`daily_pnl` from this hook.

**Files/Directories To Create:** `workers/fast_path_worker.py`, `app/ws/*`, `frontend/hooks/useRiskSocket.ts`, `frontend/app/dashboard/page.tsx` (first real version).

**Files/Directories To Modify:** `docker-compose.yml` (add `fast_path_worker` service), `app/main.py` (register ws router).

**Database Changes:** None (fast path is Redis-only by design, per F4).

**API Changes:** `POST /ws/ticket`, `WS /ws`.

**UI Changes:** Dashboard now shows live-updating portfolio value/P&L (still missing the risk-metrics section, added in Phase 10).

**Implementation Details:** The connection manager maps `websocket connection → set of subscribed portfolio_ids` and `portfolio_id → set of websocket connections`, both directions needed for clean disconnect cleanup.

**Acceptance Criteria:** With the ingestion + fast-path workers running and a browser dashboard open, a real market tick updates the displayed portfolio value within ~1 second, with no page refresh.

**Testing:** Integration test using a fake Redis Stream producer emitting synthetic ticks, asserting the correct `risk_state` Redis key is updated and the correct pub/sub message is published, scoped only to portfolios actually holding that symbol; a WS-level test using `httpx`'s WebSocket test support for the subscribe/ownership-check flow.

**Manual Verification:** Open two browser sessions for two different users holding different symbols; confirm each only receives updates for their own holdings' relevant ticks (data isolation, not just a UI check).

**Git Commit Strategy:**
```
feat(realtime): implement fast-path tick consumer
feat(ws): implement WebSocket ticket issuance and connection manager
feat(ui): wire live dashboard to WebSocket price/PnL updates
test(realtime): add fast-path and WS ownership coverage
```

**Git Checkpoint:** Live, per-user, ownership-scoped real-time price/P&L updates working end-to-end.

**Known Risks:** Out-of-order tick delivery under load — the timestamp-based idempotency guard (F4) must be tested explicitly with an artificially reordered synthetic tick sequence, not assumed correct.

**Definition of Done:** Live updates verified in-browser; ownership isolation verified by test, not just by inspection.

---

### Phase 10 — Slow-Path Risk Recompute

**Objective:** F5 fully implemented — VaR, CVaR, volatility, drawdown, Sharpe recomputed on a debounced/batched cadence using the Phase 8 quant engine, and surfaced on the dashboard.

**Why This Phase Exists:** This is where the quant engine (Phase 8) and the real-time pipeline (Phase 9) meet — the first phase where the product's actual risk numbers become visible.

**Dependencies:** Phase 8 (quant engine), Phase 9 (tick pipeline, WS fan-out pattern).

**What Has Already Been Completed:** Fast-path price/PnL updates; a correct, tested quant engine sitting unused.

**What Needs To Be Done:**
- `workers/slow_path_worker.py`: separate Redis Streams consumer group on `market:ticks`; batches affected-portfolio recompute requests into a rolling window (time- or count-based, whichever triggers first); on each window flush, pulls recent price history (from a small in-memory/Redis-cached rolling buffer maintained by this worker, seeded from Finnhub historical bars on first computation for a symbol) and calls the Phase 8 quant engine; writes the result into `risk_state:{portfolio_id}` (merging with fast-path fields) and publishes a `risk_update` WS message; periodically (every ~5 min) persists a `risk_snapshots` row (§8.2) for audit/replay-comparison purposes.
- `GET /portfolios/{id}/risk` (§7.2) implemented, reading the cached `risk_state` (REST fallback for non-WS clients, initial page load).
- Frontend: dashboard's risk-metrics panel (VaR/CVaR/volatility/drawdown/Sharpe cards) wired to both the initial REST fetch and subsequent WS `risk_update` messages.

**Files/Directories To Create:** `workers/slow_path_worker.py`, `app/risk/service.py`, `app/risk/router.py`, `frontend/components/dashboard/MetricCard.tsx`.

**Files/Directories To Modify:** `docker-compose.yml` (add `slow_path_worker` service), `app/main.py` (register risk router), `frontend/app/dashboard/page.tsx`.

**Database Changes:** First real writes to `risk_snapshots`.

**API Changes:** `GET /portfolios/{id}/risk`.

**UI Changes:** Full risk-metrics section of the dashboard live.

**Implementation Details:** The "insufficient historical data" edge case (F5) must render an explicit UI state, not a zero or an error — a genuinely new portfolio with only a few price observations should say so.

**Acceptance Criteria:** VaR/CVaR/volatility/drawdown/Sharpe visibly update on the dashboard within the batching window after a relevant tick, distinctly slower/less frequent than the price ticker from Phase 9.

**Testing:** Integration test asserting the batching window actually batches (multiple rapid ticks → one recompute, not N); unit test for the insufficient-data fallback path; a test asserting an exception in one portfolio's computation does not stop the worker loop for other portfolios (F5's isolation edge case).

**Manual Verification:** Watch the dashboard during active market hours, confirm the two update cadences (fast price tick vs. slower risk-metric refresh) are visibly distinct as designed.

**Git Commit Strategy:**
```
feat(risk): implement slow-path batched risk recompute worker
feat(risk): add risk snapshot persistence
feat(api): add GET portfolio risk endpoint
feat(ui): wire dashboard risk metrics panel
test(risk): add batching, isolation, and insufficient-data coverage
```

**Git Checkpoint:** The dashboard shows real, correctly computed, live-updating risk metrics for the first time.

**Known Risks:** Seeding enough historical price data for a *newly added* symbol to compute a meaningful covariance matrix immediately — mitigate by fetching a bootstrap history window (e.g. last 60 trading days) from Finnhub's REST historical-candles endpoint the first time a symbol is added, rather than only relying on ticks accumulated after subscription.

**Definition of Done:** All five core risk metrics visible and correctly updating on the live dashboard; isolation and insufficient-data edge cases covered by tests.


---

### Phase 11 — GARCH Volatility Modeling

**Objective:** F7 fully implemented — per-symbol GARCH(1,1) conditional volatility, scheduled refit, feeding downstream simulation/tail-risk phases.

**Why This Phase Exists:** Sequenced right after the core risk pipeline is live so Monte Carlo (Phase 12) can consume real, time-varying volatility from day one rather than being built against a flat-volatility placeholder and reworked later.

**Dependencies:** Phase 10 (a working price-history buffer to fit against).

**What Has Already Been Completed:** Slow-path recompute using flat historical volatility implicitly (via the covariance matrix's diagonal).

**What Needs To Be Done:**
- `quant/garch.py`: `fit_garch(returns) -> GarchFit` wrapping `arch.arch_model(returns, vol='Garch', p=1, q=1)`, plus `forecast_volatility(fit, horizon)`; documented fallback to historical standard deviation below the minimum-observation threshold (F7's edge case).
- `workers/garch_worker.py`: scheduled (e.g. every 15 minutes via a simple asyncio sleep-loop or APScheduler) refit for every symbol currently in `symbol_subscriptions` with `subscriber_count > 0`; writes `symbol_volatility:{symbol}` to Redis and an audit row to `garch_fits`.
- Wire `quant/risk_metrics.py`'s Monte-Carlo-facing volatility input (used starting in Phase 12) to read from `symbol_volatility:{symbol}` when available, falling back to the historical estimate otherwise.

**Files/Directories To Create:** `quant/garch.py`, `workers/garch_worker.py`, `tests/unit/test_garch.py`.

**Files/Directories To Modify:** `docker-compose.yml` (add `garch_worker` service).

**Database Changes:** First real writes to `garch_fits`.

**API Changes:** None (internal, consumed by Phase 12/13).

**UI Changes:** None directly (invisible per §4's design decision for this feature).

**Implementation Details:** Catch `arch` non-convergence exceptions explicitly and fall back rather than letting the worker crash on a single problematic symbol.

**Acceptance Criteria:** `symbol_volatility:{symbol}` is populated and refreshed on schedule for every actively-subscribed symbol; a symbol with insufficient history correctly falls back without error.

**Testing:** Unit tests against a synthetic GARCH-generated return series (fit should recover parameters in the right ballpark), and against an insufficient-length series (fallback path).

**Manual Verification:** Inspect `garch_fits` rows after a scheduled refit cycle; confirm parameters are sane (`alpha + beta < 1` for stationarity).

**Git Commit Strategy:**
```
feat(quant): implement GARCH(1,1) volatility estimation
feat(garch): implement scheduled per-symbol refit worker
test(quant): add GARCH fit and fallback coverage
```

**Git Checkpoint:** Time-varying volatility available for every actively-held symbol.

**Known Risks:** GARCH fitting is the most computationally expensive scheduled job so far — ensure it runs on its own worker (already the plan) so a slow fit never blocks the fast/slow tick-processing paths.

**Definition of Done:** Volatility estimates refresh on schedule; fallback path tested; no worker crashes on a bad fit.

---

### Phase 12 — Monte Carlo Simulation Engine

**Objective:** F8 fully implemented — async, progress-streamed Monte Carlo simulation using GBM, Cholesky-correlated shocks (from the Ledoit-Wolf covariance matrix, Phase 8), GARCH-informed volatility (Phase 11), and antithetic variates.

**Why This Phase Exists:** The platform's headline quantitative feature; also the shared engine reused by the Decision Engine (Phase 17) and, in reduced form, by the Historical Replay's per-day evaluation is *not* Monte Carlo (that reuses Phase 8/10 directly) — Monte Carlo here is specifically the user-triggered "what happens next" simulation.

**Dependencies:** Phase 8 (covariance), Phase 11 (volatility), Phase 2's `arq`/Redis setup.

**What Has Already Been Completed:** Correct covariance and volatility inputs available; no simulation capability yet.

**What Needs To Be Done:**
- `quant/monte_carlo.py`: vectorized (NumPy, batched matrix ops, not per-path loops) GBM path simulation with Cholesky-decomposed correlated shocks and antithetic variate pairing; returns probability-of-profit/loss, expected P&L, and a percentile range.
- `app/simulations/service.py` + `router.py`: `POST /simulations` creates a `simulations` row (`status=pending`) and enqueues an `arq` job; `GET /simulations/{id}` polls/fetches.
- `workers/job_worker.py`: the `arq` worker entrypoint; the Monte Carlo job function runs the simulation in batches, publishing `simulation_progress` WS messages via the existing portfolio pub/sub channel every N batches, writes final results (and status) to the `simulations` row on completion, catches and records failure with `error_message` on exception (never leaves a job stuck `pending` — enforced via an `arq` job timeout).
- Frontend: Simulation panel (form, progress bar, results) per §4.6.

**Files/Directories To Create:** `quant/monte_carlo.py`, `app/simulations/*`, `workers/job_worker.py`, `frontend/app/dashboard/simulate/page.tsx`, `frontend/components/simulation/*`.

**Files/Directories To Modify:** `docker-compose.yml` (add `job_worker` service running `arq`), `app/main.py` (register simulations router).

**Database Changes:** First real writes to `simulations`.

**API Changes:** `POST /simulations`, `GET /simulations/{id}`.

**UI Changes:** Full Monte Carlo panel per §4.6 (EVT row added in Phase 13).

**Implementation Details:** Rate-limit simulation creation (§11: 10/hour/user, 1 concurrent) at the router level before the job is ever enqueued.

**Acceptance Criteria:** A user can run a 10K/50K/100K-path simulation at any offered horizon, see live progress, and see a final, numerically sane result (probability of profit/loss summing to ~1, expected range consistent with the portfolio's volatility).

**Testing:** Unit tests for the vectorized simulation against a known-analytical single-asset GBM case (mean/variance of the terminal distribution should match theory within Monte Carlo error at a large path count); integration test for the full create → progress → complete job lifecycle using a fake/short-circuited job for speed; a failure-path test (force an exception mid-job, assert `status=failed` with a message, never stuck `pending`).

**Manual Verification:** Run a real 100K-path simulation in the browser, watch the progress bar, confirm results render.

**Git Commit Strategy:**
```
feat(quant): implement vectorized Monte Carlo simulation engine
feat(simulations): implement async simulation job creation and polling
feat(worker): implement arq job worker with progress streaming
feat(ui): build Monte Carlo simulation panel
test(quant): add Monte Carlo statistical correctness coverage
test(simulations): add job lifecycle and failure-path coverage
```

**Git Checkpoint:** A user can trigger, watch, and read the result of a real Monte Carlo simulation end-to-end.

**Known Risks:** 100K paths across many assets can be memory-heavy if implemented naively — batch the simulation (e.g. 10K paths per batch, accumulate summary statistics incrementally) rather than holding the full path matrix in memory at once; this is also what enables meaningful progress reporting.

**Definition of Done:** All three path counts and all four horizons work correctly and within acceptable time/memory bounds; job lifecycle fully tested.

---

### Phase 13 — EVT / Peaks-Over-Threshold Tail Risk

**Objective:** F9 fully implemented — a Generalized Pareto Distribution tail-risk estimate computed alongside every Monte Carlo simulation, for comparison.

**Why This Phase Exists:** Directly follows Monte Carlo since it shares the same trigger point and result payload, and is cheap enough (unlike Monte Carlo) to compute synchronously within the same request/job.

**Dependencies:** Phase 12 (simulation result payload/UI structure to extend).

**What Has Already Been Completed:** Monte Carlo simulation fully working, `simulations.results` JSON populated with a `monte_carlo` sub-object only.

**What Needs To Be Done:**
- `quant/evt.py`: `fit_evt(returns, threshold_quantile=0.90) -> EVTFit` using `scipy.stats.genpareto.fit()` on the exceedances beyond the chosen threshold; derive VaR/CVaR analytically from the fitted shape/scale parameters; automatic threshold-lowering (or an explicit "insufficient tail data" result) when too few exceedances exist (F9's edge case).
- Modify the Phase 12 job function to also compute the EVT estimate (synchronously, since it's cheap) and include it as an `evt` sub-object in the same `simulations.results` JSON.
- Frontend: add the EVT comparison row to the existing Simulation panel per §4.6.

**Files/Directories To Create:** `quant/evt.py`, `tests/unit/test_evt.py`.

**Files/Directories To Modify:** `workers/job_worker.py` (Monte Carlo job function extended), `frontend/components/simulation/EVTComparisonRow.tsx`.

**Database Changes:** None (extends the existing `results` JSONB shape, no migration needed since it's schemaless JSON).

**API Changes:** `GET /simulations/{id}` response gains the `evt` field (additive, non-breaking).

**UI Changes:** EVT comparison row added to the Simulation panel.

**Implementation Details:** Never silently fall back to hiding the EVT row on fit failure — show the explicit "EVT estimate unavailable" message (F9's error-handling requirement) so the user knows a second check was attempted.

**Acceptance Criteria:** Every completed simulation shows both a Monte Carlo and an EVT CVaR figure side by side; on a portfolio with too little historical tail data, the explicit unavailable message shows instead of a fabricated number.

**Testing:** Unit tests against a synthetic heavy-tailed return series (EVT CVaR should exceed the Gaussian/Monte-Carlo-implied CVaR, demonstrating the intended effect) and against a too-short series (fallback message path).

**Manual Verification:** Run a real simulation, confirm the EVT row appears and the two numbers are both sane and the EVT figure is generally the more conservative (larger) one, as expected.

**Git Commit Strategy:**
```
feat(quant): implement EVT / Peaks-Over-Threshold tail risk estimation
feat(simulations): include EVT estimate alongside Monte Carlo results
feat(ui): add EVT comparison row to simulation panel
test(quant): add EVT fit and insufficient-data coverage
```

**Git Checkpoint:** Every simulation result now demonstrates two independent, correctly-differentiated tail-risk methodologies.

**Known Risks:** Threshold choice materially affects the GPD fit — document the chosen default (90th percentile) and its rationale in code comments and in the README's methodology section, rather than treating it as an arbitrary magic number.

**Definition of Done:** EVT estimate correctly computed and displayed for every simulation with sufficient data; explicit fallback message otherwise.


---

### Phase 14 — Risk Budget & Real-Time Alerting

**Objective:** F10 fully implemented — user-configurable risk budget, SAFE/WATCH/HIGH/BREACH state machine, and real-time push alerts on state transitions.

**Why This Phase Exists:** This converts the (now fully working) risk-metrics pipeline into the product's core proactive behavior — the single most important feature for the "continuous, not manual" value proposition.

**Dependencies:** Phase 10 (slow-path recompute producing CVaR on a live cadence).

**What Has Already Been Completed:** CVaR computed and refreshed continuously; no budget/alerting concept yet.

**What Needs To Be Done:**
- `PUT /portfolios/{id}/risk-budget` (§7.2): create/update the `risk_budgets` row; sensible default thresholds pre-filled during onboarding (Phase 5's flow extended with an optional budget-setting step, or a settings-page addition — implemented here as a dashboard settings modal since onboarding is already feature-complete from Phase 5).
- Extend `workers/slow_path_worker.py`: after each recompute, calculate `utilization = cvar / budget.max_cvar`, map to a state via the configurable thresholds, compare to the *previously stored* state (kept in `risk_state:{portfolio_id}`); on a genuine transition, write an `alerts` row (linked to the triggering `risk_snapshots` row), publish an `alert` WS message; apply a minimum-time-between-alerts guard to prevent oscillation spam (F10's edge case).
- `GET /alerts` (§7.4): cursor-paginated list.
- Frontend: risk-budget utilization bar (colored by state) on the dashboard; a settings modal to set/edit the budget; an `AlertBanner` component that slides in on a WS `alert` message and persists for BREACH-level alerts until dismissed (§4.5's toast rule).

**Files/Directories To Create:** `app/alerts/*`, `frontend/components/dashboard/RiskBudgetBar.tsx`, `frontend/components/dashboard/AlertBanner.tsx`, `frontend/components/settings/RiskBudgetModal.tsx`.

**Files/Directories To Modify:** `workers/slow_path_worker.py`, `app/portfolios/router.py` (risk-budget endpoint), `app/main.py` (register alerts router).

**Database Changes:** First real writes to `risk_budgets` and `alerts`.

**API Changes:** `PUT /portfolios/{id}/risk-budget`, `GET /alerts`.

**UI Changes:** Budget bar, alert banner, budget settings modal.

**Implementation Details:** The "no budget configured yet" edge case (F10) must show a clear prompt on the dashboard, not a broken/zero utilization bar.

**Acceptance Criteria:** Setting a deliberately low budget on a real or demo portfolio results in a genuine BREACH alert firing and appearing in-browser without a page refresh, exactly once per transition (not repeatedly while the state remains unchanged).

**Testing:** Integration test simulating a sequence of recomputes crossing multiple thresholds, asserting exactly one alert per transition and none for a repeated same-state recompute; a test for the minimum-time-between-alerts guard.

**Manual Verification:** Manually set an artificially low budget on the demo portfolio, confirm a real-time alert appears; confirm dismissing a non-BREACH toast auto-dismisses after 5s while a BREACH banner persists until manually dismissed.

**Git Commit Strategy:**
```
feat(alerts): implement risk budget configuration
feat(alerts): implement breach state machine and real-time alert firing
feat(ui): build risk budget bar and alert banner
test(alerts): add state-transition and anti-oscillation coverage
```

**Git Checkpoint:** The platform now behaves proactively, not just reactively — its defining feature is live.

**Known Risks:** Threshold oscillation right at a boundary — the hysteresis/minimum-interval guard must be tested with an adversarial synthetic sequence hovering exactly at a threshold, not just a clean monotonic one.

**Definition of Done:** Budget configuration, state machine, and real-time alerting all verified working and tested.

---

### Phase 15 — Hidden Correlation / Concentration Detector

**Objective:** F11 fully implemented — per-asset risk contribution displayed alongside allocation weight, and correlation-cluster warnings surfaced on the dashboard.

**Why This Phase Exists:** The single most differentiated, demo-worthy quant feature; sequenced right after alerting since it reuses the same slow-path recompute cycle and covariance matrix already being calculated.

**Dependencies:** Phase 10 (slow-path recompute, Ledoit-Wolf covariance already available per-cycle).

**What Has Already Been Completed:** Portfolio-level VaR/CVaR/volatility; per-asset breakdown not yet surfaced.

**What Needs To Be Done:**
- Extend `quant/risk_metrics.py` (already has the `RC_i`/`MCR_i` formulas from Phase 8 — this phase is primarily about *surfacing*, not computing, since the math already exists): add a `detect_correlation_clusters(correlation_matrix, threshold=0.7)` utility returning grouped symbol clusters exceeding the threshold.
- Extend `workers/slow_path_worker.py`'s recompute to include `risk_contribution` and `correlation_flags` in the `risk_state`/`risk_snapshots` payload (the `risk_snapshots` schema already has these JSONB columns from Phase 3 — this phase populates them for the first time).
- Frontend: `RiskContributionList` (horizontal bar list, allocation % vs. risk-contribution % side by side) and `ConcentrationWarning` banner component on the dashboard.

**Files/Directories To Create:** `frontend/components/dashboard/RiskContributionList.tsx`, `frontend/components/dashboard/ConcentrationWarning.tsx`.

**Files/Directories To Modify:** `quant/risk_metrics.py` (add cluster-detection utility), `workers/slow_path_worker.py`, `frontend/app/dashboard/page.tsx`.

**Database Changes:** None (existing JSONB columns, now populated).

**API Changes:** `GET /portfolios/{id}/risk` response gains populated `risk_contribution`/`correlation_flags` fields (already part of the schema, previously empty/unused).

**UI Changes:** Risk contribution list and concentration warning banner.

**Implementation Details:** The single-asset-portfolio edge case (F11) must hide this section entirely rather than showing a meaningless "100% concentrated" warning.

**Acceptance Criteria:** On the demo portfolio (which includes correlated semiconductor names per Assumption A4), the concentration warning correctly fires and names the correct correlated symbols; risk-contribution percentages are visibly different from raw allocation percentages, demonstrating the "you're not as diversified as you think" story.

**Testing:** Unit test for cluster detection against a synthetic correlation matrix with a known planted cluster; integration test confirming the demo portfolio produces the expected warning.

**Manual Verification:** Load the demo portfolio, confirm the concentration warning appears with the correct named symbols and a sensible correlation value.

**Git Commit Strategy:**
```
feat(quant): implement correlation cluster detection
feat(risk): surface risk contribution and concentration flags in risk state
feat(ui): build risk contribution list and concentration warning
test(quant): add cluster detection coverage
```

**Git Checkpoint:** The platform's core differentiator (risk contribution vs. allocation) is now fully visible and demo-ready.

**Known Risks:** Threshold choice (0.7) is a judgment call — document it as configurable and explain the choice in a code comment, consistent with the "no unexplained magic numbers" standard in §10.

**Definition of Done:** Correlation warnings and risk-contribution breakdown correctly computed, displayed, and tested against the demo portfolio.

---

### Phase 16 — HMM Market Regime Detection

**Objective:** F12 fully implemented — a shared, scheduled Hidden Markov Model regime signal (calm vs. stressed probability) visible on the dashboard.

**Why This Phase Exists:** Adds a second, earlier-warning signal layered on top of the threshold-based alerting from Phase 14, and is a strong, self-contained demo feature.

**Dependencies:** Phase 6 (a market benchmark's price history available), Phase 2 (Redis/Postgres).

**What Has Already Been Completed:** Per-portfolio risk metrics; no market-wide regime concept yet.

**What Needs To Be Done:**
- `quant/regime.py`: `fit_hmm(returns) -> HMMFit` using `hmmlearn.hmm.GaussianHMM(n_components=2)` on a benchmark return series (e.g. an equal-weighted or index proxy of the demo symbol universe); `forward_probability(fit, latest_observations)` returning the **filtered/forward** probability at the most recent timestep (explicitly not the smoothed Viterbi path — F12's key implementation detail); post-fit relabeling so the higher-variance state is always labeled "stressed," regardless of raw component index (F12's edge case).
- `workers/regime_worker.py`: scheduled refit (e.g. every 5 minutes), writes to a shared (non-portfolio-scoped) Redis key and a `regime_states` row.
- `GET /market/regime` (§7.6).
- Frontend: `RegimeBadge` component on the dashboard topbar/header area.

**Files/Directories To Create:** `quant/regime.py`, `workers/regime_worker.py`, `frontend/components/dashboard/RegimeBadge.tsx`.

**Files/Directories To Modify:** `docker-compose.yml` (add `regime_worker` service), `app/market/router.py` (add regime endpoint), `frontend/app/dashboard/page.tsx`.

**Database Changes:** First real writes to `regime_states`.

**API Changes:** `GET /market/regime`.

**UI Changes:** Regime badge.

**Implementation Details:** Keep this a single, shared signal reused across all portfolios (not recomputed per-portfolio) — it is a market-context signal, not a portfolio-specific one, which is also why it lives in its own scheduled worker rather than inside the slow-path worker.

**Acceptance Criteria:** The regime badge shows a plausible, updating probability; a manually-injected synthetic high-volatility period in a test fixture correctly shifts the labeled "stressed" probability upward, proving the relabeling logic is correct rather than coincidentally correct.

**Testing:** Unit test with a synthetic two-regime return series (calm period, then an artificially volatile period) asserting the forward probability correctly identifies the current regime at each point, and that the "stressed" label consistently tracks the higher-variance state across independent re-fits (guards against the label-swapping edge case).

**Manual Verification:** Watch the regime badge update across a scheduled refit cycle; sanity-check the value against recent real market volatility.

**Git Commit Strategy:**
```
feat(quant): implement HMM market regime detection with forward probabilities
feat(regime): implement scheduled regime refit worker
feat(ui): add market regime badge to dashboard
test(quant): add regime detection and label-stability coverage
```

**Git Checkpoint:** A live, demo-worthy market-context signal is now visible.

**Known Risks:** With only a handful of demo symbols, the benchmark return series may be noisy — document this as an acceptable MVP simplification and note that a real deployment would use a genuine market index feed.

**Definition of Done:** Regime badge live and updating; forward-probability and relabeling logic both covered by tests.


---

### Phase 17 — Decision Engine

**Objective:** F14 fully implemented — on a risk-budget breach, 2–3 ranked candidate actions are generated and displayed automatically.

**Why This Phase Exists:** Turns the platform from "a system that tells you something is wrong" into "a system that tells you what to consider doing about it" — the second most differentiated feature, and it depends on almost everything built so far (risk contribution for identifying a reduction candidate, Monte Carlo for evaluating outcomes, alerting for the trigger).

**Dependencies:** Phase 14 (breach trigger), Phase 15 (risk contribution, to identify the largest-risk-contributing position), Phase 12 (Monte Carlo, reused at a smaller path count for candidate evaluation).

**What Has Already Been Completed:** Breach alerts firing; risk contribution known; Monte Carlo engine available.

**What Needs To Be Done:**
- `workers/decision_engine_worker.py`: subscribes to the same breach-transition signal as the alerting logic (Phase 14); constructs 2–3 candidate weight vectors — "do nothing" (current weights), "reduce largest risk contributor" (reduce that position by a configurable percentage, redistribute to cash), "increase cash" (flat percentage shift to cash) — omitting the reduce-position candidate when there is no single clear largest contributor (F14's edge case); evaluates each candidate via a smaller/faster Monte Carlo run (e.g. 10K paths, synchronous, since this must accompany the alert promptly) using the already-existing `quant/monte_carlo.py`; ranks by `expected_return - λ · CVaR` (λ configurable); falls back to a deterministic mean-variance approximation if the Monte Carlo evaluation itself fails (F14's error-handling requirement) rather than blocking the alert.
- Persist to `decisions` (linked to the triggering `alerts` row); include the ranked candidates directly in the `alert` WS payload so the frontend can render them immediately alongside the alert banner.
- `GET /portfolios/{id}/decisions/latest` (§7.4) for REST/Slack-bot access.
- Frontend: `DecisionCard` × up to 3, rendered beneath an expanded `AlertBanner` (§4.6's Risk Event screen).

**Files/Directories To Create:** `workers/decision_engine_worker.py`, `app/alerts/decisions_service.py`, `frontend/components/dashboard/DecisionCard.tsx`.

**Files/Directories To Modify:** `docker-compose.yml` (add `decision_engine_worker` service), `app/alerts/router.py` (add the `decisions/latest` endpoint), `frontend/components/dashboard/AlertBanner.tsx` (expand to show decision cards).

**Database Changes:** First real writes to `decisions`.

**API Changes:** `GET /portfolios/{id}/decisions/latest`.

**UI Changes:** Decision cards under an expanded alert.

**Implementation Details:** This worker must be explicitly, structurally incapable of executing a trade — there is no code path anywhere in the system that submits an order; this is worth stating directly in the module's docstring given the product's advisory-only constraint (§1).

**Acceptance Criteria:** Triggering a real breach on the demo portfolio (via a deliberately low budget, as in Phase 14's test) results in 2–3 correctly-ranked decision cards appearing within a few seconds of the alert.

**Testing:** Unit test for candidate-generation logic (correct omission of the reduce-position candidate on a well-diversified portfolio); integration test for the full breach → decision-generation → WS-payload flow; a forced-failure test for the Monte Carlo fallback path.

**Manual Verification:** Trigger a real breach, confirm decision cards appear with sane, differentiated numbers across the three candidates.

**Git Commit Strategy:**
```
feat(decisions): implement candidate action generation
feat(decisions): implement Monte Carlo-based candidate ranking with fallback
feat(ui): build decision engine cards
test(decisions): add candidate generation and fallback coverage
```

**Git Checkpoint:** The platform now closes the loop from "something changed" to "here's what to consider" — its second core differentiator is live.

**Known Risks:** Running even a reduced Monte Carlo synchronously for up to 3 candidates could add noticeable alert latency — benchmark this during the phase and reduce the candidate-evaluation path count further if needed to keep the alert-to-decision-card delay comfortably under a few seconds.

**Definition of Done:** Decision cards correctly generated, ranked, persisted, and displayed for a real breach; fallback path tested.

---

### Phase 18 — AI Risk Analyst (LangGraph Explain + What-If)

**Objective:** F15 fully implemented — a LangGraph agent (Claude API) that explains risk state and answers what-if questions, strictly separated from all numeric computation.

**Why This Phase Exists:** Makes every quantitative feature built so far accessible in plain language, while its core architectural point (AI never calculates) is the single most interview-defensible design decision in the whole system — sequenced last among the "core loop" features since it narrates results that must already exist and be correct.

**Dependencies:** Phase 10/15 (risk state to explain), Phase 8's `quant/scenarios.py` (the deterministic what-if evaluator, built in this phase).

**What Has Already Been Completed:** All numeric features the AI will narrate over.

**What Needs To Be Done:**
- `quant/scenarios.py`: `evaluate_scenario(portfolio, shocks: dict[str, float]) -> ScenarioResult` — a purely deterministic function applying a percentage shock per symbol and recomputing portfolio-level VaR/CVaR/expected impact via the existing quant engine. This function is the *only* thing that ever produces a number in the what-if flow.
- `app/ai/tools.py`: two LangGraph tools — `explain_risk_state(risk_snapshot_id)` (fetches already-computed numbers, returns them as structured data for the agent to narrate, never invents a number) and `parse_and_evaluate_scenario(question: str, portfolio_id)` (the agent's first step converts the free-text question into a strictly-typed Pydantic `ScenarioRequest` — validated and rejected if malformed, per §11's input-validation requirement — then calls `evaluate_scenario` from `quant/scenarios.py`, never estimates the outcome itself).
- `app/ai/agent.py`: the LangGraph graph wiring these two tools with a system prompt that explicitly instructs the model it must call a tool for every numeric claim and must state any interpretive assumption (e.g. "market" mapped to a default −10% diversified shock) explicitly in its response, per F15's ambiguous-input edge case.
- `POST /ai/explain`, `POST /ai/what-if` (§7.5); persisted to `ai_conversations`/`ai_messages`.
- Frontend: the AI chat panel per §4.6, with suggested-question chips, rendering the *structured numeric result* directly (not parsed from the AI's prose) alongside the narration text.

**Files/Directories To Create:** `quant/scenarios.py`, `app/ai/*`, `frontend/components/ai/*`, `frontend/app/dashboard` AI-panel integration.

**Files/Directories To Modify:** `app/main.py` (register ai router).

**Database Changes:** First real writes to `ai_conversations`/`ai_messages`.

**API Changes:** `POST /ai/explain`, `POST /ai/what-if`.

**UI Changes:** AI explain/what-if chat panel.

**Implementation Details:** Rate-limit `/ai/what-if` (§11: 30/hour/user) both to control LLM cost and to prevent the deterministic scenario evaluator from being hammered.

**Acceptance Criteria:** Asking "what if NVDA falls 20%" produces a correctly-parsed `{"NVDA": -0.20}` scenario, a real recomputed CVaR from the quant engine, and a plain-language narration referencing those exact numbers; asking an ambiguous question ("what if the market crashes") results in either a clarifying question or an explicitly-stated default assumption, never a silently guessed magnitude.

**Testing:** Unit tests for `evaluate_scenario` (deterministic, no LLM involved — pure quant-engine correctness); a mocked-LLM integration test asserting the tool-calling flow produces a validated `ScenarioRequest` from a range of sample questions, and that a malformed/adversarial tool-call output is rejected by Pydantic validation rather than silently passed through; a test for the LLM-timeout fallback (numbers render, narration shows "unavailable").

**Manual Verification:** Ask several real what-if questions in the browser, confirm the numbers are correct and match a manually-computed check; deliberately ask an ambiguous question and confirm the assumption is stated, not hidden.

**Git Commit Strategy:**
```
feat(quant): implement deterministic scenario evaluation
feat(ai): implement LangGraph explain and what-if tools
feat(ai): wire explain and what-if endpoints
feat(ui): build AI chat panel
test(ai): add scenario evaluation and tool-calling validation coverage
```

**Git Checkpoint:** Every quantitative feature in the product is now explainable in plain language, with a demonstrably hallucination-resistant architecture.

**Known Risks:** LLM API cost/latency variability — the per-user rate limit and the numeric-first response design (numbers always render even if narration is slow/fails) directly mitigate both the cost risk and the UX risk.

**Definition of Done:** Explain and what-if both fully working and tested; the tool-calling/validation boundary verified by a test that specifically tries to make the agent bypass it.

---

### Phase 19 — Historical Replay & Kupiec Backtest

**Objective:** F16 and F13 fully implemented — the demo-closing feature, replaying the current portfolio through a real historical stress period and validating the risk model's own accuracy.

**Why This Phase Exists:** Sequenced last among the quant features because it depends on the full risk engine (Phase 10), the risk-budget state machine (Phase 14), and produces the platform's single most convincing "proof of value" moment — a natural capstone before moving to the frontend polish and secondary-client phases.

**Dependencies:** Phase 14 (state machine and thresholds to replay against), Phase 10 (the quant engine being replayed).

**What Has Already Been Completed:** A fully correct, live risk engine; no historical dataset or replay mechanism yet.

**What Needs To Be Done:**
- Populate `backend/data/historical/` with the checked-in historical OHLC dataset (Assumption A10) covering the demo symbol universe across at least one real stress period; implement `scripts/seed_historical_dataset.py` for real, loading this into a `historical_prices` table (added via a new migration in this phase).
- `quant/backtest.py`: the Kupiec proportion-of-failures likelihood-ratio test, implemented directly from its closed-form statistic, compared against a chi-squared critical value at a configurable significance level; explicit "insufficient sample size" result below a minimum number of replay days (F13's edge case).
- `app/replays/service.py` + `router.py`: `POST /replays` enqueues an `arq` job (same async-job pattern as Phase 12) that iterates the historical dataset day by day, applies it to the *current* portfolio's holdings, runs the Phase 10 quant engine per day, records each day's state to `replay_daily_states`, tracks every threshold-crossing against the *current* risk budget (Phase 14's thresholds), and on completion computes and stores the Kupiec backtest (`backtest_results`).
- Frontend: the Historical Replay screen per §4.6 (period selector, animated chart with a breach-day marker, backtest badge).

**Files/Directories To Create:** `quant/backtest.py`, `app/replays/*`, a new Alembic migration for `historical_prices`, `frontend/app/dashboard/replay/page.tsx`, `frontend/components/replay/*`.

**Files/Directories To Modify:** `scripts/seed_historical_dataset.py` (real implementation), `workers/job_worker.py` (add the replay job function), `app/main.py` (register replays router).

**Database Changes:** New `historical_prices` table (migration); first real writes to `replays`, `replay_daily_states`, `backtest_results`.

**API Changes:** `POST /replays`, `GET /replays/{id}`.

**UI Changes:** Full Historical Replay screen.

**Implementation Details:** A symbol held in the current portfolio but absent from the checked-in historical dataset must be excluded from the replay with an explicit note (F16's edge case), never silently dropped without surfacing that fact.

**Acceptance Criteria:** Running a replay on the demo portfolio against the seeded historical stress period produces a day-by-day risk trajectory, correctly marks the day the current risk budget would have been breached, and produces a Kupiec backtest result (pass/fail with the underlying rates) — this is the exact sequence to be used in the eventual demo/pitch.

**Testing:** Unit test for the Kupiec statistic against a textbook worked example (known input counts → known statistic/p-value); integration test for the full replay job lifecycle; a test for the "symbol missing from historical dataset" edge case.

**Manual Verification:** Run the replay in the browser end-to-end, confirm the breach marker lines up with the actual historical drawdown, and that the backtest badge shows a sensible pass/fail result.

**Git Commit Strategy:**
```
feat(data): seed checked-in historical price dataset
feat(quant): implement Kupiec backtest
feat(replays): implement historical replay job and daily state tracking
feat(ui): build historical replay screen with backtest badge
test(quant): add Kupiec statistic correctness coverage
test(replays): add replay lifecycle and missing-symbol coverage
```

**Git Checkpoint:** The platform's full demo narrative — onboard, watch, alert, explain, simulate, decide, and now *prove it retrospectively* — is complete end-to-end.

**Known Risks:** Sourcing a clean, sufficiently long historical dataset for the exact demo symbol universe — budget real research time for this rather than treating it as a trivial data-entry task; if a symbol's full history isn't available, adjust the demo symbol universe rather than compromising the replay's integrity.

**Definition of Done:** Full replay-to-backtest flow working and tested against the checked-in dataset; this is the last "core feature" phase before frontend/secondary-client/production phases.


---

### Phase 20 — Frontend Application: Design System Consolidation & Full Polish

**Objective:** F18 fully implemented — every screen from §4.6 is built, styled per the §4 design system, and consistent; the previously feature-by-feature-built UI is unified into a coherent product.

**Why This Phase Exists:** Phases 5–19 each added UI incrementally, prioritizing function over polish to keep momentum on the backend/quant work. This phase is where the product becomes visually and interactionally coherent — deliberately sequenced after all data/features exist, so design decisions are made against real data, not placeholders.

**Dependencies:** Phases 5–19 (every screen's underlying feature must already work).

**What Has Already Been Completed:** Every screen exists in a functional-but-unpolished state, built incrementally.

**What Needs To Be Done:**
- Build out `components/ui/` as the actual shared primitive library (Button, Card, Input, Modal, Dropdown, Tabs, Toast, Tooltip, Table) per §4.5's exact specification, then refactor every existing screen to use these primitives instead of any one-off styling introduced during earlier phases.
- Implement the full color/typography/spacing token system (`styles/tokens.css`) and audit every existing component for hardcoded values, replacing them with tokens.
- Implement loading skeletons (matching real content shape), empty states, and error states for every screen per §4.5/§4.6, including states that were stubbed simply during earlier phases (e.g. Phase 10's "insufficient data" state gets its final visual treatment here).
- Implement responsive behavior (sidebar → bottom nav, grid reflow, AI panel → full-screen sheet on mobile) across all screens.
- Implement dark/light mode toggle with the full token swap.
- Accessibility pass: keyboard navigation, focus-visible states, contrast verification, non-color-only signaling for risk states.
- Micro-interactions: number-update flash, budget-bar animated transitions, per §4.5.

**Files/Directories To Create:** `frontend/components/ui/*` (full primitive set), `frontend/styles/tokens.css`.

**Files/Directories To Modify:** Every existing page/component built in Phases 5–19, refactored to use the new primitives and tokens.

**Database Changes:** None.

**API Changes:** None (this phase is frontend-only).

**UI Changes:** The entire application, unified.

**Implementation Details:** This phase is explicitly a refactor-and-polish phase, not a new-feature phase — resist the temptation to add functionality here; any gap discovered belongs in a tracked follow-up, not a scope-creeping addition mid-polish.

**Acceptance Criteria:** Every screen in §4.6 matches its specification; no screen has a hardcoded color/spacing value outside the token system; the app is fully usable (all core flows) at a 375px mobile viewport and in both light and dark mode.

**Testing:** Component tests (Vitest + RTL) for every `components/ui/` primitive; visual regression is out of scope for MVP (documented as a future addition, e.g. Chromatic) but manual side-by-side comparison against the §4.6 wireframes is part of manual verification.

**Manual Verification:** Full click-through of every screen on desktop and mobile viewports, in both themes, using the manual QA checklist from §13.

**Git Commit Strategy:**
```
feat(ui): build shared design-system primitive components
refactor(ui): migrate all screens to design tokens and shared primitives
feat(ui): implement loading, empty, and error states across all screens
feat(ui): implement responsive layout and mobile behavior
feat(ui): implement dark/light mode toggle
feat(ui): accessibility pass (keyboard nav, contrast, non-color signaling)
```

**Git Checkpoint:** A visually and interactionally coherent, fully responsive, accessible product.

**Known Risks:** Refactoring every screen at once risks large, hard-to-review diffs — break this phase's commits by primitive/screen rather than as one giant commit, per the Conventional Commits discipline already established.

**Definition of Done:** Every §4.6 screen spec is met; component tests pass; manual QA checklist (desktop, mobile, both themes) passes.

---

### Phase 21 — Slack Bot Second Client

**Objective:** F17 fully implemented — a working Slack app exposing `/risklens status`, `/risklens whatif`, `/risklens alerts`, proving the backend's multi-client reusability.

**Why This Phase Exists:** Deliberately sequenced after the core web product is fully feature-complete and polished (Phase 20) — the Slack bot's entire value proposition is reusing an already-correct API, so it should be near-trivial by this point if the API boundary (§5.5) was respected throughout.

**Dependencies:** Phase 4 (auth, extended here with API tokens), Phase 10/15 (`GET /portfolios/{id}/risk`), Phase 18 (`POST /ai/what-if`), Phase 14 (`GET /alerts`).

**What Has Already Been Completed:** A fully working REST API covering everything the bot needs.

**What Needs To Be Done:**
- `POST /auth/api-tokens` (§7.1) implemented for real now (scoped read + what-if only, hashed at rest, individually revocable — §11).
- `slack_bot/app.py`: Slack Bolt app; `/risklens login` flow issuing and linking an API token to a Slack user ID (stored in `api_tokens`, associated via a lightweight `slack_links` mapping — added via a small migration in this phase); `/risklens status`, `/risklens whatif <symbol> <pct>`, `/risklens alerts` commands calling the existing REST endpoints with the linked token and formatting the JSON response as Slack Block Kit messages.
- Add the `slack_bot` service to `docker-compose.yml` and its own lightweight Dockerfile (reusing `backend/Dockerfile.worker`'s base pattern).

**Files/Directories To Create:** `slack_bot/*`, a small migration for `slack_links`.

**Files/Directories To Modify:** `app/auth/router.py` (implement the api-tokens endpoint for real), `docker-compose.yml`.

**Database Changes:** `slack_links` table (`slack_user_id`, `user_id`, `created_at`).

**API Changes:** `POST /auth/api-tokens` goes live.

**UI Changes:** None (Slack is the client).

**Implementation Details:** The bot must never expose write/import capability (§F17's constraint) — enforce this by only ever requesting `read`/`whatif` scopes when issuing the token during the link flow, and by having the API itself reject a write-scoped call from a token lacking that scope (defense in depth, not just "the bot doesn't offer the command").

**Acceptance Criteria:** A linked Slack user can run all three commands and get correctly formatted, accurate responses matching what the web dashboard shows for the same portfolio.

**Testing:** Integration tests for the link flow and each command's happy path and unlinked-account path (F17's edge case); a security test explicitly asserting a read/whatif-scoped token is rejected by a write endpoint.

**Manual Verification:** Run all three commands in a real (or sandboxed) Slack workspace, confirm output matches the web dashboard.

**Git Commit Strategy:**
```
feat(auth): implement scoped API token issuance
feat(slack): implement Slack Bolt app with account linking
feat(slack): implement status, whatif, and alerts commands
test(slack): add command and scope-enforcement coverage
```

**Git Checkpoint:** A second, genuinely independent client proves the API is a real product boundary, not UI-coupled logic.

**Known Risks:** Slack app review/approval processes if ever published publicly — out of scope for MVP (a private/sandboxed workspace app is sufficient for the resume/demo purpose); document this distinction clearly.

**Definition of Done:** All three commands working end-to-end in a real Slack workspace; scope enforcement verified by test.

---

### Phase 22 — Testing Hardening & Security Pass

**Objective:** Close testing and security gaps deliberately deferred during feature-building phases; reach the coverage and hardening bar implied by §11 and §13 across the whole codebase, not just per-feature.

**Why This Phase Exists:** Individual phases included their own tests, but a dedicated pass is needed to catch cross-feature interactions, fill coverage gaps, and apply security measures that only make sense once the full surface area exists (e.g. a comprehensive rate-limit review across every endpoint at once).

**Dependencies:** All feature phases (Phases 1–21).

**What Has Already Been Completed:** Per-feature unit/integration tests; ad hoc security measures applied incrementally.

**What Needs To Be Done:**
- Run and act on `pip-audit` and `npm audit`/Dependabot findings; upgrade or patch any high-severity dependency issue.
- Full CORS configuration review (only the deployed frontend origin allowed — §5/§11).
- Full rate-limit review across every endpoint in §7 (not just the ones called out individually in earlier phases) — confirm each state-changing or expensive endpoint has an appropriate limit.
- End-to-end (Playwright) tests for the five critical journeys listed in §13.
- Fill any unit/integration coverage gaps identified via a coverage report (target: high coverage on `quant/` — already enforced at 100% intent in Phase 8 — and meaningful coverage on every `service.py`).
- Manually attempt to break the F15 tool-calling boundary (adversarial prompt injection attempting to make the AI report a fabricated number) and confirm the Pydantic-validated, quant-engine-sourced numeric path cannot be bypassed.
- Manually attempt cross-user data access on every domain (portfolios, alerts, simulations, replays, decisions) with two real test accounts, confirming the row-level ownership checks (§5.6) hold everywhere, not just where explicitly tested per-phase.

**Files/Directories To Create:** `frontend/tests/e2e/*` (the five critical journeys), any missing `tests/unit`/`tests/integration` files identified by the coverage review.

**Files/Directories To Modify:** Dependency version bumps as needed; rate-limit configuration on any endpoint found lacking one.

**Database Changes:** None expected.

**API Changes:** None expected (hardening, not new features) — unless a security review surfaces a genuine gap, which is documented as a fix commit, not treated as new scope.

**UI Changes:** None expected.

**Implementation Details:** Treat this phase as an audit against the requirements already written in §11/§13, not as an open-ended "find more things to build" phase.

**Acceptance Criteria:** No high-severity dependency vulnerabilities; every endpoint has an appropriate rate limit; all five E2E journeys pass; cross-user data access is confirmed blocked on every domain by manual test; the AI tool-calling boundary is confirmed unbypassable by a deliberate adversarial attempt.

**Testing:** This entire phase *is* testing — see "What Needs To Be Done."

**Manual Verification:** The cross-user and prompt-injection checks above are explicitly manual, documented steps, not just automated tests — record the steps taken and results in the PR description for this phase.

**Git Commit Strategy:**
```
chore(security): resolve dependency vulnerabilities
chore(security): review and complete rate limiting across all endpoints
test(e2e): add critical user journey coverage
test(coverage): fill unit/integration coverage gaps
docs(security): document manual penetration/ownership-check findings
```

**Git Checkpoint:** A codebase that has been deliberately, comprehensively audited against its own stated security and testing bar — not just incrementally tested feature by feature.

**Known Risks:** This phase can uncover real, sometimes uncomfortable gaps (e.g. a forgotten ownership check on a less-visited endpoint) — treat any such finding as a required fix before moving on, not a "known issue" to defer to Phase 24.

**Definition of Done:** Every acceptance criterion above is met and documented.

---

### Phase 23 — CI/CD Pipeline & Deployment

**Objective:** F19/F20 fully implemented — automated CI on every PR, automated deployment on merge to `main`, and a live, working production deployment.

**Why This Phase Exists:** Sequenced after Phase 22's hardening so the first automated deployment ships a codebase that has already passed a full security/testing review, not a moving target.

**Dependencies:** Phase 22 (a codebase ready to be trusted in CI/CD), Phase 2 (Docker images already defined).

**What Has Already Been Completed:** A fully tested, hardened, Dockerized application running correctly locally via Compose.

**What Needs To Be Done:**
- `.github/workflows/ci.yml`: on every PR — install deps, run `ruff`/`black --check`/`mypy` (backend), `eslint`/`tsc --noEmit` (frontend), run the full unit + integration test suite (backend, against a Postgres/Redis service container) and the frontend unit/component suite; build (but do not push) Docker images to confirm they build cleanly; run Playwright E2E tests against a `docker compose`-launched full stack.
- `.github/workflows/deploy.yml`: on merge to `main` — build and push backend/worker Docker images; trigger Render deploy hooks for each service (API + each worker + Slack bot); trigger a Vercel deploy for the frontend (Vercel's native GitHub integration can largely handle this automatically — document the exact configuration used).
- Configure Render: one Postgres instance, one Redis instance, one web service (API), one service per worker (`ingestion_worker`, `fast_path_worker`, `slow_path_worker`, `garch_worker`, `regime_worker`, `decision_engine_worker`, `job_worker`, `slack_bot`) — each built from the same repo with a distinct start command, sharing the `DATABASE_URL`/`REDIS_URL` environment variables.
- Configure Vercel: connect the `frontend/` directory as the project root, set `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` to the deployed Render API's public URL.
- Run the Alembic migration against the production database as part of the deploy step (a Render deploy hook or a one-off job run before the API service restarts).
- Verify the full production deployment end-to-end (register a real account, import a demo portfolio, observe a live tick update, run a real simulation).

**Files/Directories To Create:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `render.yaml` (Render's infrastructure-as-code service definition, documenting every service in one file), `docs/setup.md` (deployment-specific instructions).

**Files/Directories To Modify:** `.env.example` files updated to reflect exactly what production needs (separate from local-dev-only values).

**Database Changes:** Migration run against the production database for the first time.

**API Changes:** None (deployment, not features).

**UI Changes:** None.

**Implementation Details:** Store all production secrets (Finnhub key, Anthropic key, Slack tokens, JWT signing secret, database URL) exclusively in Render's/Vercel's secret managers — never in `render.yaml` or any committed file.

**Acceptance Criteria:** A PR triggers CI and must pass before merge is allowed (branch protection configured); a merge to `main` results in a fully automated deployment with no manual step; the deployed application is fully functional end-to-end, not just "the health check passes."

**Testing:** CI itself is the test harness for this phase; additionally, a smoke test hitting the *deployed* `/health` and a couple of key read endpoints runs as the final step of the deploy workflow, failing the deploy (and ideally alerting) if the live environment isn't actually healthy post-deploy.

**Manual Verification:** A full manual walkthrough of the live, deployed application covering the same critical journeys as the E2E tests (§13), run against production URLs, not localhost.

**Git Commit Strategy:**
```
ci(github-actions): add lint, type-check, and test workflow
ci(github-actions): add build and deploy workflow
chore(deploy): add Render service definitions
docs(setup): document production deployment configuration
```

**Git Checkpoint:** A fully automated CI/CD pipeline with a live, working, publicly accessible deployment.

**Known Risks:** Free/low-cost tiers on Render can have cold-start delays for infrequently-used services (e.g. a worker that only fires occasionally) — document this as an expected characteristic of the demo deployment, not a bug, and note the paid-tier upgrade path if this becomes a real problem during a live demo.

**Definition of Done:** CI blocks bad merges; deploys are fully automated; the live production URL is fully functional end-to-end.

---

### Phase 24 — Final QA, Bug Elimination & Production Readiness

**Objective:** The final phase — full regression pass across the entire, now-deployed application; elimination of all discovered critical bugs; a project-wide readiness verification against §16/§17's checklists.

**Why This Phase Exists:** No individual feature phase, however carefully executed, substitutes for a holistic pass across the finished, integrated, deployed product — this phase exists specifically to catch what only becomes visible once everything is together and running in its real environment.

**Dependencies:** All previous phases.

**What Has Already Been Completed:** A fully featured, tested, hardened, deployed application.

**What Needs To Be Done:**
- Full regression walkthrough of every user flow in §3.2/§4.6, on the live deployed URL, on both desktop and mobile, in both themes.
- Full API testing pass against the live deployment (not just CI's ephemeral test environment) — every endpoint in §7 exercised at least once against production.
- Database review: confirm all indexes exist as specified in production (not just in the migration file — verify against the live schema), confirm no orphaned data from testing is left in a state that would confuse a first-time demo viewer.
- Security review repeat (a condensed version of Phase 22's checks) specifically against the production environment and its actual configured secrets/CORS/rate limits.
- Performance review: confirm real-tick-to-dashboard-update latency is acceptable in production (not just in local Docker Compose, where network characteristics differ); confirm a 100K-path Monte Carlo simulation completes in a reasonable time against production compute.
- Accessibility review repeat against the deployed frontend.
- Remove all dead code, unused dependencies, and any debug/placeholder code paths left over from incremental development (e.g. Phase 6's fixed demo symbol list, if any trace of it remains after Phase 7 superseded it).
- Verify environment variable documentation (`.env.example` files) is complete and accurate against what production actually requires.
- Verify the README is complete: project description, setup instructions (local + link to `docs/setup.md` for production), architecture summary link, and a clear statement of what is MVP vs. documented future work (§2's assumptions table, and the out-of-scope items from §3.1).
- Final end-to-end verification: a single, uninterrupted walkthrough from a brand-new account through the entire demo narrative (onboard → live dashboard → simulate → EVT comparison → trigger a breach → decision cards → AI explain/what-if → historical replay → Kupiec badge → Slack bot commands), performed exactly as it would be performed for an actual demo/interview.

**Files/Directories To Create:** None expected (this phase fixes and verifies, it does not add features).

**Files/Directories To Modify:** Any file touched by a discovered bug fix; `README.md` finalized.

**Database Changes:** None expected beyond routine fixes if a schema issue is discovered.

**API Changes:** None expected.

**UI Changes:** Bug fixes only.

**Implementation Details:** Every bug found in this phase gets its own small, clearly-scoped fix commit (`fix(scope): description`) rather than being batched into one large "final fixes" commit — the Git history should remain readable and intentional through to the very end, per §14's stated principle.

**Acceptance Criteria:** Every item in the project-wide Definition of Done (§16) is checked off against the live, deployed application.

**Testing:** Full regression per "What Needs To Be Done" above; the automated test suite (all layers) passes in CI at the exact commit tagged as the release.

**Manual Verification:** The single uninterrupted end-to-end demo walkthrough described above, performed and confirmed working without any manual workaround or "just ignore that part" caveat.

**Git Commit Strategy:**
```
fix(<scope>): <description of each discovered issue, one per commit>
chore(cleanup): remove dead code and unused dependencies
docs(readme): finalize project README
chore(release): tag v1.0.0
```

**Git Checkpoint:** A tagged `v1.0.0` release representing a genuinely finished, demo-ready, production-deployed product.

**Known Risks:** The temptation to keep adding "just one more feature" during this phase instead of finishing — explicitly resist this; any good new idea discovered here goes into a documented backlog (§2-style assumptions/future-work list), not into this release.

**Definition of Done:** §16's project-wide Definition of Done is fully satisfied; `v1.0.0` tagged; the end-to-end demo walkthrough succeeds without caveats.


---

## 15. Phase Dependency Map

```text
Phase 1 (Foundation)
   ↓
Phase 2 (Docker/Local Dev)
   ↓
Phase 3 (Database Foundation)
   ↓
Phase 4 (Auth) ──────────────┐
   ↓                          │
Phase 5 (Portfolio Ingestion) │
   ↓                          │
Phase 6 (Market Data Ingestion)
   ↓
Phase 7 (Reverse Index)
   ↓
Phase 8 (Quant Engine) ◄──────┘  [can be developed in parallel with Phases 4–7;
   ↓                              sequenced here because Phase 9 needs it]
Phase 9 (Fast Path + WS)
   ↓
Phase 10 (Slow Path Risk Recompute)
   ↓
   ├──► Phase 11 (GARCH) ──► Phase 12 (Monte Carlo) ──► Phase 13 (EVT)
   ├──► Phase 14 (Risk Budget & Alerting)
   └──► Phase 15 (Correlation Detector)
   ↓
Phase 16 (HMM Regime Detection)   [depends only on Phase 6, can run parallel to 11–15]
   ↓
Phase 17 (Decision Engine)  [depends on 12, 14, 15]
   ↓
Phase 18 (AI Risk Analyst)  [depends on 10, 15]
   ↓
Phase 19 (Historical Replay & Kupiec)  [depends on 14]
   ↓
Phase 20 (Frontend Polish)  [depends on ALL of 5–19]
   ↓
Phase 21 (Slack Bot)  [depends on 4, 10/15, 14, 18]
   ↓
Phase 22 (Testing & Security Hardening)  [depends on ALL feature phases]
   ↓
Phase 23 (CI/CD & Deployment)
   ↓
Phase 24 (Final QA & Production Readiness)
```

**Parallelizable work:** Phase 8 (Quant Engine) has no real dependency on Phases 4–7 and can be built by a second developer concurrently. Phases 11 (GARCH), 14 (Alerting), 15 (Correlation), and 16 (Regime) are mutually independent once Phase 10 exists and can be split across developers/sequenced in any order among themselves. Everything from Phase 17 onward has hard dependencies and should not be parallelized without care.

---

## 16. Project-Wide Definition of Done

The project is not complete until every item below is true, verified against the **live, deployed** application:

- [ ] Every feature in §3.1's Core list (F1–F20) works correctly end-to-end
- [ ] All five critical E2E user journeys (§13) pass in CI and manually against production
- [ ] UI matches the §4 design system on every screen — no unstyled/placeholder screens remain
- [ ] Responsive behavior verified on a real mobile viewport, not just DevTools emulation
- [ ] Every API endpoint in §7 integration-tested for its happy path, an auth/ownership failure, and a validation failure
- [ ] Database schema in production matches §8 exactly, including all indexes and constraints
- [ ] Authentication and authorization (row-level ownership) verified on every domain by explicit cross-user manual test
- [ ] Every documented validation rule (§3.2's per-feature specs) enforced and tested
- [ ] Every documented error state renders a specific, actionable message — no raw stack traces reach the client
- [ ] Every documented loading state uses the correct pattern (skeleton vs. determinate progress bar per §4.5)
- [ ] Every documented empty state has a clear primary action, not blank space
- [ ] Every documented edge case (per-feature, §3.2) has a corresponding test
- [ ] Full automated test suite (unit, integration, component, E2E) passes at the release commit
- [ ] No known critical bugs remain (Phase 24's regression pass is clean)
- [ ] No console errors/warnings on any screen in production
- [ ] No broken links, buttons, or dead-end UI states
- [ ] No placeholder/mock functionality remains except the explicitly-documented out-of-scope items (§3.1, §2)
- [ ] Security basics implemented and verified (§11) — auth, rate limiting, CORS, input validation, secrets management, no credential storage
- [ ] Performance acceptable in production: sub-second fast-path updates, risk recompute within the batching window, Monte Carlo completing within a reasonable bound at 100K paths
- [ ] CI/CD pipeline fully automated; deployment works with zero manual steps beyond a `main` merge
- [ ] Environment configuration fully documented in `.env.example` files and `docs/setup.md`
- [ ] README complete: description, setup, architecture summary, MVP-vs-future-work distinction

---

## 17. Production Readiness Checklist

- [ ] **Build:** Docker images for API and every worker build cleanly in CI; frontend builds cleanly via `next build`
- [ ] **Deployment:** Render services (API + 7 workers + Slack bot) and Vercel frontend all deployed and healthy
- [ ] **Environment variables:** every required variable documented and set in Render's/Vercel's secret managers; none committed to the repo
- [ ] **Database migrations:** Alembic migration history applied cleanly to the production database; `alembic upgrade head` is part of the deploy workflow
- [ ] **Database backups:** Render's managed Postgres automatic daily backup enabled (default on Render's managed Postgres — confirmed, not assumed)
- [ ] **Logging:** structured JSON logs flowing from every service, viewable in Render's log dashboard
- [ ] **Monitoring:** `/health` endpoint on every service checked by Render's platform health checks
- [ ] **Error tracking:** Sentry receiving events from both frontend and backend in production
- [ ] **Security:** CORS restricted to the production frontend origin; rate limits active; no debug mode enabled in any production service
- [ ] **API rate limits:** verified active against the live deployment, not just locally
- [ ] **Performance:** verified acceptable against production compute, not just local Docker Compose
- [ ] **Accessibility:** verified against the deployed frontend
- [ ] **Documentation:** `README.md`, `docs/setup.md`, and this `implementation.md` all current and accurate as of the release
- [ ] **Rollback strategy:** Render supports one-click rollback to a previous successful deploy per service; Vercel supports instant rollback to a previous deployment — both confirmed usable, not just assumed available
- [ ] **Disaster recovery:** database backup restore process understood and documented (even if never exercised for this project's scale) — a single paragraph in `docs/setup.md` is sufficient for this project's scope
- [ ] **Operational procedures:** a short "if X breaks, check Y" troubleshooting section in `docs/setup.md` covering the most likely real failure modes (Finnhub disconnect, a worker crash-looping, a stuck simulation job)

---

## 18. Developer Experience

### Local Setup
1. Clone the repository.
2. Copy `backend/.env.example` → `backend/.env`, `frontend/.env.example` → `frontend/.env`, root `.env.example` → `.env`; fill in `FINNHUB_API_KEY` and `ANTHROPIC_API_KEY` (both have free-tier signup flows documented in `docs/setup.md`).
3. `docker compose up` — brings up Postgres, Redis, the API, every worker, and the frontend.
4. `docker compose exec api alembic upgrade head` — applies migrations.
5. `docker compose exec api python scripts/seed_demo_portfolio.py --user-email you@example.com` (after registering a user via the UI) — optional, for exploring the demo portfolio without the UI flow.
6. Visit `http://localhost:3000`.

### Prerequisites
Docker & Docker Compose; a Finnhub free-tier API key; an Anthropic API key; (Node/Python are not required on the host if developing entirely inside containers, though local editor tooling benefits from a local `venv`/`node_modules` — both are documented as optional in `docs/setup.md`).

### Running Tests
- Backend: `docker compose exec api pytest` (unit + integration); `docker compose exec api pytest tests/unit -k quant` to run only the quant engine's suite.
- Frontend: `docker compose exec frontend npm run test` (unit/component); `npm run test:e2e` (Playwright, run against a full Compose stack).

### Linting/Formatting
- Backend: `ruff check . && black --check .`; auto-fix with `ruff check --fix . && black .`.
- Frontend: `npm run lint`; `npm run format`.
- Both run automatically via `pre-commit` on every commit, and again in CI as a blocking check.

### Building
- Backend/worker images: `docker build -f backend/Dockerfile .` / `docker build -f backend/Dockerfile.worker --build-arg WORKER=slow_path_worker .`.
- Frontend: `npm run build` (or the Vercel-managed equivalent in production).

### Deployment
See `docs/setup.md` for the full Render/Vercel configuration walkthrough produced in Phase 23.

### Troubleshooting Common Issues
- **Dashboard shows stale/frozen data:** check `ingestion_worker` logs for a Finnhub disconnect; check it's within market hours (free-tier delayed data may be sparse outside them).
- **Simulation stuck at "pending":** check `job_worker` (arq) is running and connected to the same Redis instance as the API.
- **No alerts ever fire:** confirm a risk budget has actually been set for the portfolio (`GET /portfolios/{id}/risk-budget` — dashboard shows an explicit prompt if none exists).

### Coding Conventions
Per §9/§10 — naming conventions, small focused functions, the `quant/`/`components/ui/` reuse-boundary rule, short non-obvious-only comments.

### Branch Naming
`type/short-description`, e.g. `feat/monte-carlo-engine`, `fix/alert-oscillation-guard`.

### Commit Conventions
Conventional Commits, per §14's phase-by-phase examples throughout.

### PR Expectations & Review Checklist
- References the relevant phase from §14.
- Includes/updates tests per §13's applicable category.
- Passes CI (lint, type-check, tests, Docker build) before merge is enabled.
- For any change touching `quant/`, includes a test asserting the specific numeric behavior changed/added, not just a passing build.
- For any change touching a domain that reads/writes user-owned data, includes an explicit ownership-check consideration in the PR description.

---

## 19. Important Engineering Principle

This project is optimized in the order: **Correctness → Maintainability → Security → User Experience → Performance → Scalability.** Concretely, this shows up throughout the plan above as: the quant engine (Phase 8) is tested exhaustively *before* anything is built on top of it (correctness first); the interface/registry pattern in §10 exists so features can be added or swapped without touching unrelated code (maintainability); row-level ownership and the AI tool-calling boundary are treated as non-negotiable from Phase 4/18 onward, not bolted on in Phase 22 (security); the design system (Phase 20) is deliberately sequenced *after* every feature works, not before (UX polish follows function); and explicit "defer until scale requires it" call-outs (§12) keep the team from spending time on performance/scalability work the project doesn't yet need, in service of finishing a correct, secure, usable product first.


---

## 20. Final Implementation Roadmap

### Complete Phase Roadmap

| Phase | Name | Main Goal | Dependencies | Expected Git Milestone |
|---|---|---|---|---|
| 1 | Project Foundation & Tooling | Runnable, lintable monorepo skeleton | None | `chore(tooling): configure lint/format/pre-commit` |
| 2 | Docker & Local Dev Environment | Full stack runs via one command | 1 | `chore(docker): add docker-compose for local development` |
| 3 | Database Foundation | Full schema live in Postgres | 2 | `feat(db): add initial Alembic migration` |
| 4 | Authentication & Authorization | Working register/login/refresh/logout | 3 | `feat(auth): add current-user dependency for protected routes` |
| 5 | Portfolio Ingestion | Demo/CSV/manual portfolio entry | 4 | `feat(ui): build onboarding flow` |
| 6 | Market Data Ingestion Service | Live Finnhub ticks flowing into Redis | 2, 5 | `feat(ingestion): publish ticks to Redis Stream with reconnect/backoff` |
| 7 | Symbol Reverse Index & Routing | Demand-driven, restart-safe subscriptions | 5, 6 | `feat(ingestion): subscribe dynamically based on reverse index` |
| 8 | Core Quant Engine | Tested Ledoit-Wolf + base risk metrics | 1 (parallelizable) | `test(quant): add comprehensive unit coverage for risk metrics` |
| 9 | Fast-Path Pipeline & WS Fan-Out | Live price/PnL on the dashboard | 6/7, 4 | `feat(ui): wire live dashboard to WebSocket price/PnL updates` |
| 10 | Slow-Path Risk Recompute | Live VaR/CVaR/vol/drawdown/Sharpe | 8, 9 | `feat(ui): wire dashboard risk metrics panel` |
| 11 | GARCH Volatility Modeling | Time-varying volatility per symbol | 10 | `feat(garch): implement scheduled per-symbol refit worker` |
| 12 | Monte Carlo Simulation Engine | Async, progress-streamed simulation | 8, 11 | `feat(ui): build Monte Carlo simulation panel` |
| 13 | EVT Tail Risk | Second, independent tail-risk estimate | 12 | `feat(ui): add EVT comparison row to simulation panel` |
| 14 | Risk Budget & Alerting | Real-time proactive breach alerts | 10 | `feat(ui): build risk budget bar and alert banner` |
| 15 | Correlation / Concentration Detector | Risk contribution vs. allocation | 10 | `feat(ui): build risk contribution list and concentration warning` |
| 16 | HMM Regime Detection | Live calm/stressed probability signal | 6 | `feat(ui): add market regime badge to dashboard` |
| 17 | Decision Engine | Ranked, advisory action recommendations | 12, 14, 15 | `feat(ui): build decision engine cards` |
| 18 | AI Risk Analyst | Tool-calling explain + what-if | 10/15 | `feat(ui): build AI chat panel` |
| 19 | Historical Replay & Kupiec Backtest | The demo-closing proof-of-value screen | 14 | `feat(ui): build historical replay screen with backtest badge` |
| 20 | Frontend Design System Polish | A coherent, responsive, accessible product | 5–19 | `feat(ui): accessibility pass` |
| 21 | Slack Bot Second Client | Proven multi-client API reuse | 4, 10/15, 14, 18 | `feat(slack): implement status, whatif, and alerts commands` |
| 22 | Testing & Security Hardening | Audited against §11/§13's full bar | 1–21 | `docs(security): document manual penetration/ownership-check findings` |
| 23 | CI/CD Pipeline & Deployment | Live, automatically-deployed application | 22 | `docs(setup): document production deployment configuration` |
| 24 | Final QA & Production Readiness | Tagged, demo-ready `v1.0.0` release | 1–23 | `chore(release): tag v1.0.0` |

### Feature → Phase Mapping

| Feature | Primary Phase(s) |
|---|---|
| F1 Authentication | 4 |
| F2 Portfolio Ingestion | 5 |
| F3 Symbol Reverse Index | 7 |
| F4 Real-Time Fast Path | 9 |
| F5 Slow-Path Risk Recompute | 10 |
| F6 Ledoit-Wolf Shrinkage | 8 |
| F7 GARCH Volatility | 11 |
| F8 Monte Carlo Simulation | 12 |
| F9 EVT Tail Risk | 13 |
| F10 Risk Budget & Alerting | 14 |
| F11 Correlation / Concentration Detector | 15 |
| F12 HMM Regime Detection | 16 |
| F13 Kupiec Backtest | 19 |
| F14 Decision Engine | 17 |
| F15 AI Risk Analyst | 18 |
| F16 Historical Replay | 19 |
| F17 Slack Bot | 21 |
| F18 Frontend Dashboard (all screens) | 5, 9, 10, 12–19 (incrementally), 20 (polish) |
| F19 Docker Compose | 2 |
| F20 CI/CD | 23 |
| F21 Email/SMS notifications | Out of scope — documented extension point (§5.9's pub/sub design supports adding a subscriber) |
| F22 Portfolio optimization | Out of scope — documented extension point (§Assumptions, cut per earlier trimming discussion) |
| F23 Broker OAuth | Out of scope — documented extension point (Assumption A5/§3.1) |
| F24 Copula tail-dependence | Out of scope — documented future work (per earlier research discussion) |

---

## 21. Architecture Summary

RiskLens is a service-oriented monolith-of-workers: one FastAPI application serves REST + WebSocket traffic; a set of independently deployable background workers (ingestion, fast-path, slow-path, GARCH, HMM regime, decision engine, and an `arq` job worker for Monte Carlo/replay) handle everything continuous or heavy, communicating exclusively through Redis (Streams for tick data, pub/sub for fan-out, direct keys for cached state, `arq` for job queuing). PostgreSQL is the single durable source of truth; Redis is explicitly cache/messaging only, reconstructable from Postgres where it matters. The quant engine is a standalone, framework-agnostic Python package (Ledoit-Wolf covariance, GARCH volatility, Monte Carlo with correlated shocks and antithetic variates, EVT tail risk, HMM regime detection, Kupiec backtesting) consumed identically by the API, every worker, and — via the strict tool-calling boundary — the AI layer, which never performs a calculation itself. The frontend is a Next.js/TypeScript dashboard following a restrained, financial-terminal-inspired design system, live-updated via a single WebSocket connection per session. A Slack bot proves the backend's reusability as a genuine API. The entire stack runs identically in local Docker Compose and in production (Render for backend services, Vercel for the frontend), deployed via a fully automated GitHub Actions CI/CD pipeline.

---

## 22. Final Project Checklist

- [ ] All 24 phases completed with their individual Definition of Done satisfied
- [ ] §16's project-wide Definition of Done fully satisfied
- [ ] §17's production readiness checklist fully satisfied
- [ ] Full demo walkthrough (onboard → live dashboard → simulate/EVT → breach/decision cards → AI explain/what-if → historical replay/Kupiec → Slack bot) succeeds without caveats on the live deployment
- [ ] `v1.0.0` tagged in Git with a clean, intentional, readable commit history from Phase 1 through Phase 24
- [ ] README, `docs/setup.md`, and this `implementation.md` all accurate as of the tagged release
- [ ] Every out-of-scope item (F21–F24) clearly documented as future work, not silently missing

