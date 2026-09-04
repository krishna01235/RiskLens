"""market/models.py -- ORM models for market data."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (
        UniqueConstraint("symbol", "trading_date", name="uix_historical_prices_symbol_date"),
        Index("ix_historical_prices_symbol_date", "symbol", "trading_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)
