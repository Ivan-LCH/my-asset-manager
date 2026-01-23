
import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
import sys
import os

# Mock the environment to run the function
def safe_float(val):
    try:
        if val is None or str(val).strip() == "": return 0.0
        return float(str(val).replace(",", ""))
    except:
        return 0.0

def get_connection():
    return sqlite3.connect("data/assets.db")

def _get_detail(conn, asset_id: str, a_type: str) -> dict:
    table_map = {
        'REAL_ESTATE': 'real_estate_details',
        'STOCK': 'stock_details',
        'PENSION': 'pension_details',
        'SAVINGS': 'savings_details'
    }
    if a_type not in table_map: return {}
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT * FROM {table_map[a_type]} WHERE asset_id = ?", (asset_id,)).fetchone()
    if row:
        d = dict(row)
        d.pop('asset_id', None)
        return d
    return {}

def get_real_assets():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM assets").fetchall()
        assets = []
        for row in rows:
            asset = dict(row)
            detail = _get_detail(conn, asset['id'], asset['type'])
            if detail: asset.update(detail)
            asset['history'] = []
            assets.append(asset)
            
        history_rows = conn.execute("SELECT * FROM asset_history ORDER BY date").fetchall()
        
        history_map = {}
        for h in history_rows:
            aid = h['asset_id']
            if aid not in history_map: history_map[aid] = []
            history_map[aid].append({
                'date': h['date'], 
                'value': h['value'], 
                'price': h['price'], 
                'quantity': h['quantity']
            })
            
        for asset in assets:
            if asset['id'] in history_map:
                asset['history'] = history_map[asset['id']]
                
        return assets

# Import the logic function (copied/adapted from app.py to ensure identical logic)
def generate_history_df(assets, type_filter=None):
    if not assets: return pd.DataFrame()
    target_assets = [a for a in assets if (type_filter is None or a['type'] == type_filter)]
    if not target_assets: return pd.DataFrame()

    today = datetime.now()
    is_long_term = (type_filter is None) or (type_filter == 'REAL_ESTATE')
    period_years = 10 if is_long_term else 3
    start_limit = today - timedelta(days=365 * period_years)
    
    all_records = []
    
    for asset in target_assets:
        a_id = asset['id']
        a_name = asset['name']
        a_type = asset['type']
        a_acc = asset.get('accountName', '기타')
        
        # DEBUG
        # print(f"Processing {a_name} ({a_type})... History Len: {len(asset.get('history', []))}")

        acq_date_str = str(asset.get('acquisitionDate', '2023-01-01'))[:10]
        try: acq_date = pd.to_datetime(acq_date_str)
        except: acq_date = pd.to_datetime('2023-01-01')
        
        acq_price = safe_float(asset.get('acquisitionPrice', 0))
        qty = safe_float(asset.get('quantity', 0))
        is_qty_based = a_type in ['STOCK', 'PHYSICAL']
        
        if is_qty_based and qty > 0:
            init_val = acq_price * qty
        else:
            init_val = acq_price
            
        all_records.append({
            'asset_id': a_id, 'date': acq_date, 'value': init_val, 'name': a_name
        })
        
        hist_raw = asset.get('history', [])
        for h in hist_raw:
            d_str = h.get('date')
            if not d_str: continue
            
            val = 0
            if h.get('value') is not None:
                val = safe_float(h['value'])
            elif h.get('price') is not None and h.get('quantity') is not None:
                val = safe_float(h['price']) * safe_float(h['quantity'])
            
            # DEBUG
            if str(a_id) == '2':
                print(f"DEBUG TSLA RAW: {h}")
                print(f"DEBUG VAL CALC: v={h.get('value')}, p={h.get('price')}, q={h.get('quantity')} -> ResultVal={val}")

            all_records.append({
                'asset_id': a_id, 'date': pd.to_datetime(d_str), 'value': val, 'name': a_name, 'type': a_type, 'account': a_acc, 'is_real_estate': (a_type=='REAL_ESTATE'),
                'loan': safe_float(asset.get('loanAmount', 0)) + safe_float(asset.get('tenantDeposit', 0))
            })
            
        # Curr
        last_date = pd.to_datetime(today.date())
        last_val = safe_float(asset.get('currentValue', 0))
        all_records.append({
            'asset_id': a_id, 'date': last_date, 'value': last_val, 'name': a_name
        })

    if not all_records: return pd.DataFrame()
    
    df_raw = pd.DataFrame(all_records)
    
    # DEBUG: Check TSLA in df_raw
    print("\n[df_raw TSLA check]")
    print(df_raw[df_raw['asset_id'].astype(str) == '2'].tail(10))
    print(df_raw[df_raw['asset_id'].astype(str) == '2']['value'].describe())

    df_raw = df_raw.sort_values('date').drop_duplicates(subset=['asset_id', 'date'], keep='last')
    
    # DEBUG
    print("\n[df_raw sample]")
    print(df_raw.tail())

    df_pivot = df_raw.pivot(index='date', columns='asset_id', values='value')
    
    full_idx = pd.date_range(start=start_limit, end=today, freq='D')
    df_pivot = df_pivot.reindex(full_idx).ffill().fillna(0)
    
    # Check max values
    print("\n[Pivot Max Values]")
    print(df_pivot.max())

    return df_pivot

def run_debug():
    assets = get_real_assets()
    print(f"Loaded {len(assets)} assets.")
    
    # Filter for STOCK only as user mentioned "주식 부문"
    print("Testing STOCK chart generation...")
    df = generate_history_df(assets, type_filter='STOCK')
    
    if df.empty:
        print("Generated DataFrame is EMPTY.")
    else:
        print("Generated DataFrame OK.")

if __name__ == "__main__":
    run_debug()
