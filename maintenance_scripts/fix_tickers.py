import sqlite3
from database import get_connection

updates = {
    "ACE 테슬라벨류체인액티브": "457480.KS",
    "ACE 테슬라밸류체인액티브": "457480.KS",
    "GLD": "GLD",
    "KODEX AI전력핵심설비": "487240.KS",
    "KODEX 미국AI테크TOP10타겟커버드콜": "483280.KS",
    "QQQM": "QQQM",
    "SOL 팔란티어미국채커버드콜혼합": "0040X0.KS",
    "TIGER 글로벌AI전력인프라액티브": "491010.KS",
    "TIGER 미국배당다우존스": "458730.KS",
    "TIGER 테슬라채권혼합Fn": "447770.KS",
    "알파벳A": "GOOGL",
    "테슬라": "TSLA",
    "팔란티어": "PLTR"
}

def correct_tickers():
    with get_connection() as conn:
        # 오타 수정
        conn.execute("UPDATE assets SET name = 'KODEX AI전력핵심설비' WHERE name LIKE '%KODEX AI전력핵실설비%'")
        
        count = 0
        for name, ticker in updates.items():
            if not ticker: continue
            cursor = conn.execute("UPDATE stock_details SET ticker = ? WHERE asset_id IN (SELECT id FROM assets WHERE name = ?)", (ticker, name))
            if cursor.rowcount > 0:
                print(f"Fixed: {name} -> {ticker}")
                count += cursor.rowcount
        print(f"Total corrections: {count}")

        # 미국 주식 USD 설정
        usd_stocks = ['TSLA', 'PLTR', 'GOOGL', 'QQQM', 'GLD']
        ph = ','.join(['?']*len(usd_stocks))
        cursor = conn.execute(f"UPDATE stock_details SET currency = 'USD' WHERE ticker IN ({ph})", usd_stocks)
        print(f"Updated {cursor.rowcount} stocks to USD currency.")

if __name__ == "__main__":
    correct_tickers()
