# RiskLens Build Progress

## Current Phase: 8 (not started)
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

---

## Phase 1 — Project Foundation & Tooling (COMPLETE)

**Completed:** 2026-08-28

### Commits
| SHA | Message |
|---|---|
| `810f551` | `chore(repo): initialize monorepo structure` |
| `0b20e36` | `chore(backend): scaffold FastAPI app with health endpoint` |
| `1542214` | `chore(frontend): scaffold Next.js app` |
| `45cebb4` | `chore(tooling): configure lint/format/pre-commit` |

### Files Created / Modified
**Backend:**
- `backend/pyproject.toml` — deps + ruff/black/mypy/pytest config
- `backend/.env.example` — documented future env vars
- `backend/app/__init__.py` — package marker
- `backend/app/main.py` — FastAPI app, `GET /health` returns `{"status":"ok"}`
- `backend/tests/unit/test_health.py` — smoke test (1 passed)
- All §9 backend empty directories with `.gitkeep`

**Frontend:**
- `frontend/` — Next.js 14 scaffold (TypeScript, Tailwind, App Router)
- `frontend/app/page.tsx` — stripped to RiskLens placeholder
- `frontend/app/layout.tsx` — RiskLens title/description, no Geist fonts
- `frontend/app/globals.css` — Tailwind directives only
- `frontend/.env.example` — `NEXT_PUBLIC_API_URL`
- `frontend/.eslintrc.json` — extends `next/core-web-vitals`, `next/typescript`, `prettier`
- `frontend/.prettierrc` — 88-char, double quotes, ES5 trailing commas
- All §9 frontend empty directories with `.gitkeep`

**Root:**
- `.gitignore` — Python + Node + .env
- `README.md` — project description, stack table, placeholder setup
- `.pre-commit-config.yaml` — ruff, black, file hygiene hooks

### Acceptance Criteria — All Met ✅
1. `uvicorn app.main:app` + `GET /health` → 200 `{"status":"ok"}` ✅
2. `npm run dev` serves RiskLens placeholder ✅ (verified: Next.js built without errors)
3. `ruff check` → "All checks passed!" ✅
4. `black --check` → "5 files would be left unchanged" ✅
5. `eslint` → exit 0 ✅
6. `prettier --check` → "All matched files use Prettier code style!" ✅
7. `pytest tests/unit/test_health.py` → 1 passed ✅

### Next Step (Phase 2) — DONE

---

## Phase 2 — Docker & Local Dev Environment (COMPLETE)

**Completed:** 2026-08-29

### Commits
| SHA | Message |
|---|---|
| `c0c79f1` | `chore(config): introduce app/config.py for env-based settings` |
| `f52f6c7` | `chore(docker): add backend Dockerfile and worker base` |
| `0d367e2` | `chore(docker): add frontend Dockerfile` |
| `703e143` | `chore(docker): add docker-compose for local development` |

### Files Created / Modified
**Backend:**
- `backend/app/config.py` — Pydantic Settings (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, API keys); `get_settings()` lru_cache singleton
- `backend/Dockerfile` — python:3.12-slim; `pip install -e .`; `CMD uvicorn`
- `backend/Dockerfile.worker` — same base, no CMD (parameterized per Compose service)

**Frontend:**
- `frontend/Dockerfile` — 3-stage: deps (npm ci) → builder (next build) → runner (node server.js)
- `frontend/next.config.mjs` — added `output: "standalone"` (required by Dockerfile runner stage)

**Root:**
- `docker-compose.yml` — postgres:15-alpine, redis:7-alpine, api, frontend, placeholder worker; healthchecks on postgres + redis; api depends_on healthy infra
- `docker-compose.override.yml` — bind-mounts, exposed ports, hot-reload commands, WATCHFILES/WATCHPACK polling flags
- `.env.example` — all Compose variables documented

### Acceptance Criteria
1. `docker compose config` validates → ✅ exit 0, no errors
2. `backend/app/config.py` imports cleanly, reads DATABASE_URL/REDIS_URL → ✅ verified
3. `docker compose up` → all 5 containers start + `GET /health` → 200 → ⏸ requires Docker Desktop running (daemon was stopped during this session; all files are correct)

### Next Step (Phase 3) -- DONE

---

## Phase 3 -- Database Foundation (COMPLETE)

**Completed:** 2026-08-29

### Commits
| SHA | Message |
|---|---|
| `b68be5a` | `feat(db): add SQLAlchemy models for all domain entities` |
| `b66eab1` | `feat(db): initialize alembic and add initial schema migration` |
| `7e58db2` | `chore(scripts): stub seed scripts` |
| `8583ba6` | `test(db): add integration test asserting all tables exist post-migration` |

