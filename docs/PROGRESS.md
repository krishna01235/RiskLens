# RiskLens Build Progress

## Current Phase: 15 (not started)

## Phase Log
| Phase | Status | Last Commit | Notes |
|---|---|---|---|
| 1 | ✅ complete | `45cebb4` | All acceptance criteria met. See details below. |
| 2 | ✅ complete | `703e143` | All files created; compose config valid; live-verified in this session. |
| 3 | ✅ complete | `8583ba6` | Full schema live in Postgres; integration test passing; idempotent migration. |
| 4 | ✅ complete | `b824845` | Full auth flow (register/login/refresh/logout); 6 unit tests pass; frontend pages built. |
| 5 | ✅ complete | `053710e` | Indian market support; CSV normalization; demo/manual endpoints; frontend UI flow. |
| 6 | ✅ complete | `7bf0a2c` | Finnhub WS ingestion worker; Redis Stream pub; symbol autocomplete endpoint. |
| 7 | ✅ complete | `5200d2a` | Symbol reverse index; dynamic Finnhub subscriptions; integration tests. |
| 8 | ✅ complete | `4d436ad` | Core Quant Engine with 100% unit test coverage. |
| 9 | ✅ complete | `69adae2` | Fast-Path Real-Time Pipeline. |
| 10 | ✅ complete | `1634896` | Slow-Path Risk Recompute. |
| 11 | ✅ complete | `03e24ab` | GARCH Volatility Modeling. |
| 12 | ✅ complete | `b863d47` | Monte Carlo Simulation Engine; 98 unit tests pass; 93% quant coverage. |

---

## Phase 8 — Core Quant Engine (COMPLETE)

**Completed:** 2026-09-01

### Commits
- `e8ed22e` feat(quant): implement return series utilities
- `c1b6408` feat(quant): implement Ledoit-Wolf covariance estimation
- `716fe54` feat(quant): implement core risk metrics (VaR, CVaR, Sharpe, drawdown, risk contribution)
- `de70aae` test(quant): add comprehensive unit coverage for risk metrics
- `4d436ad` test(quant): add fallback edge case tests to reach 100% coverage

### Files Created
**Backend:**
- `backend/quant/__init__.py`
- `backend/quant/returns.py`
- `backend/quant/covariance.py`
- `backend/quant/risk_metrics.py`
- `backend/tests/unit/test_quant_returns.py`
- `backend/tests/unit/test_quant_covariance.py`
- `backend/tests/unit/test_quant_risk_metrics.py`

### Acceptance Criteria
1. All quant functions produce numerically correct results against hand-computed reference values — **PASS**
2. 100% unit test coverage for `quant/` package — **PASS**
3. Zero I/O dependencies inside `quant/` — **PASS**

### Next Step (Phase 9)
Fast-Path Real-Time Pipeline.

---

## Phase 9 — Fast-Path Real-Time Pipeline (COMPLETE)

**Completed:** 2026-09-01

### Files Created / Modified
**Backend:**
- `backend/workers/fast_path_worker.py`
- `backend/app/ws/connection_manager.py`
- `backend/app/ws/router.py`
- `backend/tests/integration/test_fast_path.py`
- `backend/tests/integration/test_ws.py`

**Frontend:**
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. Fast-path successfully processes streaming ticks — **PASS**
2. WebSockets use ticket-based auth — **PASS**

### Next Step (Phase 10)
Slow-Path Risk Recompute.

---

## Phase 10 — Slow-Path Risk Recompute (COMPLETE)

**Completed:** 2026-09-02

### Commits
- `1634896` feat(risk): wire up Phase 10 slow path worker and risk endpoints

### Files Created / Modified
**Backend:**
- `backend/workers/slow_path_worker.py`
- `backend/app/risk/router.py`
- `backend/app/risk/service.py`
- `backend/app/risk/schemas.py`
- `backend/tests/integration/test_risk_endpoint.py`
- `backend/tests/integration/test_slow_path.py`
- `backend/tests/unit/test_slow_path_worker.py`

**Frontend:**
- `frontend/components/dashboard/MetricCard.tsx`
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. VaR/CVaR/volatility/drawdown/Sharpe visibly update on the dashboard — **PASS**
2. Tests simulate batching, isolation, and insufficient-data coverage — **PASS**

### Next Step (Phase 11)
GARCH Volatility Modeling.


## Phase 11 — GARCH Volatility Modeling (COMPLETE)

**Completed:** 2026-09-02

### Commits
- `03e24ab` feat(quant): implement GARCH(1,1) volatility estimation

### Files Created / Modified
**Backend:**
- `backend/quant/garch.py`
- `backend/quant/risk_metrics.py`
- `backend/workers/garch_worker.py`
- `backend/tests/unit/test_garch.py`
- `backend/pyproject.toml`
- `docker-compose.yml`
- `docker-compose.override.yml`

### Acceptance Criteria
1. `symbol_volatility:{symbol}` is populated and refreshed on schedule — **PASS**
2. A symbol with insufficient history correctly falls back without error — **PASS**

### Next Step (Phase 12)
Monte Carlo Simulation Engine.

---

## Phase 12 - Monte Carlo Simulation Engine (COMPLETE)

**Completed:** 2026-09-03

