"""auth/schemas.py — Pydantic request/response models for the auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.constants import ALLOWED_SCOPES

# ── Requests ──────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ApiTokenCreateRequest(BaseModel):
    """Request body for POST /auth/api-tokens."""

    scopes: Annotated[list[str], Field(min_length=1)]

    @field_validator("scopes")
    @classmethod
    def scopes_must_be_valid(cls, v: list[str]) -> list[str]:
        invalid = set(v) - ALLOWED_SCOPES
        if invalid:
            raise ValueError(
                f"Invalid scope(s): {invalid}. Allowed: {sorted(ALLOWED_SCOPES)}"
            )
        return v


class SlackLinkRequest(BaseModel):
    """Request body for POST /slack/link (called by the Slack bot)."""

    code: str
    slack_user_id: str


# ── Responses ─────────────────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiTokenResponse(BaseModel):
    """Returned once on token creation; raw_token is never stored and not
    retrievable again — the caller must save it immediately."""

    id: uuid.UUID
    raw_token: str
    scopes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OneTimeCodeResponse(BaseModel):
    """Returned by POST /auth/api-tokens/one-time-code."""

    code: str
    expires_in_seconds: int
