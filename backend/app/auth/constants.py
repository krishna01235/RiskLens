"""app/auth/constants.py — Auth-layer named constants.

Single source of truth for values used across service functions,
schema validators, and the Slack bot. Import from here; never
re-declare locally.
"""

# Number of random bytes used to generate an API token (hex-encoded
# to a 64-char string).  Provides 256 bits of entropy.
API_TOKEN_BYTE_LENGTH: int = 32

# Complete set of valid API token scopes.
# Schema validators and service functions both import this set — it is
# never duplicated.
ALLOWED_SCOPES: frozenset[str] = frozenset({"read", "whatif"})

# Redis key TTL for one-time login codes (seconds).
# A user has 5 minutes to paste the code into Slack before it expires.
ONE_TIME_CODE_TTL_SECONDS: int = 300
