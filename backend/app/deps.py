"""deps.py — Shared FastAPI dependencies.

Every protected endpoint imports ``get_current_user`` from this module.
Row-level ownership enforcement is done at the *service layer* of each domain
module (not just here), as required by the ownership-and-security-review skill.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.service import decode_access_token
from app.database import get_db

# The token URL is used only to populate the Swagger UI "Authorize" dialog.
# Actual token issuance happens in /auth/login.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """Decode the Bearer access token and return the authenticated User.

    Raises HTTP 401 if:
    - No Authorization header is present
    - The token is expired, malformed, or has an invalid signature
    - The user UUID in the token no longer exists in the database

    Usage::

        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exception

    try:
        user_id: uuid.UUID = decode_access_token(token)
    except (JWTError, ValueError):
        raise credentials_exception from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user
