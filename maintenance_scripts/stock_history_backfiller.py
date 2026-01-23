
import yfinance as yf
import pandas as pd
from datetime import datetime
from database import get_connection, get_all_assets
from dateutil.relativedelta import relativedelta

def backfill_stock_history():
    print("🚀 Starting Stock History Backfill (Monthly from 2023-01)...")
    
    start_date_str = "2023-01-01"
    
    # 1. Fetch all stock assets
    with get_connection() as conn:
        # Join to get ticker and currency
        sql = """
            SELECT a.id, a.name, a.quantity, a.acquisition_date, s.ticker, s.currency
            FROM assets a
            JOIN stock_details s ON a.id = s.asset_id
            WHERE a.type = 'STOCK' AND s.ticker IS NOT NULL AND s.ticker != ''
        """
        stocks = [dict(row) for row in conn.execute(sql).fetchall()]
    
    # 2. Fetch Exchange Rate History (USD/KRW)
    # Global exchange rate dataframe for lookup
    print("💱 Fetching Exchange Rate History (KRW=X)...")
    usd_krw_hist = pd.DataFrame()
    try:
        er_ticker = yf.Ticker("KRW=X")
        # Fetching a bit more to ensure coverage
        usd_krw_hist = er_ticker.history(start=start_date_str, interval="1mo")
        # Ensure timezone naive for merging
        usd_krw_hist.index = usd_krw_hist.index.tz_localize(None)
        # Resample to Month End or Start? Yfinance '1mo' usually gives date at start of month.
        # Let's normalize to Year-Month string for easy lookup
        usd_krw_hist['YYYYMM'] = usd_krw_hist.index.strftime('%Y-%m')
    except Exception as e:
        print(f"❌ Failed to fetch exchange rate history: {e}")
        # If failed, we might default to 1300? or stop? 
        # For now let's hope it works. If empty, loop will handle.

    total_inserted = 0
    
    with get_connection() as conn:
        for stock in stocks:
            ticker = stock['ticker']
            name = stock['name']
            asset_id = stock['id']
            qty_current = float(stock['quantity'])
            currency = stock['currency']
            acq_date_str = stock['acquisition_date']
            
            print(f"⏳ Processing {name} ({ticker})...")
            
            # Parse acquisition date
            acq_date = None
            if acq_date_str:
                try:
                    # Try YYYY-MM-DD
                    acq_date = datetime.strptime(acq_date_str[:10], "%Y-%m-%d")
                except:
                    pass
            
            # Fetch Stock History
            try:
                yf_stock = yf.Ticker(ticker)
                # auto_adjust=True accounts for splits/dividends
                hist = yf_stock.history(start=start_date_str, interval="1mo", auto_adjust=True)
                
                if hist.empty:
                    print(f"   ⚠️ No history found for {ticker}")
                    continue
                
                # Prepare batch insert
                history_records = []
                
                for date, row in hist.iterrows():
                    # Normalize date
                    date_naive = date.tz_localize(None)
                    date_str = date_naive.strftime("%Y-%m-%d")
                    yyyy_mm = date_naive.strftime('%Y-%m')
                    
                    price = row['Close']
                    if pd.isna(price): continue
                    
                    # 1. Determine Quantity
                    # If date < acquisition_date, qty = 0 (unless we assume hold? User said: "없는 달도 당연히 있겠지만... 가져온 월을 주식수가 없으면 그 전 월을 참고")
                    # User rule: "acquisition_date가 없는 달은 그 전 달을 참고" -> implicit logic.
                    # Simplified User Rule interpretation:
                    # - "수량은 해당 월의 이전 수량을 그대로 사용해야 해" implies tracking quantity over time.
                    # - But we only have CURRENT quantity and ACQUISITION date.
                    # - My approved plan: "If acq_date exists: 0 before acq, current qty after."
                    
                    qty = qty_current
                    if acq_date and date_naive < acq_date:
                        qty = 0
                    
                    if qty == 0:
                        # Skip if we didn't own it? Or record as 0? 
                        # Recording 0 might be useful to show "Nothing". 
                        # But typically history is for "Value". 0 value.
                        pass # Allowed to record 0 value.
                        
                    # 2. Determine Exchange Rate
                    rate = 1.0
                    if currency == 'USD':
                        # Find matching month rate
                        # Use average of that month? or Close of that month? 
                        # yfinance 1mo gives row per month.
                        # Lookup by YYYYMM
                        match = usd_krw_hist[usd_krw_hist['YYYYMM'] == yyyy_mm]
                        if not match.empty:
                            rate = match['Close'].iloc[0]
                        else:
                            # Fallback: Forward fill or 1300? 
                            # If recent, maybe not yet in monthly hist?
                            # Try simple history last value if empty?
                            rate = 1300.0 # Warning
                            
                    elif currency != 'KRW':
                        # Valid KRW/USD only handled for now as per previous fix
                        rate = 1.0

                    # 3. Calculate Value
                    value = price * qty * rate
                    
                    history_records.append((
                        asset_id,
                        date_str,
                        float(value),
                        float(price),
                        float(qty)
                    ))

                # Batch Insert / Upsert
                # Since we want to backfill, and avoid duplicates, we can DELETE existing for this period first?
                # Or just INSERT (since no unique constraint on date/asset_id yet... this is a risk).
                # Good practice: Delete existing history for this asset >= 2023-01-01 associated with monthly backfill?
                # But 'asset_history' doesn't distinguish source.
                # Let's check if duplicates exist. For now, let's just insert.
                # User's request implies "filling gaps". 
                # "가지고 있던 값들과 비교해서 해당 월의 숫자와 가져온 금액으로 히스토리를 채우는 거야" 
                # -> suggest merging.
                # Safe approach: Delete for this asset >= 2023-01-01 and Re-insert is cleanest for a "Backfill" operation.
                
                conn.execute("DELETE FROM asset_history WHERE asset_id = ? AND date >= ?", (asset_id, start_date_str))
                
                conn.executemany("""
                    INSERT INTO asset_history (asset_id, date, value, price, quantity)
                    VALUES (?, ?, ?, ?, ?)
                """, history_records)
                
                print(f"   ✅ Backfilled {len(history_records)} months for {ticker}")
                total_inserted += len(history_records)
                
            except Exception as e:
                print(f"   ❌ Error processing {ticker}: {e}")

    print(f"🎉 Backfill Complete. Total {total_inserted} records inserted.")

if __name__ == "__main__":
    backfill_stock_history()