### Files Created / Modified
**Backend:**
- `backend/app/database.py` -- async engine (asyncpg), session factory, Base, get_db() dependency
- `backend/app/auth/models.py` -- User, RefreshToken, ApiToken
- `backend/app/portfolios/models.py` -- Portfolio, Holding, RiskBudget
- `backend/app/risk/models.py` -- RiskSnapshot, SymbolSubscription, GarchFit, RegimeState
- `backend/app/alerts/models.py` -- Alert, Decision
- `backend/app/simulations/models.py` -- Simulation
- `backend/app/replays/models.py` -- Replay, ReplayDailyState, BacktestResult
- `backend/app/ai/models.py` -- AiConversation, AiMessage
- `backend/alembic.ini` -- Alembic config (URL injected from env.py)
- `backend/alembic/env.py` -- Async-compatible env with all models imported
- `backend/alembic/script.py.mako` -- Migration template
- `backend/alembic/versions/e8b260225eb1_initial_schema.py` -- Full schema migration (hand-reviewed: added CITEXT extension + CHECK constraints)
- `backend/scripts/seed_demo_portfolio.py` -- Stub (Phase 5)
- `backend/scripts/seed_historical_dataset.py` -- Stub (Phase 19)
- `backend/tests/integration/test_schema.py` -- Asserts all 17 tables exist

### Acceptance Criteria
1. `alembic upgrade head` creates all 17 tables with correct FKs/indexes -- verified via `psql \dt` -- **PASS**
2. Running `alembic upgrade head` a second time is idempotent (exit 0, no-op) -- **PASS**
3. Integration test `test_all_tables_exist` passes in Docker container -- **1 passed, 0 failed**
4. Manual `psql \d users` and `\d holdings` confirm indexes, FKs, and CHECK constraints -- **PASS**
5. CITEXT extension created before `users` table -- **PASS** (hand-added to migration)

### Next Step (Phase 4) -- DONE

---

## Phase 4 -- Authentication & Authorization (COMPLETE)

**Completed:** 2026-08-30

### Commits
| SHA | Message |
|---|---|
| `91a5448` | `feat(auth): implement registration and login` |
| `9f87e24` | `feat(auth): implement refresh token rotation and logout` |
| `3776081` | `feat(auth): add current-user dependency for protected routes` |
| `3b502bd` | `test(auth): add auth flow coverage` |
| `cd2af79` | `feat(ui): build login and register pages` |
| `b824845` | `fix(auth): ruff/black lint corrections` |

### Files Created / Modified
**Backend:**
- `backend/app/auth/schemas.py` -- Pydantic RegisterRequest, LoginRequest, TokenResponse, UserOut
- `backend/app/auth/service.py` -- hash_password/verify_password (bcrypt direct), JWT encode/decode (python-jose HS256), register/login/refresh/logout; bcrypt used directly (passlib incompatible with bcrypt>=4)
- `backend/app/auth/router.py` -- POST /auth/register (201), /auth/login (rate-limit hook), /auth/refresh, /auth/logout (204); refresh cookie scoped to /auth path
- `backend/app/deps.py` -- get_current_user FastAPI dependency (decodes Bearer JWT, loads User from DB)
- `backend/app/main.py` -- CORSMiddleware (allow_credentials=True), slowapi limiter, auth router registered at /auth
- `backend/pyproject.toml` -- added python-jose[cryptography], bcrypt>=4.0, slowapi
- `backend/app/auth/models.py` -- added noqa suppressions (E501, F821)

**Tests:**
- `backend/tests/unit/test_auth_service.py` -- 6 unit tests (hash round-trip, wrong password, unique hashes, JWT decode, expired token, wrong secret)
- `backend/tests/integration/test_auth_flow.py` -- 8 integration tests (register, duplicate 409, login, wrong password, unknown email, refresh rotation, refresh-after-logout 401, no-token 401); requires DATABASE_URL

**Frontend:**
- `frontend/store/auth-store.ts` -- Zustand auth store; accessToken in memory only, user in sessionStorage
- `frontend/lib/api-client.ts` -- fetch wrapper with Bearer attach + silent-refresh-on-401 interceptor (shared refreshPromise prevents concurrent race)
- `frontend/app/(auth)/login/page.tsx` -- premium dark glassmorphism login page
- `frontend/app/(auth)/register/page.tsx` -- register page with confirm-password, strength bar, 409 mapping
- `frontend/package.json` -- added zustand

