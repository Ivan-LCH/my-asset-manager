import yfinance as yf
from datetime import datetime, timedelta

def test_fetch():
    tickers = ["AAPL", "005930.KS"]
    today = datetime.now()
    # Mocking the date range logic from stock_updater.py
    # Scenario: Last update was Jan 31, 2026. Today is Feb 3, 2026.
    
    # Let's say last_db_date was "2026-01-31"
    last_db_date_str = "2026-01-31" 
    last_db_date = datetime.strptime(last_db_date_str, "%Y-%m-%d")
    
    fetch_start = last_db_date
    fetch_end = today + timedelta(days=1)
    
    print(f"Testing fetch from {fetch_start} to {fetch_end}")
    
    for t in tickers:
        print(f"Fetching {t}...")
        try:
            dat = yf.Ticker(t)
            hist = dat.history(start=fetch_start, end=fetch_end, auto_adjust=True)
            print(f"Result for {t}:")
            print(hist)
            if hist.empty:
                print(f"WARNING: Empty history for {t}")
        except Exception as e:
            print(f"ERROR fetching {t}: {e}")

if __name__ == "__main__":
    test_fetch()
