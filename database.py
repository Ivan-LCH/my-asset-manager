# -----------------------------------------------------------------------------------------------------
# Database Module - SQLite 기반 자산 데이터 관리
# -----------------------------------------------------------------------------------------------------
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# -----------------------------------------------------------------------------------------------------
# 설정
# -----------------------------------------------------------------------------------------------------
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_NAME = os.getenv("DB_FILE_NAME", "assets.db")
DB_PATH = os.path.join(DB_DIR, DB_NAME)


# -----------------------------------------------------------------------------------------------------
# 연결 관리
# -----------------------------------------------------------------------------------------------------
@contextmanager
def get_connection():
    """SQLite 연결을 컨텍스트 매니저로 제공"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # dict-like 접근 가능
    conn.execute("PRAGMA foreign_keys = ON")  # FK 강제
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------------------------------
# 스키마 정의
# -----------------------------------------------------------------------------------------------------
SCHEMA_SQL = """
-- 공통 자산 테이블
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    current_value REAL DEFAULT 0,
    acquisition_date TEXT,
    acquisition_price REAL DEFAULT 0,
    disposal_date TEXT,
    disposal_price REAL DEFAULT 0,
    quantity REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 부동산 상세
CREATE TABLE IF NOT EXISTS real_estate_details (
    asset_id TEXT PRIMARY KEY,
    is_owned INTEGER DEFAULT 1,
    has_tenant INTEGER DEFAULT 0,
    tenant_deposit REAL DEFAULT 0,
    address TEXT,
    loan_amount REAL DEFAULT 0,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 주식 상세
CREATE TABLE IF NOT EXISTS stock_details (
    asset_id TEXT PRIMARY KEY,
    account_name TEXT,
    currency TEXT DEFAULT 'KRW',
    is_balance_adjustment INTEGER DEFAULT 0,
    is_pension_like INTEGER DEFAULT 0,
    pension_start_year INTEGER,
    pension_monthly REAL,
    ticker TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 연금 상세
CREATE TABLE IF NOT EXISTS pension_details (
    asset_id TEXT PRIMARY KEY,
    pension_type TEXT,
    expected_start_year INTEGER,
    expected_end_year INTEGER,
    expected_monthly_payout REAL DEFAULT 0,
    annual_growth_rate REAL DEFAULT 0,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 예적금 상세
CREATE TABLE IF NOT EXISTS savings_details (
    asset_id TEXT PRIMARY KEY,
    is_pension_like INTEGER DEFAULT 0,
    pension_start_year INTEGER,
    pension_monthly REAL,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 자산 이력
CREATE TABLE IF NOT EXISTS asset_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,
    price REAL,
    quantity REAL,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);

-- 설정
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(type);
CREATE INDEX IF NOT EXISTS idx_history_asset_id ON asset_history(asset_id);
CREATE INDEX IF NOT EXISTS idx_history_date ON asset_history(date);
"""


def init_db():
    """데이터베이스 초기화 및 스키마 생성"""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
    print(f"✅ Database initialized at {DB_PATH}")


# -----------------------------------------------------------------------------------------------------
# CRUD - Assets
# -----------------------------------------------------------------------------------------------------
def insert_asset(asset: dict) -> str:
    """자산 추가 (공통 + 상세 테이블)"""
    with get_connection() as conn:
        # 공통 테이블
        conn.execute("""
            INSERT INTO assets (id, type, name, current_value, acquisition_date, 
                              acquisition_price, disposal_date, disposal_price, quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asset['id'], asset['type'], asset['name'],
            asset.get('current_value', 0),
            asset.get('acquisition_date'),
            asset.get('acquisition_price', 0),
            asset.get('disposal_date'),
            asset.get('disposal_price', 0),
            asset.get('quantity', 0)
        ))
        
        # 유형별 상세 테이블
        _insert_detail(conn, asset)
        
    return asset['id']


def _insert_detail(conn, asset: dict):
    """유형별 상세 테이블에 삽입"""
    a_type = asset['type']
    a_id = asset['id']
    
    if a_type == 'REAL_ESTATE':
        conn.execute("""
            INSERT INTO real_estate_details (asset_id, is_owned, has_tenant, tenant_deposit, address, loan_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            a_id,
            1 if asset.get('is_owned') else 0,
            1 if asset.get('has_tenant') else 0,
            asset.get('tenant_deposit', 0),
            asset.get('address'),
            asset.get('loan_amount', 0)
        ))
    
    elif a_type == 'STOCK':
        conn.execute("""
            INSERT INTO stock_details (asset_id, account_name, currency, is_balance_adjustment, 
                                       is_pension_like, pension_start_year, pension_monthly, ticker)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a_id,
            asset.get('account_name'),
            asset.get('currency', 'KRW'),
            1 if asset.get('is_balance_adjustment') else 0,
            1 if asset.get('is_pension_like') else 0,
            asset.get('pension_start_year'),
            asset.get('pension_monthly'),
            asset.get('ticker')
        ))
    
    elif a_type == 'PENSION':
        conn.execute("""
            INSERT INTO pension_details (asset_id, pension_type, expected_start_year, 
                                         expected_end_year, expected_monthly_payout, annual_growth_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            a_id,
            asset.get('pension_type'),
            asset.get('expected_start_year'),
            asset.get('expected_end_year'),
            asset.get('expected_monthly_payout', 0),
            asset.get('annual_growth_rate', 0)
        ))
    
    elif a_type == 'SAVINGS':
        conn.execute("""
            INSERT INTO savings_details (asset_id, is_pension_like, pension_start_year, pension_monthly)
            VALUES (?, ?, ?, ?)
        """, (
            a_id,
            1 if asset.get('is_pension_like') else 0,
            asset.get('pension_start_year'),
            asset.get('pension_monthly')
        ))


def update_asset(asset: dict):
    """자산 업데이트"""
    with get_connection() as conn:
        conn.execute("""
            UPDATE assets SET 
                name = ?, current_value = ?, acquisition_date = ?, acquisition_price = ?,
                disposal_date = ?, disposal_price = ?, quantity = ?, updated_at = ?
            WHERE id = ?
        """, (
            asset['name'], asset.get('current_value', 0),
            asset.get('acquisition_date'), asset.get('acquisition_price', 0),
            asset.get('disposal_date'), asset.get('disposal_price', 0),
            asset.get('quantity', 0), datetime.now().isoformat(),
            asset['id']
        ))
        
        # 상세 테이블 업데이트 (DELETE + INSERT)
        _delete_detail(conn, asset['id'], asset['type'])
        _insert_detail(conn, asset)


def update_asset_value_only(asset_id: str, current_value: float, quantity: float = None):
    """자산의 현재 가치(및 수량)만 업데이트 (상세 정보 유지)"""
    with get_connection() as conn:
        if quantity is not None:
            conn.execute("""
                UPDATE assets SET current_value = ?, quantity = ?, updated_at = ?
                WHERE id = ?
            """, (current_value, quantity, datetime.now().isoformat(), asset_id))
        else:
            conn.execute("""
                UPDATE assets SET current_value = ?, updated_at = ?
                WHERE id = ?
            """, (current_value, datetime.now().isoformat(), asset_id))


def _delete_detail(conn, asset_id: str, a_type: str):
    """유형별 상세 테이블에서 삭제"""
    table_map = {
        'REAL_ESTATE': 'real_estate_details',
        'STOCK': 'stock_details',
        'PENSION': 'pension_details',
        'SAVINGS': 'savings_details'
    }
    if a_type in table_map:
        conn.execute(f"DELETE FROM {table_map[a_type]} WHERE asset_id = ?", (asset_id,))


def delete_asset(asset_id: str):
    """자산 삭제 (CASCADE로 상세/이력 자동 삭제)"""
    with get_connection() as conn:
        conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))


def get_all_assets() -> list:
    """모든 자산 조회 (상세 정보 JOIN)"""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM assets").fetchall()
        assets = []
        for row in rows:
            asset = dict(row)
            # 상세 정보 가져오기
            detail = _get_detail(conn, asset['id'], asset['type'])
            if detail:
                asset.update(detail)
            # 이력 가져오기
            asset['history'] = get_asset_history(asset['id'])
            assets.append(asset)
        return assets


def _get_detail(conn, asset_id: str, a_type: str) -> dict:
    """유형별 상세 정보 조회"""
    table_map = {
        'REAL_ESTATE': 'real_estate_details',
        'STOCK': 'stock_details',
        'PENSION': 'pension_details',
        'SAVINGS': 'savings_details'
    }
    if a_type not in table_map:
        return {}
    
    row = conn.execute(f"SELECT * FROM {table_map[a_type]} WHERE asset_id = ?", (asset_id,)).fetchone()
    if row:
        d = dict(row)
        d.pop('asset_id', None)
        return d
    return {}


# -----------------------------------------------------------------------------------------------------
# CRUD - History
# -----------------------------------------------------------------------------------------------------
def insert_history(asset_id: str, history_item: dict):
    """이력 추가"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO asset_history (asset_id, date, value, price, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, (
            asset_id,
            history_item.get('date'),
            history_item.get('value'),
            history_item.get('price'),
            history_item.get('quantity')
        ))


