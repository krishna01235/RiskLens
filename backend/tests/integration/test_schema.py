"""tests/integration/test_schema.py

Assert that every §8.2 table exists in the database after migration.

Requires a live Postgres instance reachable via DATABASE_URL.
Run with:  pytest tests/integration/test_schema.py -v
"""

import os
import pytest
import asyncpg

# All 17 domain tables defined in §8.2
EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "api_tokens",
    "portfolios",
    "holdings",
    "risk_budgets",
    "risk_snapshots",
    "alerts",
    "decisions",
    "simulations",
    "replays",
    "replay_daily_states",
    "backtest_results",
    "ai_conversations",
    "ai_messages",
    "symbol_subscriptions",
    "garch_fits",
    "regime_states",
}


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set; skipping integration test")
    # asyncpg uses postgresql:// not postgresql+asyncpg://
    return url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.mark.asyncio
async def test_all_tables_exist(db_url: str) -> None:
    """Query information_schema.tables and assert all expected tables are present."""
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            """
        )
        actual_tables = {row["table_name"] for row in rows}
        missing = EXPECTED_TABLES - actual_tables
        assert not missing, f"Missing tables after migration: {sorted(missing)}"
    finally:
        await conn.close()
