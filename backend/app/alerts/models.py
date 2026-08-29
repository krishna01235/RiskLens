"""alerts/models.py -- ORM models: alerts, decisions."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_portfolio_fired", "portfolio_id", "fired_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_snapshots.id"),
        nullable=False,
    )
    from_state: Mapped[str] = mapped_column(Text, nullable=False)
    to_state: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    dismissed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="alerts")  # type: ignore[name-defined]
    risk_snapshot: Mapped["RiskSnapshot"] = relationship(back_populates="alerts")  # type: ignore[name-defined]
    decisions: Mapped[list["Decision"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # [{label, expected_return, cvar, p_loss}, ...]
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    alert: Mapped["Alert"] = relationship(back_populates="decisions")
