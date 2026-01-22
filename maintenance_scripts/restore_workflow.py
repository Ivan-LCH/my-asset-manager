import os
import shutil
import subprocess
import datetime
import sys

# 설정
NEW_DB = "assets_new.db"
ORIG_DB = "assets.db"
DATA_DIR = "data"
APPS_DIR = "/app" # Docker 내부 경로

def run_step(step_name, command, env):
    print(f"\n========================================")
    print(f"▶️ [Step] {step_name}")
    print(f"========================================")
    result = subprocess.run(command, shell=True, env=env, cwd=APPS_DIR)
    if result.returncode != 0:
        print(f"❌ {step_name} Failed!")
        sys.exit(1)
    print(f"✅ {step_name} Success!")

def main():
    # 환경변수 설정 (새 DB 파일명)
    env = os.environ.copy()
    env["DB_FILE_NAME"] = NEW_DB
    
    new_db_path = os.path.join(APPS_DIR, DATA_DIR, NEW_DB)
    orig_db_path = os.path.join(APPS_DIR, DATA_DIR, ORIG_DB)

    # 1. 기존 Temp DB 삭제
    if os.path.exists(new_db_path):
        os.remove(new_db_path)
        print(f"🗑️ Deleted existing temp DB: {new_db_path}")

    # 2. DB 초기화 (by calling a snippet)
    run_step("Initialize DB", f"python3 -c 'from database import init_db; init_db()'", env)

    # 3. 마이그레이션
    run_step("Migrate from Google Sheets", "python3 migrate_from_gsheet.py", env)
    
    # 4. Ticker 교정 및 USD 설정
    run_step("Fix Tickers & Currency", "python3 fix_tickers.py", env)
    
    # 5. 주가 업데이트
    run_step("Update Stock Prices", "python3 stock_updater.py", env)
    
    # 6. 교체 (Swap)
    print(f"\n========================================")
    print(f"🔄 Swapping Database...")
    print(f"========================================")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{orig_db_path}.{timestamp}.bak"
    
    if os.path.exists(orig_db_path):
        shutil.move(orig_db_path, backup_path)
        print(f"📦 Backup created: {backup_path}")
    
    shutil.move(new_db_path, orig_db_path)
    print(f"✅ Database Restored Successfully! ({orig_db_path})")

if __name__ == "__main__":
    main()
