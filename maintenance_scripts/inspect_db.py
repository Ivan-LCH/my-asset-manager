
import sqlite3
import os

DB_PATH = "/home/ivan/my_prog/asset_manager/data/assets.db"

def inspect_db():
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = ["assets", "stock_details", "asset_history"]
    
    print("--- Database Inspection ---")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}': {count} rows")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                print(f"  Sample data ({table}):")
                for row in rows:
                    print(f"    {dict(row)}")
        except Exception as e:
            print(f"Error querying {table}: {e}")

    conn.close()

if __name__ == "__main__":
    inspect_db()
