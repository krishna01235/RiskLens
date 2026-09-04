"""main.py — FastAPI application factory.

Mounts:
  - CORS middleware (origins from settings)
  - slowapi rate-limiter + 429 exception handler
  - /auth router
  - /portfolios router (Phase 5)
  - /market router stub (Phase 5; replaced by real router in Phase 6)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.auth.router import router as auth_router
from app.ai.router import ai_router
from app.config import get_settings
from app.market.router import market_router
from app.portfolios.router import portfolios_router
from app.risk.router import risk_router
from app.alerts.router import alerts_router
from app.simulations.router import simulations_router
from app.ws.router import router as ws_router

settings = get_settings()

# ── Rate limiter (shared instance) ────────────────────────────────────────────
# Endpoints opt-in with @limiter.limit("5/minute") + request: Request param.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="RiskLens API",
    version="0.1.0",
    description="Event-driven quantitative risk monitoring platform.",
)

# CORS — allow the frontend origin(s) configured in settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # required for the httpOnly refresh cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

# slowapi — must be added after CORS so it can read client IPs
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/auth")
app.include_router(portfolios_router, prefix="/portfolios")
app.include_router(market_router, prefix="/market")
app.include_router(risk_router)
app.include_router(alerts_router)
app.include_router(simulations_router)
app.include_router(ws_router)
app.include_router(ai_router)


# ── Utility endpoints ─────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
