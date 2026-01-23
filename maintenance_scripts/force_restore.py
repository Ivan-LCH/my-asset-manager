
import yfinance as yf
from datetime import datetime, timedelta
import time
from database import get_connection, insert_history_batch

def force_restore_stocks():
    print("🚀 Forcing Full Stock History Restore (from 2023-01-01)...")
    
    with get_connection() as conn:
        # 1. Get all stocks
        sql = """
            SELECT a.id, a.name, a.quantity, s.ticker, s.currency, a.current_value, a.acquisition_date
            FROM assets a
            JOIN stock_details s ON a.id = s.asset_id
            WHERE a.type = 'STOCK' AND s.ticker IS NOT NULL AND s.ticker != ''
        """
        assets = [dict(row) for row in conn.execute(sql).fetchall()]
    
    print(f"📋 Found {len(assets)} stock assets.")

    # 2. Delete existing history for these assets
    with get_connection() as conn:
        for a in assets:
            conn.execute("DELETE FROM asset_history WHERE asset_id = ?", (a['id'],))
    print("🗑️  Cleared existing stock history.")

    # 3. Fetch and insert
    ticker_map = {}
    for a in assets:
        t = a['ticker'].upper().strip()
        if t not in ticker_map: ticker_map[t] = []
        ticker_map[t].append(a)

    today = datetime.now()
    updated_count = 0

    for ticker, asset_list in ticker_map.items():
        try:
            print(f"⏳ Processing: {ticker}")
            yf_ticker = yf.Ticker(ticker)
            
            # Fetch full history
            hist = yf_ticker.history(start="2023-01-01", end=today + timedelta(days=1), auto_adjust=True)
            
            if hist.empty:
                print(f"   ⚠️ No data for {ticker}")
                continue

            # Get exchange rate (simplified)
            currency = asset_list[0]['currency']
            rate = 1.0
            if currency != 'KRW':
                 # Try to get rate
                 try:
                     fx = yf.Ticker(f"{currency}KRW=X")
                     rate = fx.fast_info.get('last_price', 1300.0)
                 except:
                     rate = 1300.0 # Fallback

            for asset in asset_list:
                qty = float(asset['quantity'])
                if qty == 0: continue
                
                acq_date_str = asset.get('acquisition_date')
                acq_date = None
                if acq_date_str:
                    try: acq_date = datetime.strptime(acq_date_str[:10], "%Y-%m-%d")
                    except: pass
                
                records = []
                for ts, row in hist.iterrows():
                    r_date = ts.to_pydatetime().replace(tzinfo=None)
                    
                    # Quantity logic: 0 before acquisition
                    r_qty = qty
                    if acq_date and r_date < acq_date: 
                        r_qty = 0
                    
                    price = row['Close']
                    value = price * r_qty * rate
                    
                    records.append({
                        'date': r_date.strftime("%Y-%m-%d"),
                        'price': price,
                        'quantity': r_qty,
                        'value': value
                    })
                
                if records:
                    insert_history_batch(asset['id'], records)
                    # Update current value to latest
                    latest = records[-1]
                    # Direct update to assets table to ensure consistency
                    with get_connection() as conn:
                        conn.execute("UPDATE assets SET current_value = ?, updated_at = ? WHERE id = ?", 
                                     (latest['value'], datetime.now().isoformat(), asset['id']))

                updated_count += 1
                
        except Exception as e:
            print(f"   ❌ Error {ticker}: {e}")

    print(f"✅ Recovery Completed. Updated {updated_count} assets.")

if __name__ == "__main__":
    force_restore_stocks()
