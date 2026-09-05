"""Application configuration via Pydantic Settings.

All settings are read from environment variables (or a .env file in local
development).  A single cached instance is obtained via ``get_settings()``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: Annotated[
        str,
        Field(
            default="postgresql+asyncpg://risklens:risklens@localhost:5432/risklens",
            description="Async SQLAlchemy connection string (asyncpg driver).",
        ),
    ]

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: Annotated[
        str,
        Field(
            default="redis://localhost:6379/0",
            description="Redis connection URL used for caching, pub/sub, and Streams.",
        ),
    ]

    # ── Auth / Security ────────────────────────────────────────────────────────
    secret_key: Annotated[
        str,
        Field(
            default="change-me-generate-a-real-secret",
            description=(
                "HMAC secret for JWT signing. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            ),
        ),
    ]
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── External APIs ──────────────────────────────────────────────────────────
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Slack ──────────────────────────────────────────────────────────────────
    slack_bot_token: str = ""
    slack_signing_secret: str = ""

    # ── CORS ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins. Add the deployed frontend URL in production.",
    )

    # ── Cookie ─────────────────────────────────────────────────────────────────
    cookie_secure: bool = Field(
        default=False,
        description=(
            "Set to True in production (HTTPS). "
            "Controls the Secure flag on the httpOnly refresh token cookie. "
            "Set via COOKIE_SECURE=true environment variable."
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
