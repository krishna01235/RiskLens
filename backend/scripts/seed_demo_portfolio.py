"""scripts/seed_demo_portfolio.py -- Seed the fixed demo portfolio for a user.

Usage:
    python -m scripts.seed_demo_portfolio --user-id <uuid> [--market us|india]

Requires DATABASE_URL to be set in the environment (or a .env file present).
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from app.database import async_session_factory
from app.portfolios.schemas import DemoMarket
from app.portfolios.service import create_demo_portfolio


async def _seed(user_id: uuid.UUID, market: DemoMarket) -> None:
    async with async_session_factory() as db:
        portfolio = await create_demo_portfolio(db, user_id, market)
        print(
            f"[seed] demo portfolio created: id={portfolio.id} "
            f"name={portfolio.name!r} holdings={len(portfolio.holdings)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a demo portfolio for an existing user."
    )
    parser.add_argument(
        "--user-id",
        required=True,
        type=uuid.UUID,
        help="UUID of the user to seed the portfolio for.",
    )
    parser.add_argument(
        "--market",
        choices=["us", "india"],
        default="us",
        help="Which demo portfolio to seed (default: us).",
    )
    args = parser.parse_args()

    market = DemoMarket(args.market)
    asyncio.run(_seed(args.user_id, market))


if __name__ == "__main__":
    main()
