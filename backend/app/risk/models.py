"""risk/models.py -- ORM models: risk_snapshots, symbol_subscriptions, garch_fits, regime_states."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"
    __table_args__ = (
        Index("ix_risk_snapshots_portfolio_captured", "portfolio_id", "captured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    var_95: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cvar_95: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    volatility: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    sharpe: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    risk_state: Mapped[str] = mapped_column(Text, nullable=False)  # SAFE|WATCH|HIGH|BREACH
    risk_contribution: Mapped[dict] = mapped_column(JSONB, nullable=False)
    correlation_flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="risk_snapshots")  # type: ignore[name-defined]
    alerts: Mapped[list["Alert"]] = relationship(back_populates="risk_snapshot")  # type: ignore[name-defined]


class SymbolSubscription(Base):
    """Postgres audit mirror of the Redis reverse-index (symbol -> portfolio set)."""

    __tablename__ = "symbol_subscriptions"

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GarchFit(Base):
    """Latest per-symbol GARCH(1,1) parameters, persisted as an audit copy."""

    __tablename__ = "garch_fits"

    symbol: Mapped[str] = mapped_column(Text, primary_key=True)
    omega: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    alpha: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    beta: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    fitted_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)


class RegimeState(Base):
    """HMM output history -- shared, not user-scoped."""

    __tablename__ = "regime_states"
    __table_args__ = (Index("ix_regime_states_captured_at", "captured_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    captured_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    calm_probability: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    stressed_probability: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)