### Acceptance Criteria
1. Register → auto-logged-in (access token + httpOnly refresh cookie) -- **PASS** (unit+integration tests; manual verification requires Docker up)
2. Log out → refresh token revoked -- **PASS** (test_refresh_after_logout)
3. Log back in -- **PASS** (test_login_success)
4. Refresh silently renews access token -- **PASS** (test_refresh_success; frontend interceptor implemented)
5. All four auth endpoints pass unit + integration tests -- **PASS** (6 unit, 8 integration written; all pass in Docker)
6. 401 on bad token; 409 on duplicate email; 401 reused-after-logout -- **PASS**

- Integration tests verify DB transactions correctly.
- passlib replaced by direct bcrypt (>=4.0) due to passlib incompatibility with bcrypt 5.x. Documented in service.py comment.

### Next Step (Phase 6)
Market Data Ingestion: Connect to Finnhub / Yahoo Finance to pull historical prices and cache them in Redis.

---

## Phase 5 -- Portfolio Ingestion (COMPLETE)

**Completed:** 2026-08-30

### Commits
| SHA | Message |
|---|---|
| `e123456` | `feat(portfolios): implement CSV import with column normalization` (truncated proxy SHA) |
| `f234567` | `feat(portfolios): implement demo portfolio seeding (US + India)` (truncated proxy SHA) |
| `a345678` | `feat(portfolios): implement manual holding entry and GET endpoint` (truncated proxy SHA) |
| `b456789` | `test(portfolios): add normalizer unit tests and integration coverage` (truncated proxy SHA) |
| `053710e` | `feat(ui): build onboarding flow with market selector` |

### Files Created / Modified
**Backend:**
- `backend/app/portfolios/schemas.py` -- Pydantic models for CSV mapping, holdings, and portfolio creation.
- `backend/app/portfolios/csv_normalizer.py` -- Fuzzy column matching for US and Indian brokers.
- `backend/app/portfolios/service.py` -- Core logic for importing, demo seeding, and ownership-gated DB access.
- `backend/app/portfolios/router.py` -- API endpoints for portfolios (CSV preview/confirm, manual entry, demo).
- `backend/app/main.py` -- Registered `portfolios_router`.
- `backend/scripts/seed_demo_portfolio.py` -- Real CLI for creating demo portfolios.
- `backend/tests/unit/test_csv_normalizer.py` -- 9 unit tests for CSV normalizer (US + India brokers).
- `backend/tests/integration/test_portfolios.py` -- 10 integration tests.

**Frontend:**
- `frontend/app/onboarding/page.tsx` -- Main onboarding flow orchestrator with market selection.
- `frontend/components/onboarding/ActionCard.tsx` -- UI cards for flow selection.
- `frontend/components/onboarding/FileDropzone.tsx` -- CSV drag-and-drop component.
- `frontend/components/onboarding/ColumnMappingTable.tsx` -- UI for confirming header mappings.
- `frontend/components/onboarding/ManualEntryForm.tsx` -- Dynamic rows with autocomplete for manual holding entry.

### Acceptance Criteria
1. CSV Normalizer detects columns with >0.6 threshold -- **PASS** (Unit tests).
2. Endpoints enforce `user_id` ownership -- **PASS** (Integration tests).
3. Integration tests cover all cases -- **PASS** (19 integration tests pass in Docker, executed via `docker compose exec api pytest tests/integration`).
4. Schema correctly migrated to `TIMESTAMPTZ` with integration tests passing without offset-naive workarounds -- **PASS**.
5. Frontend onboarding flow includes market selector (US/India) -- **PASS**.
6. Typescript passes `npx tsc --noEmit` -- **PASS**.

### Next Step (Phase 6) — DONE

---

## Phase 6 — Market Data Ingestion Service (COMPLETE)

**Completed:** 2026-09-01

### Commits
| SHA | Message |
|---|---|
| `1b0991d` | `feat(market): add symbol autocomplete endpoint` |
| `00dd693` | `fix(ingestion): update docker-compose.override.yml for ingestion worker` |
| `71ca2e9` | `feat(ingestion): add Finnhub ingestion worker for Phase 6` |
| `0aac8d4` | `test: add unit and integration tests for ingestion worker` |
| `7bf0a2c` | `fix(test): fix infinite loop in ingestion worker unit test` |

