"""auth/schemas.py — Pydantic request/response models for the auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Requests ──────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
