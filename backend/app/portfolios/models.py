"""portfolios/models.py -- ORM models: portfolios, holdings, risk_budgets."""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, Text, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (Index("ix_portfolios_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, default="My Portfolio")
    source: Mapped[str] = mapped_column(Text, nullable=False)  # demo | csv | manual
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
        nullable=False, default=lambda: datetime.now(UTC)
    )

    # relationships
    user: Mapped["User"] = relationship(back_populates="portfolios")  # type: ignore[name-defined]
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    risk_budget: Mapped["RiskBudget | None"] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", uselist=False
    )
    risk_snapshots: Mapped[list["RiskSnapshot"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    simulations: Mapped[list["Simulation"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    replays: Mapped[list["Replay"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    ai_conversations: Mapped[list["AiConversation"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_holdings_portfolio_symbol"),
        Index("ix_holdings_symbol", "symbol"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")


class RiskBudget(Base):
    __tablename__ = "risk_budgets"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    max_cvar: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    watch_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.60")
    )
    high_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.80")
    )
    breach_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("1.00")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), 
        nullable=False, default=lambda: datetime.now(UTC)
    )

    portfolio: Mapped["Portfolio"] = relationship(back_populates="risk_budget")
