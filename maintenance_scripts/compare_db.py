
import sqlite3
import os

FILES = [
    "/home/ivan/my_prog/asset_manager/data/assets.db",
    "/home/ivan/my_prog/asset_manager/data/assets.db.corrupted_20260123.bak"
]

def check_file(path):
    print(f"\n🔍 Checking {os.path.basename(path)}...")
    if not os.path.exists(path):
        print("   File not found.")
        return

    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Count stock details
        try:
            cursor.execute("SELECT COUNT(*) FROM stock_details")
            cnt = cursor.fetchone()[0]
            print(f"   stock_details count: {cnt}")
        except:
            print("   stock_details table error or missing")

        # Count assets of type STOCK
        try:
            cursor.execute("SELECT COUNT(*), name FROM assets WHERE type='STOCK' GROUP BY id")
            rows = cursor.fetchall()
            print(f"   STOCK assets count: {len(rows)}")
            for r in rows:
                print(f"     - {r[1]}")
        except:
             print("   assets table error")
             
        conn.close()
    except Exception as e:
        print(f"   Error opening DB: {e}")

if __name__ == "__main__":
    for f in FILES:
        check_file(f)
