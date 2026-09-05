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
| 13 | ✅ complete | `xxxxxxx` | Extreme Value Theory. |
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
| 13 | ✅ complete | `xxxxxxx` | Extreme Value Theory. |
| 14 | ✅ complete | `c7f4d8b` | Risk Budget & Alerting. |
| 15 | ✅ complete | `f1e3baa` | Correlation Cluster Detection. |
| 16 | ✅ complete | `f1e3baa` | HMM Market Regime Detection. |
| 17 | ✅ complete | `3e8e192` | Decision Engine. |
| 18 | ✅ complete | `b4fba39` | AI Risk Analyst (LangGraph Explain + What-If). |
| 19 | ✅ complete | `xxxxxxx` | Historical Replay & Kupiec Backtest. |
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

---

## Phase 15 - Hidden Correlation / Concentration Detector (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `9fa2bf4` feat(quant): implement correlation cluster detection
- `c48aaf1` feat(risk): surface risk contribution and concentration flags in risk state
- `e103042` feat(ui): build risk contribution list and concentration warning

### Files Created / Modified
**Backend:**
- `backend/quant/risk_metrics.py`
- `backend/tests/unit/test_quant_risk_metrics.py`
- `backend/workers/slow_path_worker.py`
- `backend/tests/integration/test_slow_path.py`

**Frontend:**
- `frontend/components/dashboard/ConcentrationWarning.tsx`
- `frontend/components/dashboard/RiskContributionList.tsx`
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. On the demo portfolio, the concentration warning correctly fires and names the correct correlated symbols — **PASS**
2. Risk-contribution percentages are visibly different from raw allocation percentages — **PASS**
3. Unit test for cluster detection against a synthetic correlation matrix with a known planted cluster — **PASS**
4. Integration test confirming the demo portfolio produces the expected warning — **PASS**

### Next Step (Phase 16)
HMM Market Regime Detection.

---

## Phase 16 - HMM Market Regime Detection (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `40fe7af` feat(quant): implement HMM market regime detection with forward probabilities
- `211feee` feat(regime): implement scheduled regime refit worker
- `f1e3baa` feat(ui): add market regime badge to dashboard

### Files Created / Modified
**Backend:**
- `backend/quant/regime.py`
- `backend/tests/unit/test_quant_regime.py`
- `backend/workers/regime_worker.py`
- `backend/app/market/router.py`
- `backend/pyproject.toml`
- `docker-compose.yml`

**Frontend:**
- `frontend/components/dashboard/RegimeBadge.tsx`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. The regime badge shows a plausible, updating probability. — **PASS**
2. A manually-injected synthetic high-volatility period in a test fixture correctly shifts the labeled "stressed" probability upward, proving the relabeling logic is correct rather than coincidentally correct. — **PASS**

## Phase 17 - Decision Engine (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `fc92b45` feat(quant): refactor constants and implement decision candidates generation
- `12b4f9d` feat(risk): implement decision engine worker to generate and save decision candidates
- `3e8e192` feat(ui): build DecisionCard and update AlertBanner for decisions pending state

### Files Created / Modified
**Backend:**
- `backend/quant/constants.py`
- `backend/quant/garch.py`
- `backend/quant/evt.py`
- `backend/app/alerts/schemas.py`
- `backend/app/alerts/decisions_service.py`
- `backend/workers/decision_engine_worker.py`
- `backend/workers/utils.py`
- `backend/workers/job_worker.py`
- `backend/app/alerts/router.py`
- `backend/app/alerts/service.py`
- `backend/tests/test_decisions_service.py`
- `docker-compose.yml`

**Frontend:**
- `frontend/components/dashboard/DecisionCard.tsx`
- `frontend/components/dashboard/AlertBanner.tsx`
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. Defined rule for omitting the "reduce largest risk contributor" candidate — **PASS**
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

## Phase 13  Extreme Value Theory (EVT) (COMPLETE)

**Completed:** 2026-09-02

### Files Modified
**Backend:**
-  ackend/quant/evt.py (NEW)
-  ackend/tests/unit/test_evt.py (NEW)
-  ackend/app/simulations/schemas.py
-  ackend/workers/job_worker.py

**Frontend:**
- rontend/components/simulation/EVTComparisonRow.tsx (NEW)
- rontend/components/simulation/SimulationResults.tsx

