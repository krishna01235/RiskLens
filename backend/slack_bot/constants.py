"""slack_bot/constants.py — Re-exports auth constants so bot code has a single import path."""

from app.auth.constants import ALLOWED_SCOPES, ONE_TIME_CODE_TTL_SECONDS

__all__ = ["ALLOWED_SCOPES", "ONE_TIME_CODE_TTL_SECONDS"]
