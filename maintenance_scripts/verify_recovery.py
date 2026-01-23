
import sqlite3
import os
from datetime import datetime

DB_PATH = "/home/ivan/my_prog/asset_manager/data/assets.db"

def verify_db():
    if not os.path.exists(DB_PATH):
        print("❌ Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check asset_history count
    cursor.execute("SELECT Count(*) FROM asset_history")
    count = cursor.fetchone()[0]
    print(f"Total history records: {count}")

    # Check the latest date in history
    cursor.execute("SELECT MAX(date) FROM asset_history")
    last_date = cursor.fetchone()[0]
    print(f"Latest history date: {last_date}")

    conn.close()

if __name__ == "__main__":
    verify_db()