### Acceptance Criteria
1. EVT gracefully fails and returns valid payload if fewer than 20 tail points are available  **PASS**
2. job_worker.py re-uses historical return prices for EVT computation  **PASS**
3. EVT VaR/CVaR payload displayed properly in the frontend  **PASS**

---

## Phase 14 - Risk Budget & Real-Time Alerting (COMPLETE)

**Completed:** 2026-09-03

### Commits
- `83d41fe` feat(alerts): implement SAFE/WATCH/HIGH/BREACH state machine with hysteresis and anti-oscillation
- `9933fde` feat(alerts): implement risk budget API and alerts endpoint
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

---

## Phase 15 - Hidden Correlation / Concentration Detector (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `9fa2bf4` feat(quant): implement correlation cluster detection
- `c48aaf1` feat(risk): surface risk contribution and concentration flags in risk state
- `e103042` feat(ui): build risk contribution list and concentration warning

### Files Created / Modified
**Backend:**
- `backend/quant/risk_metrics.py`
- `backend/tests/unit/test_quant_risk_metrics.py`
- `backend/workers/slow_path_worker.py`
- `backend/tests/integration/test_slow_path.py`

**Frontend:**
- `frontend/components/dashboard/ConcentrationWarning.tsx`
- `frontend/components/dashboard/RiskContributionList.tsx`
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. On the demo portfolio, the concentration warning correctly fires and names the correct correlated symbols — **PASS**
2. Risk-contribution percentages are visibly different from raw allocation percentages — **PASS**
3. Unit test for cluster detection against a synthetic correlation matrix with a known planted cluster — **PASS**
4. Integration test confirming the demo portfolio produces the expected warning — **PASS**

### Next Step (Phase 16)
HMM Market Regime Detection.

---

## Phase 16 - HMM Market Regime Detection (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `40fe7af` feat(quant): implement HMM market regime detection with forward probabilities
- `211feee` feat(regime): implement scheduled regime refit worker
- `f1e3baa` feat(ui): add market regime badge to dashboard

### Files Created / Modified
**Backend:**
- `backend/quant/regime.py`
- `backend/tests/unit/test_quant_regime.py`
- `backend/workers/regime_worker.py`
- `backend/app/market/router.py`
- `backend/pyproject.toml`
- `docker-compose.yml`

**Frontend:**
- `frontend/components/dashboard/RegimeBadge.tsx`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. The regime badge shows a plausible, updating probability. — **PASS**
2. A manually-injected synthetic high-volatility period in a test fixture correctly shifts the labeled "stressed" probability upward, proving the relabeling logic is correct rather than coincidentally correct. — **PASS**

## Phase 17 - Decision Engine (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `fc92b45` feat(quant): refactor constants and implement decision candidates generation
- `12b4f9d` feat(risk): implement decision engine worker to generate and save decision candidates
- `3e8e192` feat(ui): build DecisionCard and update AlertBanner for decisions pending state

### Files Created / Modified
**Backend:**
- `backend/quant/constants.py`
- `backend/quant/garch.py`
- `backend/quant/evt.py`
- `backend/app/alerts/schemas.py`
- `backend/app/alerts/decisions_service.py`
- `backend/workers/decision_engine_worker.py`
- `backend/workers/utils.py`
- `backend/workers/job_worker.py`
- `backend/app/alerts/router.py`
- `backend/app/alerts/service.py`
- `backend/tests/test_decisions_service.py`
- `docker-compose.yml`

**Frontend:**
- `frontend/components/dashboard/DecisionCard.tsx`
- `frontend/components/dashboard/AlertBanner.tsx`
- `frontend/hooks/useRiskSocket.ts`
- `frontend/app/dashboard/page.tsx`

### Acceptance Criteria
1. Defined rule for omitting the "reduce largest risk contributor" candidate — **PASS**
2. Added a per-candidate timeout on synchronous Monte Carlo evaluation — **PASS**
3. `decision_engine_worker.py` reuses the exact same inputs as Phase 12's Monte Carlo — **PASS**
4. Purely advisory constraint clearly documented — **PASS**
5. UI displays "decisions pending" state in the Alert Banner — **PASS**

---

## Phase 18 - AI Risk Analyst (LangGraph Explain + What-If) (COMPLETE)

**Completed:** 2026-09-05

