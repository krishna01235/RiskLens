import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.models import User
from app.config import get_settings

async def main():
    db_url = "postgresql+asyncpg://risklens:risklens@localhost:5432/risklens"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Try to insert a User with an AWARE datetime
        user = User(
            id=uuid.uuid4(),
            email=f"test_{uuid.uuid4().hex}@test.com",
            password_hash="test",
            created_at=datetime.now(UTC) # AWARE DATETIME
        )
        session.add(user)
        try:
            await session.commit()
            print("SUCCESS")
        except Exception as e:
            print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