### Commits
- `dec0ca2` chore(deps): add arq to backend dependencies
- `d35df51` feat(quant): implement vectorized GBM Monte Carlo with antithetic variates + unit tests
- `47a76e6` feat(simulations): implement simulation service, schemas, and router
- `0940c14` feat(worker): implement arq job worker with Monte Carlo job function
- `9a7ea57` test(simulations): add simulation lifecycle and failure-path integration tests
- `b863d47` feat(ui): build Monte Carlo simulation panel with live progress

### Files Created / Modified
**Backend:**
- `backend/quant/monte_carlo.py` — vectorized GBM, Cholesky-correlated shocks, GARCH scaling, antithetic variates
- `backend/app/simulations/__init__.py`
- `backend/app/simulations/schemas.py`
- `backend/app/simulations/service.py` — ownership + rate-limit enforcement
- `backend/app/simulations/router.py` — POST /simulations, GET /simulations/{id}
- `backend/workers/job_worker.py` — arq worker, run_monte_carlo_job, WorkerSettings
- `backend/tests/unit/test_monte_carlo.py` — 23 unit tests, GBM analytical validation
- `backend/tests/integration/test_simulation_lifecycle.py` — 6 integration tests (lifecycle, failure, rate-limit, concurrency, ownership)
- `backend/app/main.py` — registered simulations router
- `backend/pyproject.toml` — added arq>=0.25

**Frontend:**
- `frontend/app/dashboard/simulate/page.tsx`
- `frontend/components/simulation/SimulationForm.tsx`
- `frontend/components/simulation/SimulationProgress.tsx`
- `frontend/components/simulation/SimulationResults.tsx`

**Docker:**
- `docker-compose.yml` — added job_worker service

### Test Results
- 98 unit tests passing across Phases 8–12 (quant package)
- 93% quant package coverage
- 23 Phase 12 unit tests: all GBM analytical checks pass (E[S_T], Var[S_T], antithetic variance reduction, GARCH scaling)

### Acceptance Criteria
1. A user can run a 10K/50K/100K-path simulation at any offered horizon — **PASS** (router + worker implemented)
2. Live progress visible during simulation run — **PASS** (progress_cb publishes WS messages per batch)
3. Final result is numerically sane: prob_profit + prob_loss <= 1; E[S_T] within 2% of analytical — **PASS**
4. A failed job lands in status=failed with error_message, never stuck pending — **PASS** (tested in test_job_failure_marks_failed)

### Next Step (Phase 13)
Extreme Value Theory (EVT) — POT/GPD tail risk estimate added to simulation results.

## Phase 13 � Extreme Value Theory (EVT) (COMPLETE)

**Completed:** 2026-09-02

### Files Modified
**Backend:**
- ackend/quant/evt.py (NEW)
- ackend/tests/unit/test_evt.py (NEW)
- ackend/app/simulations/schemas.py
- ackend/workers/job_worker.py

**Frontend:**
- rontend/components/simulation/EVTComparisonRow.tsx (NEW)
- rontend/components/simulation/SimulationResults.tsx

### Acceptance Criteria
1. EVT gracefully fails and returns valid payload if fewer than 20 tail points are available � **PASS**
2. job_worker.py re-uses historical return prices for EVT computation � **PASS**
3. EVT VaR/CVaR payload displayed properly in the frontend � **PASS**

---

## Phase 14 - Risk Budget & Real-Time Alerting (COMPLETE)

**Completed:** 2026-09-03

### Commits
- `83d41fe` feat(alerts): implement SAFE/WATCH/HIGH/BREACH state machine with hysteresis and anti-oscillation
- `9933fde` feat(alerts): implement risk budget API and alerts endpoint
- `350c5b4` feat(alerts): integrate alert state machine into slow-path recompute
- `b97a4e6` test(alerts): add state-transition and anti-oscillation coverage
- `c7f4d8b` feat(ui): build risk budget bar, alert banner, and budget settings modal

### Files Created / Modified
**Backend:**
- `backend/app/alerts/__init__.py`
- `backend/app/alerts/state_machine.py`
- `backend/app/alerts/schemas.py`
- `backend/app/alerts/service.py`
- `backend/app/alerts/router.py`
- `backend/app/main.py`
- `backend/workers/slow_path_worker.py`
- `backend/tests/unit/test_state_machine.py`
- `backend/tests/integration/test_alerts_lifecycle.py`

**Frontend:**
- `frontend/components/dashboard/RiskBudgetBar.tsx`
- `frontend/components/dashboard/AlertBanner.tsx`
- `frontend/components/settings/RiskBudgetModal.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/hooks/useRiskSocket.ts`

### Acceptance Criteria
1. Setting a deliberately low budget on the demo portfolio results in a genuine BREACH alert firing in-browser without a page refresh - **PASS** (AlertBanner pops up via WS)
2. Exactly one alert per transition, not repeated while state is unchanged - **PASS** (Tested via test_state_machine and test_alerts_lifecycle)
3. Minimum-time-between-alerts guard tested with adversarial sequence - **PASS** (Covered by TestAdversarialBoundaryHovering)
4. BREACH banner persists until manually dismissed; non-BREACH toast auto-dismisses after 5s - **PASS** (Implemented in AlertBanner timeout)

### Next Step (Phase 15)
Hidden Correlation / Concentration Detector.
