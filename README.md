# RiskLens

**RiskLens** is a full-stack, event-driven quantitative risk monitoring platform. It continuously watches an investment portfolio, quantifies risk in real time (VaR, CVaR, GARCH volatility, Monte Carlo simulation, EVT tail-risk), detects when risk crosses a configurable budget threshold, and pushes alerts with ranked action recommendations — no manual refreshing required. A tool-calling AI layer (Anthropic Claude + LangGraph) narrates results and answers what-if questions; all numeric computations are performed by the deterministic quant engine, never by the LLM.

> **Advisory only.** RiskLens never executes trades. All recommendations require explicit user action outside the system.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12, async) |
| Database | PostgreSQL 15 (SQLAlchemy 2.0 + asyncpg + Alembic) |
| Cache / Event backbone | Redis 7 (Streams + pub/sub + arq job queue) |
| Market data | Finnhub WebSocket (free tier) |
| AI orchestration | LangGraph + Anthropic Claude API |
| Frontend | Next.js 14 (App Router, TypeScript, Tailwind CSS) |
| Second client | Slack bot (Slack Bolt SDK) |
| Deployment | Render (backend + Postgres + Redis) · Vercel (frontend) |

---

## Setup

> **Note:** Full setup instructions will be written in Phase 24. Below is a placeholder for orientation.

### Prerequisites

- Python ≥ 3.12
- Node ≥ 20 LTS
- Docker + Docker Compose (for the full local stack — added in Phase 2)

### Quick Start (Phase 1 skeleton only)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
# → GET http://localhost:8000/health returns {"status": "ok"}

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000 shows RiskLens placeholder
```

---

## Project Structure

See [`docs/implementation.md`](docs/Implementation.md) for the full engineering specification, folder structure (§9), and phase-by-phase build plan.

---

## Documentation

- [`docs/implementation.md`](docs/Implementation.md) — Master engineering specification (source of truth)
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — Build log