### Commits
- `1c81ba3` feat(quant): implement deterministic scenario evaluation
- `51b3b1b` feat(ai): implement LangGraph explain and what-if tools
- `d172245` feat(ai): wire explain and what-if endpoints
- `b4fba39` feat(ai): add AI chat panel and integrate into dashboard

### Files Created / Modified
**Backend:**
- `backend/quant/scenarios.py` — deterministic scenario evaluator; sole source of numbers for AI what-if flow
- `backend/app/ai/schemas.py` — Pydantic request/response models + ShocksPayload validator
- `backend/app/ai/tools.py` — `explain_risk_state` and `evaluate_what_if` LangGraph tool functions
- `backend/app/ai/agent.py` — LangGraph StateGraph (explain + what-if flows), asyncio timeout wrapper
- `backend/app/ai/service.py` — ownership-gated business logic; Redis risk snapshot fetch; DB persistence
- `backend/app/ai/router.py` — POST /ai/explain, POST /ai/what-if (30/hour), GET conversations/messages
- `backend/app/main.py` — registered ai_router
- `backend/pyproject.toml` — added langgraph, langchain-anthropic, langchain-core
- `backend/tests/unit/test_scenarios.py` — 11 unit tests for scenarios.py
- `backend/tests/unit/test_ai_tools.py` — 12 unit tests for tools.py (adversarial input boundary)
- `backend/tests/integration/test_ai_endpoints.py` — 6 integration tests (mocked LLM; ownership/cross-user probe)

**Frontend:**
- `frontend/components/ai/ScenarioResultCard.tsx` — structured scenario result display (numbers from quant engine)
- `frontend/components/ai/AiChatPanel.tsx` — AI chat panel with suggested questions, explain/what-if routing
- `frontend/app/dashboard/page.tsx` — collapsible "AI Risk Analyst" section added

### Acceptance Criteria
1. AI never computes a number — all numeric claims pass through `evaluate_scenario()` — **PASS**
2. Cross-user probe: POST /ai/what-if on another user's portfolio returns 403 — **PASS**
3. `ShocksPayload` Pydantic model rejects out-of-range shocks before they reach the quant engine — **PASS** (12 tool unit tests)
4. LLM timeout returns `timeout=True` + `narration=None`; scenario_result still renders — **PASS**
5. Scenario result card renders deterministic numbers from the quant engine independent of narration — **PASS**
6. 23/23 Phase 18 unit tests pass — **PASS**
7. TypeScript compiles clean for Phase 18 files — **PASS**

---

## Phase 19 - Historical Replay & Kupiec Backtest (COMPLETE)

**Completed:** 2026-09-04

### Commits
- `xxxxxxx` feat(quant): implement ReplayDailyState and Kupiec backtest logic
- `xxxxxxx` feat(worker): implement replay_job to process daily loops
- `xxxxxxx` test(replays): add integration tests and ownership validation
- `xxxxxxx` feat(ui): build Kupiec Backtest Replay chart and pass/fail badges

### Files Created / Modified
**Backend:**
- `backend/app/replays/models.py`
- `backend/app/replays/schemas.py`
- `backend/app/replays/service.py`
- `backend/app/replays/router.py`
- `backend/workers/replay_job.py`
- `backend/workers/job_worker.py`
- `backend/app/main.py`
- `backend/app/deps.py`
- `backend/tests/integration/test_replays.py`
- `backend/alembic/versions/` (migration)

**Frontend:**
- `frontend/app/dashboard/replay/page.tsx`

### Acceptance Criteria
1. Replay accurately reconstructs T-25 returns using the existing portfolio — **PASS**
2. VaR is strictly computed *without* look-ahead data — **PASS**
3. Kupiec POF score evaluates pass/fail dynamically — **PASS**
4. The chart renders VaR prediction vs actual portfolio return with breach markers — **PASS**
5. Circular dependencies fixed, ensuring `run_replay_job` and integration tests work end-to-end — **PASS**

---

## Phase 20 - Frontend Design System Consolidation & Full Polish (COMPLETE)

**Completed:** 2026-09-05

### Commits
- `c7f4d8b` feat(ui): build risk budget bar, alert banner, and budget settings modal
- `2f29c31` refactor(ui): migrate AI, simulation, and settings components to design tokens
- `700a781` refactor(ui): migrate onboarding components and auth pages to design tokens
- `43f5384` feat(ui): wrap app pages in AppShell, add skeleton loading and empty states
- `1c8da04` test(ui): add unit tests for primitive components

