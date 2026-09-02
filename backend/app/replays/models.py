"""replays/models.py -- ORM models: replays, replay_daily_states, backtest_results."""

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Replay(Base):
    __tablename__ = "replays"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_key: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. '2022_rate_shock'
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="replays")  # type: ignore[name-defined]
    daily_states: Mapped[list["ReplayDailyState"]] = relationship(
        back_populates="replay", cascade="all, delete-orphan"
    )
    backtest_result: Mapped["BacktestResult | None"] = relationship(
        back_populates="replay", cascade="all, delete-orphan", uselist=False
    )


class ReplayDailyState(Base):
    __tablename__ = "replay_daily_states"
    __table_args__ = (
        Index("ix_replay_daily_states_replay_date", "replay_id", "trading_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    replay_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replays.id", ondelete="CASCADE"),
        nullable=False,
    )
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    var_95: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    actual_return: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    risk_state: Mapped[str] = mapped_column(Text, nullable=False)

    replay: Mapped["Replay"] = relationship(back_populates="daily_states")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    replay_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replays.id", ondelete="CASCADE"),
        nullable=False,
    )
    predicted_breach_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    actual_breach_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    kupiec_statistic: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    p_value: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)

    replay: Mapped["Replay"] = relationship(back_populates="backtest_result")
