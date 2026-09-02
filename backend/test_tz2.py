import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class TempUser(Base):
    __tablename__ = "temp_users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    # The actual column in DB is TIMESTAMPTZ because we will create it manually

async def main():
    db_url = "postgresql+asyncpg://risklens:risklens@localhost:5432/risklens"
    engine = create_async_engine(db_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE temp_users ALTER COLUMN created_at TYPE TIMESTAMPTZ;"))

# Actually I don't need to run it, let's just inspect the actual DB data type via python