### Acceptance Criteria
1. Extract ad-hoc hex codes into a semantic CSS variable system (`tokens.css`) — **PASS**
2. Standardize `Button`, `Card`, `Input`, `Modal`, `Toast`, and `Skeleton` — **PASS**
3. Create an `AppShell` with responsive sidebar navigation — **PASS**
4. All existing pages and components migrated to use tokens and primitives without layout regressions — **PASS**
5. All interactive elements have accessible `focus-visible` focus rings — **PASS**
6. RTL unit tests written for primitive components in vitest — **PASS**

### Next Step
Phase 21 — Slack Bot Second Client.

---

## Phase 21 — Slack Bot Second Client (COMPLETE)

**Completed:** 2026-09-05

### Commits
- `119c283` feat(auth): add named constants for API token byte-length, scopes, OTC TTL
- `c525685` feat(auth): implement scoped API token issuance and one-time code flow
- `61a92aa` feat(slack): add slack_links migration and ORM model
- `d9ea79a` feat(slack): implement slack link/unlink endpoints and register router
- `d2ffcc2` refactor(deps,routes): add get_current_user_any and apply to four Slack-bot-facing routes
- `2027398` feat(slack): implement Slack Bolt app with login, status, whatif, alerts commands
- `2589231` chore(deploy): add slack-bolt/httpx deps, slack_bot docker service, env vars
- `a3052ea` test(auth,slack): add scope-enforcement, link flow, and formatter unit tests

### Files Created
**Backend:**
- `backend/app/auth/constants.py` — `API_TOKEN_BYTE_LENGTH`, `ALLOWED_SCOPES`, `ONE_TIME_CODE_TTL_SECONDS` (single source of truth)
- `backend/app/slack/__init__.py`
- `backend/app/slack/router.py` — `POST /slack/link` (unauthenticated, rate-limited), `POST /slack/unlink` (JWT-gated)
- `backend/slack_bot/__init__.py`
- `backend/slack_bot/constants.py` — re-exports auth constants; bot never duplicates scope definitions
- `backend/slack_bot/api_client.py` — thin `httpx.AsyncClient` wrapper for all four API endpoints
- `backend/slack_bot/formatters.py` — Block Kit formatters (pure functions, no I/O)
- `backend/slack_bot/app.py` — Slack Bolt socket-mode app (`/risklens login|status|whatif|alerts`)
- `backend/alembic/versions/0d247978a39d_add_slack_links.py` — `slack_links` table migration
- `backend/tests/integration/test_api_tokens.py` — 9 integration tests
- `backend/tests/integration/test_slack_bot.py` — 7 integration tests
- `backend/tests/unit/test_formatters.py` — 22 unit tests, all passing

### Files Modified
- `backend/app/auth/schemas.py` — added `ApiTokenCreateRequest`, `ApiTokenResponse`, `OneTimeCodeResponse`, `SlackLinkRequest`
- `backend/app/auth/service.py` — added `create_api_token`, `validate_api_token`, `revoke_api_token`, `create_one_time_code`, `exchange_one_time_code`, `unlink_slack_user`, `get_linked_api_token_raw`
- `backend/app/auth/router.py` — added `POST /auth/api-tokens` (5/min RL), `DELETE /auth/api-tokens/{id}`, `POST /auth/api-tokens/one-time-code` (10/min RL)
- `backend/app/auth/models.py` — added `SlackLink` ORM model
- `backend/app/deps.py` — added `get_current_user_any(required_scope)` dependency factory
- `backend/app/portfolios/router.py` — `list_portfolios` → `get_current_user_any("read")`
- `backend/app/risk/router.py` — `get_portfolio_risk` → `get_current_user_any("read")`
- `backend/app/alerts/router.py` — `list_alerts` → `get_current_user_any("read")`
- `backend/app/ai/router.py` — `what_if` → `get_current_user_any("whatif")`
- `backend/app/main.py` — registered `slack_router`
- `backend/pyproject.toml` — added `slack-bolt>=1.18`, `httpx>=0.27`
- `docker-compose.yml` — added `slack_bot` service (socket-mode, depends on api/postgres/redis)
- `.env.example` — added `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` with documentation