def insert_history_batch(asset_id: str, history_list: list):
    """이력 일괄 추가"""
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO asset_history (asset_id, date, value, price, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (asset_id, h.get('date'), h.get('value'), h.get('price'), h.get('quantity'))
            for h in history_list
        ])


def get_asset_history(asset_id: str) -> list:
    """특정 자산의 이력 조회"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT date, value, price, quantity FROM asset_history 
            WHERE asset_id = ? ORDER BY date
        """, (asset_id,)).fetchall()
        return [dict(row) for row in rows]


def get_last_history_date(asset_id: str) -> str:
    """자산의 마지막 이력 날짜 조회 (없으면 None)"""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT MAX(date) as last_date FROM asset_history WHERE asset_id = ?
        """, (asset_id,)).fetchone()
        return row['last_date'] if row and row['last_date'] else None


def delete_asset_history(asset_id: str):
    """특정 자산의 이력 전체 삭제"""
    with get_connection() as conn:
        conn.execute("DELETE FROM asset_history WHERE asset_id = ?", (asset_id,))


# -----------------------------------------------------------------------------------------------------
# CRUD - Settings
# -----------------------------------------------------------------------------------------------------
def get_settings() -> dict:
    """모든 설정 조회"""
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row['key']: row['value'] for row in rows}


def set_setting(key: str, value):
    """설정 저장 (UPSERT)"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))


def set_settings_batch(settings: dict):
    """설정 일괄 저장"""
    for key, value in settings.items():
        set_setting(key, value)


# -----------------------------------------------------------------------------------------------------
# 초기화 실행 (모듈 import 시)
# -----------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
