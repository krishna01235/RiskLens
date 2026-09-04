# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "yfinance",
#     "pandas",
# ]
# ///

import yfinance as yf
import pandas as pd
from pathlib import Path
import os

# The 20 demo portfolio symbols (10 US, 10 India)
DEMO_SYMBOLS_US = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", 
    "JPM", "JNJ", "XOM", "BRK-B", "UNH"
]

DEMO_SYMBOLS_INDIA = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "BAJFINANCE.NS", "SBIN.NS", "WIPRO.NS", "KOTAKBANK.NS"
]

ALL_SYMBOLS = DEMO_SYMBOLS_US + DEMO_SYMBOLS_INDIA

# Q1 2020 COVID Crash Stress Period
START_DATE = "2020-02-01"
END_DATE = "2020-05-31"

def fetch_data():
    print(f"Fetching historical data for {len(ALL_SYMBOLS)} symbols from {START_DATE} to {END_DATE}...")
    
    # Download data using yfinance
    df = yf.download(ALL_SYMBOLS, start=START_DATE, end=END_DATE, group_by='ticker', auto_adjust=False)
    
    records = []
    
    # yfinance returns a MultiIndex column DataFrame when multiple tickers are downloaded
    for symbol in ALL_SYMBOLS:
        symbol_data = df[symbol] if len(ALL_SYMBOLS) > 1 else df
        # Drop rows where all price data is NaN (e.g. holidays in one market but not the other)
        symbol_data = symbol_data.dropna(how='all')
        
        for date, row in symbol_data.iterrows():
            # Drop NaN for specific row if missing (e.g. holiday in India but not US)
            if pd.isna(row['Close']):
                continue
                
            # Strip the '.NS' suffix for Indian symbols so they match the RiskLens DB
            db_symbol = symbol.replace('.NS', '')
            
            records.append({
                'symbol': db_symbol,
                'trading_date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 4),
                'high': round(row['High'], 4),
                'low': round(row['Low'], 4),
                'close': round(row['Close'], 4),
                'volume': int(row['Volume'])
            })
            
    out_df = pd.DataFrame(records)
    
    # Ensure target directory exists
    out_dir = Path(__file__).parent.parent / "data" / "historical"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / "demo_stress_period.csv"
    out_df.sort_values(by=['symbol', 'trading_date'], inplace=True)
    out_df.to_csv(out_path, index=False)
    
    print(f"Successfully generated {out_path} with {len(out_df)} records.")

if __name__ == "__main__":
    fetch_data()
