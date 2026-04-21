import yfinance as yf
import pandas as pd
from typing import Optional

class DataFetcher:
    @staticmethod
    def get_stock_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Fetches historical stock data from Yahoo Finance.
        Automatically handles NSE/BSE suffixes and retries with fallback period.
        """
        if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
            ticker = f"{ticker}.NS"

        # Try preferred period first, fall back to shorter periods on failure
        periods_to_try = [period, "1y", "6mo"]
        for p in periods_to_try:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period=p, interval=interval)
                if df is not None and not df.empty:
                    return df
            except (TypeError, KeyError, Exception):
                continue

        raise ValueError(f"No data returned from Yahoo Finance for ticker: {ticker}")

    @staticmethod
    def get_realtime_price(ticker: str) -> float:
        """
        Fetches the most recent price for a ticker.
        """
        if not (ticker.endswith(".NS") or ticker.endswith(".BO")):
            ticker = f"{ticker}.NS"
        
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
        return 0.0

if __name__ == "__main__":
    # Test fetcher
    fetcher = DataFetcher()
    reliance_data = fetcher.get_stock_data("RELIANCE")
    print(f"Reliance Data (latest 5 rows):\n{reliance_data.tail()}")
    print(f"Live Price: {fetcher.get_realtime_price('RELIANCE')}")
