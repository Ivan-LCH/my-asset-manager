# SQLite 마이그레이션 설계

**작성일:** 2026-01-22  
**완료일:** 2026-01-22  
**상태:** ✅ 완료

---

## 개요

Google Sheets 의존성을 제거하고 SQLite 로컬 DB로 전환

### 결정 사항
- ✅ 자산 유형별 컬럼 분리 (detail1~5 제거)
- ✅ Google Sheets 병행 없이 완전 전환
- ✅ 기존 데이터는 마이그레이션 스크립트로 이관
- ⏸️ Litestream + R2 백업은 후순위로 연기

---

## 아키텍처

```
현재:  Streamlit ←→ utils.py ←→ Google Sheets API
                                      ↓
변경:  Streamlit ←→ utils.py ←→ SQLite (./data/assets.db)
                                      ↓ (추후)
                               Litestream → R2
```

---

## detail1~5 필드 분석 결과

### REAL_ESTATE (부동산)
| 기존 필드 | 새 컬럼명 | 타입 | 설명 |
|----------|----------|------|------|
| detail1 | is_owned | INTEGER | 1=소유, 0=임대 (OWNED/RENTED) |
| detail2 | has_tenant | INTEGER | 1=세입자있음, 0=없음 |
| detail3 | tenant_deposit | REAL | 보증금 |
| detail4 | address | TEXT | 주소 |
| detail5 | loan_amount | REAL | 대출금 |

### STOCK (주식)
| 기존 필드 | 새 컬럼명 | 타입 | 설명 |
|----------|----------|------|------|
| detail1 | account_name | TEXT | 계좌명 (키움증권, 토스증권 등) |
| detail2 | currency | TEXT | 통화 (KRW, USD) |
| detail5 | is_balance_adjustment | INTEGER | 1=잔고보정항목 (BALANCE_ADJUSTMENT) |
| detail5 | is_pension_like | INTEGER | 1=연금성 자산 (Y 또는 PENSION_시작년_월수령액) |
| - | pension_start_year | INTEGER | 연금성일 때 수령 시작 연도 (PENSION_2045_1500000 형식에서 파싱) |
| - | pension_monthly | REAL | 연금성일 때 월 수령액 |

> **특이사항**: detail5가 `Y`, `BALANCE_ADJUSTMENT`, `PENSION_연도_금액` 등 여러 용도로 사용됨

### PENSION (연금)
| 기존 필드 | 새 컬럼명 | 타입 | 설명 |
|----------|----------|------|------|
| detail1 | pension_type | TEXT | NATIONAL, PERSONAL, RETIREMENT |
| detail2 | expected_start_year | INTEGER | 수령 시작 연도 |
| detail3 | expected_monthly_payout | REAL | 월 수령액 |
| detail4 | expected_end_year | INTEGER | 수령 종료 연도 |
| detail5 | annual_growth_rate | REAL | 연간 증가율 (%) |

### SAVINGS (예적금/현금)
| 기존 필드 | 새 컬럼명 | 타입 | 설명 |
|----------|----------|------|------|
| detail5 | is_pension_like | INTEGER | 연금성 여부 (STOCK과 동일 로직) |

### PHYSICAL (실물자산)
- detail 필드 미사용
- 단, `quantity` 기반 계산 사용 (STOCK과 동일)

### ETC (기타)
- detail 필드 미사용

---

## 최종 DB 스키마

### assets (공통 테이블)
```sql
CREATE TABLE assets (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- REAL_ESTATE, STOCK, PENSION, SAVINGS, PHYSICAL, ETC
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
```

### real_estate_details
```sql
CREATE TABLE real_estate_details (
    asset_id TEXT PRIMARY KEY,
    is_owned INTEGER DEFAULT 1,       -- 1=소유, 0=임대
    has_tenant INTEGER DEFAULT 0,     -- 1=세입자있음
    tenant_deposit REAL DEFAULT 0,    -- 보증금
    address TEXT,                     -- 주소
    loan_amount REAL DEFAULT 0,       -- 대출금
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### stock_details
```sql
CREATE TABLE stock_details (
    asset_id TEXT PRIMARY KEY,
    account_name TEXT,                -- 계좌명
    currency TEXT DEFAULT 'KRW',      -- KRW, USD
    is_balance_adjustment INTEGER DEFAULT 0,  -- 잔고보정 항목
    is_pension_like INTEGER DEFAULT 0,        -- 연금성 자산
    pension_start_year INTEGER,       -- 연금 시작 연도
    pension_monthly REAL,             -- 월 수령액
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### pension_details
```sql
CREATE TABLE pension_details (
    asset_id TEXT PRIMARY KEY,
    pension_type TEXT,               -- NATIONAL, PERSONAL, RETIREMENT
    expected_start_year INTEGER,
    expected_end_year INTEGER,
    expected_monthly_payout REAL DEFAULT 0,
    annual_growth_rate REAL DEFAULT 0,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### savings_details
```sql
CREATE TABLE savings_details (
    asset_id TEXT PRIMARY KEY,
    is_pension_like INTEGER DEFAULT 0,
    pension_start_year INTEGER,
    pension_monthly REAL,
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### asset_history
```sql
CREATE TABLE asset_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL,           -- 비수량기반 자산용
    price REAL,           -- 수량기반 자산용 (단가)
    quantity REAL,        -- 수량기반 자산용
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

### settings
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## 파일 변경 계획

| 파일 | 작업 |
|------|------|
| `database.py` | [NEW] DB 초기화, 스키마, CRUD |
| `migrate_from_gsheet.py` | [NEW] 기존 데이터 이관 + detail 필드 분리 |
| `utils.py` | [MODIFY] GSheet → SQLite |
| `app.py` | [MODIFY] parse_asset_details() 수정 |
| `requirements.txt` | [MODIFY] gspread, oauth2client 제거 |

---

## 마이그레이션 순서

1. `database.py` 생성 → 스키마 정의
2. `migrate_from_gsheet.py` 실행 → 데이터 이관 (detail→개별필드)
3. `utils.py` 수정 → SQLite 연동
4. `app.py` 수정 → parse_asset_details() 단순화
5. 테스트 후 Google Sheets 코드 완전 제거

---

## 크로스 체크 포인트

- [ ] REAL_ESTATE: is_owned, has_tenant, tenant_deposit, address, loan_amount
- [ ] STOCK: account_name, currency, is_balance_adjustment, is_pension_like
- [ ] PENSION: pension_type, expected_start_year, expected_end_year, expected_monthly_payout, annual_growth_rate
- [ ] SAVINGS: is_pension_like, pension_start_year, pension_monthly
- [ ] STOCK의 PENSION_연도_금액 파싱 로직 이관
- [ ] asset_history: value vs price/quantity 구분
