"""tests/integration/test_citext_email.py

Verify that users.email is CITEXT: two emails differing only in case must
conflict on insert (i.e. the unique constraint is case-insensitive).
"""

import os
import uuid
import pytest
import asyncpg


@pytest.mark.asyncio
async def test_email_citext_unique_conflict(db_url: str) -> None:
    """Inserting the same email in different cases must raise a UniqueViolationError."""
    asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(asyncpg_url)
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    try:
        # Insert first user with lowercase email
        await conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, created_at)
            VALUES ($1, $2, 'hash', 'user', now())
            """,
            uid1,
            "test.citext@example.com",
        )

        # Attempt to insert a second user with uppercase email — must fail
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                """
                INSERT INTO users (id, email, password_hash, role, created_at)
                VALUES ($1, $2, 'hash', 'user', now())
                """,
                uid2,
                "TEST.CITEXT@EXAMPLE.COM",  # same email, different case
            )
    finally:
        # Clean up: remove the successfully-inserted test row
        await conn.execute("DELETE FROM users WHERE id = $1", uid1)
        await conn.close()
