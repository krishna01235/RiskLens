"""scripts/seed_historical_dataset.py -- Load historical price CSV into Postgres.

Usage:
    python -m scripts.seed_historical_dataset

Requires DATABASE_URL to be set in the environment (or a .env file present).
"""

import asyncio
import csv
from datetime import datetime
from pathlib import Path

from app.database import async_session_factory
from app.market.models import HistoricalPrice

async def main() -> None:
    csv_path = Path(__file__).parent.parent / "data" / "historical" / "demo_stress_period.csv"
    if not csv_path.exists():
        print(f"[error] CSV file not found: {csv_path}")
        return

    print(f"Loading historical prices from {csv_path}...")
    
    records_to_insert = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records_to_insert.append(
                HistoricalPrice(
                    symbol=row["symbol"],
                    trading_date=datetime.strptime(row["trading_date"], "%Y-%m-%d").date(),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=int(row["volume"])
                )
            )

    async with async_session_factory() as db:
        # Simple bulk insert
        db.add_all(records_to_insert)
        await db.commit()
        
    print(f"[seed] successfully inserted {len(records_to_insert)} historical price records.")

if __name__ == "__main__":
    asyncio.run(main())