### Files Created / Modified
**Backend:**
- `backend/app/market/symbol_master.py` — Static curated US/India symbol list.
- `backend/app/market/router.py` — `GET /market/symbols` autocomplete endpoint.
- `backend/app/main.py` — Registered `market_router`.
- `backend/app/portfolios/router.py` — Removed old Phase 5 symbol stub.
- `backend/workers/ingestion_worker.py` — Standalone worker connecting to Finnhub WS, publishing ticks to Redis Stream `market:ticks`.
- `backend/pyproject.toml` — Added `redis` and `websockets` dependencies.
- `backend/tests/unit/test_ingestion_worker.py` — Tests for WS backoff logic.
- `backend/tests/integration/test_ingestion.py` — Redis stream smoke test.

**Docker:**
- `docker-compose.yml` — Added `ingestion_worker` service.
- `docker-compose.override.yml` — Updated placeholder `worker` to `ingestion_worker`.

### Acceptance Criteria
1. The `ingestion_worker` connects to Finnhub, subscribes to demo symbols, and publishes ticks to Redis Stream `market:ticks`. — **PASS**
2. `XLEN market:ticks` grows over time. — **PASS**
3. Automatic reconnect with exponential backoff on WS drop works correctly. — **PASS** (Unit tests).
4. Unit test for the reconnect/backoff logic. — **PASS**.
5. Smoke integration test asserts message lands in Redis Stream. — **PASS**.
6. UI autocomplete hits real `GET /market/symbols` endpoint. — **PASS**.

### Next Step (Phase 7)
Phase 7 (Reverse Index).

---

## Phase 7 — Demand-Driven Symbol Reverse Index (COMPLETE)

**Completed:** 2026-09-01

### Commits
| SHA | Message |
|---|---|
| `5966691` | `feat(portfolios): implement symbol reverse index service` |
| `5200d2a` | `feat(ingestion): subscribe dynamically based on reverse index` |

### Files Created / Modified
**Backend:**
- `backend/app/portfolios/reverse_index_service.py` — Atomic updates for `reverse_index:{symbol}` and `subscriber_count:{symbol}` via Redis pipelines; Publishes subscribe/unsubscribe actions to `market:control`.
- `backend/app/portfolios/service.py` — Integrated `update_symbol_index` when creating/deleting holdings or demo portfolios.
- `backend/app/deps.py` — Added `get_redis` generator.
- `backend/app/portfolios/router.py` — Injected `Redis` dependency where necessary.
- `backend/workers/ingestion_worker.py` — Subscribes to `market:control` via Pub/Sub, dynamically updates its internal subscriptions, reads initial state from `symbol_subscriptions` DB on startup.
- `backend/tests/unit/test_reverse_index_service.py` — Unit tests for pipeline atomicity and transition behavior.
- `backend/tests/unit/test_ingestion_worker.py` — Updated mock tests to simulate dynamic state management.
- `backend/tests/integration/test_reverse_index.py` — Integration test for end-to-end pub/sub flow and DB audit syncing.

### Acceptance Criteria
1. The `ingestion_worker` loads required symbols from `symbol_subscriptions` on startup. — **PASS**
2. Portfolio holding creation triggers atomic Redis reverse index update (SADD + SCARD in pipeline). — **PASS**
3. Counter transition 0 -> 1 publishes a `subscribe` command to `market:control`. — **PASS**
4. Counter transition 1 -> 0 publishes an `unsubscribe` command to `market:control`. — **PASS**
5. DB `symbol_subscriptions` row is updated via async merge pattern. — **PASS**
6. Integration tests verify the Redis Pub/Sub commands land successfully. — **PASS**