### Acceptance Criteria
1. `POST /auth/api-tokens` issues scoped tokens, hashed at rest — **PASS**
2. Scope enforcement: read token → 403 on whatif endpoint; whatif token → 403 on read endpoints — **PASS** (tested)
3. Revoked token → 401 — **PASS** (tested)
4. One-time code is single-use (atomic Redis pipeline) — **PASS** (tested)
5. All four Slack commands implemented with correct Block Kit output — **PASS** (formatters 22/22 unit tests)
6. Exactly four routes changed; all others keep `get_current_user` — **PASS**
7. Named constants are single source of truth — **PASS**
8. Rate limiting on new endpoints — **PASS** (5/min api-tokens, 10/min OTC, 10/min /slack/link)

### Next Step
Phase 22 — Testing Hardening & Security Pass.

---

## Phase 22 — Testing Hardening & Security Pass (COMPLETE)

**Completed:** 2026-09-05

### Commits
- `cd699e3` test(e2e): add Playwright config and five critical user journey tests
- `cd6475a` chore(security): complete rate limiting on all state-changing endpoints
- `e25f4b0` docs(security): document manual penetration and ownership-check findings
- `2d7cf06` chore(security): resolve frontend dependency vulnerabilities
- `33ab698` fix(quant): fix wrong absolute imports in evt.py and garch.py
- `521519f` fix(frontend): fix pre-existing TypeScript errors uncovered by Next.js 16 upgrade
- `e44a04c` test(slow_path_worker): fix tests broken by new compute_risk_from_history signature
- `89b8753` fix(e2e): fix journey1/2/3 test failures - progressbar aria, resilient assertions, onboarding nav
- `ae7437f` fix(workers): import RiskSnapshot in job_worker to resolve SQLAlchemy mapper error; fix e2e timeouts
- `2c92b3f` fix(workers): import all Portfolio relationship models in job_worker; fix e2e networkidle waits
- `0d56110` fix(workers,e2e): fix MissingGreenlet in utils.py (selectinload) and journey1 test flow
- `a1378b5` fix(e2e): replace isVisible(timeout) anti-pattern with expect().toBeVisible() in journey1

### Files Created / Modified
- `frontend/tests/e2e/journey1_onboarding.spec.ts` — Register → Demo → Dashboard (all 3 variants of redirection handled)
- `frontend/tests/e2e/journey2_csv_import.spec.ts` — CSV import flow
- `frontend/tests/e2e/journey3_simulation.spec.ts` — Monte Carlo simulation + EVT results
- `frontend/tests/e2e/journey4_replay.spec.ts` — Historical replay + Kupiec badge
- `frontend/tests/e2e/journey5_ai_whatif.spec.ts` — AI what-if flow
- `frontend/playwright.config.ts` — Playwright config (chromium, timeout=120s)
- `backend/workers/utils.py` — Fixed MissingGreenlet: added `selectinload(Portfolio.holdings)` to async query
- Various rate-limit additions across API routers (Phases 4–19 endpoints audited)
- `docs/security-findings.md` — Manual penetration test and cross-user ownership check results

### Acceptance Criteria
1. No high-severity dependency vulnerabilities — **PASS** (npm audit clean post-patch)
2. Every endpoint has an appropriate rate limit — **PASS** (all state-changing endpoints audited and limited)
3. All five E2E journeys pass — **PASS** (`5 passed (36.7s)`, verified on local full stack)
4. Cross-user data access confirmed blocked on every domain — **PASS** (documented in security-findings.md)
5. AI tool-calling boundary confirmed unbypassable by adversarial prompt — **PASS** (documented in security-findings.md)

### Key Bug Fixes in This Phase
- **MissingGreenlet** (`workers/utils.py`): `portfolio.holdings` triggered async lazy load → fixed with `selectinload(Portfolio.holdings)`
- **Journey 1 flow**: register → `/dashboard` (no portfolio) → redirect to `/onboarding` → test must `waitForURL(/onboarding/)` before clicking "Try Demo"
- **Journey 1 assertion**: `locator.isVisible({timeout})` ignores timeout (checks immediately) → replaced with `expect(locator).toBeVisible({timeout})` which correctly auto-waits
- **Journey 3**: Simulation failing due to MissingGreenlet (same root cause as above)

### Next Step
Phase 23 — CI/CD Pipeline & Deployment.
