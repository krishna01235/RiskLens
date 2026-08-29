"""alembic/env.py -- Async-compatible Alembic environment.

Uses SQLAlchemy asyncpg engine wrapped with run_sync so that Alembic`s
synchronous migration runner can drive an async engine without a separate
sync connection string.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# -- Import application Settings so DATABASE_URL is read from env / .env ------
from app.config import get_settings

# -- Import Base and ALL models so autogenerate can see every table ------------
from app.database import Base  # noqa: F401 - Base must be imported before models

# models must be imported so their tables register on Base.metadata
import app.auth.models  # noqa: F401
import app.portfolios.models  # noqa: F401
import app.risk.models  # noqa: F401
import app.alerts.models  # noqa: F401
import app.simulations.models  # noqa: F401
import app.replays.models  # noqa: F401
import app.ai.models  # noqa: F401

# -- Alembic Config object ----------------------------------------------------
config = context.config

# Override sqlalchemy.url from application settings (reads DATABASE_URL env var)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData object for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in `offline` mode (no live DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations via run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in `online` mode using the async engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
