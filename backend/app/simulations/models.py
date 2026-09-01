"""simulations/models.py -- ORM model: simulations."""

import uuid
from datetime import datetime, UTC

from sqlalchemy import ForeignKey, Index, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        Index("ix_simulations_portfolio_created", "portfolio_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    num_paths: Mapped[int] = mapped_column(Integer, nullable=False)
    # pending | running | complete | failed
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="simulations")  # type: ignore[name-defined]
