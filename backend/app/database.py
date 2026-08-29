"""
app/database.py -- Async SQLAlchemy engine, session factory, and declarative Base.

All models import Base from here.  The get_db() dependency is used by FastAPI
route handlers that need a database session.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# -- Engine -------------------------------------------------------------------
# pool_pre_ping keeps the pool healthy after network blips.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
)

# -- Session factory ----------------------------------------------------------
# expire_on_commit=False prevents DetachedInstanceError when returning ORM
# objects after a commit (common pattern in FastAPI handlers).
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# -- Declarative Base ---------------------------------------------------------
class Base(DeclarativeBase):
    """Shared base class for all SQLAlchemy ORM models."""

    pass


# -- FastAPI dependency -------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession; roll back on exception, always close on exit."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