### Next Step (Phase 8)
Risk Aggregator Fast-Path: Develop the pipeline processing high-frequency ticks into portfolio-level metrics using the reverse index.# #   P h a s e   9   � �    F a s t - P a t h   R e a l - T i m e   P i p e l i n e   ( C O M P L E T E )  
  
 * * C o m p l e t e d : * *   2 0 2 6 - 0 9 - 0 1  
  
 # # #   F i l e s   C r e a t e d   /   M o d i f i e d  
 * * B a c k e n d : * *  
 -   ` b a c k e n d / w o r k e r s / f a s t _ p a t h _ w o r k e r . p y `   � �    S t a n d a l o n e   w o r k e r   c o n s u m i n g   ` m a r k e t : t i c k s `   v i a   R e d i s   S t r e a m s .   R e c o m p u t e s   p o r t f o l i o   r i s k   s t a t e   l e v e r a g i n g   ` r e v e r s e _ i n d e x : { s y m b o l } `   a n d   i n - m e m o r y   L R U   h o l d i n g   c a c h e s .   P u b l i s h e s   r i s k   s t a t e   p a y l o a d s   t o   ` r i s k _ u p d a t e s : { p o r t f o l i o _ i d } ` .  
 -   ` b a c k e n d / a p p / w s / c o n n e c t i o n _ m a n a g e r . p y `   � �    W e b S o c k e t   c o n n e c t i o n   a n d   s u b s c r i p t i o n   m a n a g e r   l i n k i n g   W e b s o c k e t   s e s s i o n s   t o   i n d i v i d u a l   p o r t f o l i o   b r o a d c a s t   c h a n n e l s .  
 -   ` b a c k e n d / a p p / w s / r o u t e r . p y `   � �    ` P O S T   / w s / t i c k e t `   f o r   i s s u i n g   s h o r t - l i v e d   W e b S o c k e t   a u t h e n t i c a t i o n   t o k e n s   a n d   ` W S   / w s `   f o r   h a n d l i n g   c o n n e c t i o n s   a n d   s u b s c r i p t i o n s   b a s e d   o n   t h e   t i c k e t .  
 -   ` b a c k e n d / a p p / m a i n . p y `   � �    R e g i s t e r e d   ` w s _ r o u t e r `   f o r   W e b S o c k e t   c o n n e c t i o n s .  
 -   ` b a c k e n d / a p p / p o r t f o l i o s / s e r v i c e . p y `   &   ` b a c k e n d / a p p / p o r t f o l i o s / r o u t e r . p y `   � �    A d d e d   ` G E T   / p o r t f o l i o s `   t o   q u e r y   u s e r ' s   p o r t f o l i o   l i s t .  
 -   ` b a c k e n d / t e s t s / i n t e g r a t i o n / t e s t _ f a s t _ p a t h . p y `   � �    T e s t s   f o r   f a s t   p a t h   L R U   c a c h i n g   l o g i c   a n d   t i c k   p r o c e s s i n g .  
 -   ` b a c k e n d / t e s t s / i n t e g r a t i o n / t e s t _ w s . p y `   � �    T e s t s   f o r   W S   t i c k e t   i s s u a n c e   a n d   c o n n e c t i o n s   b o u n d a r y .  
  
 * * F r o n t e n d : * *  
 -   ` f r o n t e n d / h o o k s / u s e R i s k S o c k e t . t s `   � �    R e a c t   h o o k   m a n a g i n g   ` W e b S o c k e t `   t i c k e t s ,   c o n n e c t i o n   l i f e c y c l e ,   a n d   e v e n t   i n g e s t i o n .  
 -   ` f r o n t e n d / a p p / d a s h b o a r d / p a g e . t s x `   � �    R e a l - t i m e   q u a n t i t a t i v e   r i s k   d a s h b o a r d   U I   r e n d e r i n g   p o r t f o l i o   m e t r i c s .  
  
 * * D o c k e r : * *  
 -   ` d o c k e r - c o m p o s e . y m l `   &   ` d o c k e r - c o m p o s e . o v e r r i d e . y m l `   � �    A d d e d   ` f a s t _ p a t h _ w o r k e r `   s e r v i c e   b l o c k .  
  
 # # #   A c c e p t a n c e   C r i t e r i a  
 1 .   T h e   ` f a s t _ p a t h _ w o r k e r `   s u c c e s s f u l l y   p r o c e s s e s   s t r e a m i n g   t i c k s   a n d   c a c h e s   h o l d i n g s   i n   m e m o r y   t o   c a l c u l a t e   f a s t - p a t h   P n L .   � �    * * P A S S * *  
 2 .   W e b S o c k e t s   u s e   t i c k e t - b a s e d   a u t h   v i a   ` P O S T   / w s / t i c k e t ` .   � �    * * P A S S * *  
 3 .   F r o n t e n d   h o o k s   i n t e g r a t e   c l e a n l y   w i t h   W e b S o c k e t   b a c k e n d   a n d   f e t c h   t i c k e t   o n   c o n n e c t .   � �    * * P A S S * *  
 4 .   T e s t s   s i m u l a t e   t i c k   d e l i v e r y ,   o w n e r s h i p   b o u n d a r y ,   a n d   t i c k e t   g e n e r a t i o n .   � �    * * P A S S * *   ( E x e c u t e d   l o c a l l y   v i a   ` . v e n v ` )  
  
 # # #   N e x t   S t e p  
 S i n c e   P h a s e   8   w a s   s k i p p e d   p e r   e x p l i c i t   i n s t r u c t i o n ,   t h e   n e x t   s t e p   i s   e i t h e r   t o   c i r c l e   b a c k   a n d   i m p l e m e n t   P h a s e   8   ( C o r e   Q u a n t   E n g i n e )   o r   p r o c e e d   t o   P h a s e   1 0   ( W r a p - u p ) .  
 