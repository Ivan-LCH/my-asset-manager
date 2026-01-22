# -----------------------------------------------------------------------------------------------------
# Google Sheets → SQLite 마이그레이션 스크립트
# -----------------------------------------------------------------------------------------------------
"""
사용법: python3 migrate_from_gsheet.py

기존 Google Sheets 데이터를 SQLite로 이관합니다.
detail1~5 필드를 적절한 개별 컬럼으로 변환합니다.
"""
import sys
import os

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, insert_asset, insert_history_batch, set_settings_batch, get_connection

# 기존 utils.py의 Google Sheets 로드 함수 사용
# (아직 utils.py가 변경되지 않았으므로 직접 가져옴)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json


# -----------------------------------------------------------------------------------------------------
# Google Sheets 설정 (기존 utils.py에서 복사)
# -----------------------------------------------------------------------------------------------------
SPREADSHEET_NAME = "MyAssetData"
KEY_FILE = "service_account.json"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

HEADER_MAP = {
    "acqDate": "acquisitionDate",
    "acquisitionDate": "acquisitionDate",
    "aquisitionDate": "acquisitionDate",
    "AcquisitionDate": "acquisitionDate",
    "취득일": "acquisitionDate",
    "날짜": "acquisitionDate",
    "acqPrice": "acquisitionPrice",
    "acquisitionPrice": "acquisitionPrice",
    "aquisitionPrice": "acquisitionPrice",
    "취득가": "acquisitionPrice",
    "disposalDate": "disposalDate",
    "dispDate": "disposalDate",
    "매각일": "disposalDate",
    "disposalPrice": "disposalPrice",
    "dispPrice": "disposalPrice",
    "매각가": "disposalPrice",
    "currentValue": "currentValue",
    "현재가": "currentValue",
    "quantity": "quantity",
    "수량": "quantity",
    "detail1": "detail1",
    "detail2": "detail2",
    "detail3": "detail3",
    "detail4": "detail4",
    "detail5": "detail5",
    "history": "history"
}

SETTINGS_MAP = {
    "CurrentAge": "current_age",
    "RetirementAge": "retirement_age"
}


# -----------------------------------------------------------------------------------------------------
# 헬퍼 함수
# -----------------------------------------------------------------------------------------------------
def safe_float(val):
    try:
        if val is None or str(val).strip() == "":
            return 0.0
        return float(str(val).replace(",", ""))
    except:
        return 0.0


def safe_int(val):
    try:
        if val is None or str(val).strip() == "":
            return 0
        return int(float(str(val).replace(",", "")))
    except:
        return 0


# -----------------------------------------------------------------------------------------------------
# detail 필드 변환 함수
# -----------------------------------------------------------------------------------------------------
def convert_real_estate(raw_asset: dict) -> dict:
    """부동산: detail1~5 → 개별 필드"""
    return {
        'is_owned': 1 if 'OWNED' in str(raw_asset.get('detail1', '')).upper() else 0,
        'has_tenant': 1 if 'HAS_TENANT' in str(raw_asset.get('detail2', '')).upper() else 0,
        'tenant_deposit': safe_float(raw_asset.get('detail3')),
        'address': str(raw_asset.get('detail4', '')),
        'loan_amount': safe_float(raw_asset.get('detail5'))
    }


def convert_stock(raw_asset: dict) -> dict:
    """주식: detail1~5 → 개별 필드"""
    d5 = str(raw_asset.get('detail5', ''))
    name = str(raw_asset.get('name', ''))
    
    # 잔고보정 감지: detail5 값 또는 이름에 '보정' 포함
    is_balance_adj = (d5 == 'BALANCE_ADJUSTMENT' or '보정' in name)
    
    result = {
        'account_name': str(raw_asset.get('detail1', '기타')),
        'currency': str(raw_asset.get('detail2', 'KRW')),
        'is_balance_adjustment': 1 if is_balance_adj else 0,
        'is_pension_like': 0,
        'pension_start_year': None,
        'pension_monthly': None
    }
    
    # 연금성 자산 처리 (잔고보정이 아닌 경우만)
    if not is_balance_adj:
        if d5 == 'Y':
            result['is_pension_like'] = 1
        elif d5.startswith('PENSION'):
            result['is_pension_like'] = 1
            try:
                parts = d5.split('_')
                if len(parts) >= 3:
                    result['pension_start_year'] = int(parts[1])
                    result['pension_monthly'] = float(parts[2])
            except:
                pass
    
    return result


def convert_pension(raw_asset: dict) -> dict:
    """연금: detail1~5 → 개별 필드"""
    return {
        'pension_type': str(raw_asset.get('detail1', 'PERSONAL')),
        'expected_start_year': safe_int(raw_asset.get('detail2')),
        'expected_monthly_payout': safe_float(raw_asset.get('detail3')),
        'expected_end_year': safe_int(raw_asset.get('detail4')),
        'annual_growth_rate': safe_float(raw_asset.get('detail5', 0))
    }


def convert_savings(raw_asset: dict) -> dict:
    """예적금: detail5의 연금성 여부"""
    d5 = str(raw_asset.get('detail5', ''))
    
    result = {
        'is_pension_like': 0,
        'pension_start_year': None,
        'pension_monthly': None
    }
    
    if d5 == 'Y':
        result['is_pension_like'] = 1
    elif d5.startswith('PENSION'):
        result['is_pension_like'] = 1
        try:
            parts = d5.split('_')
            if len(parts) >= 3:
                result['pension_start_year'] = int(parts[1])
                result['pension_monthly'] = float(parts[2])
        except:
            pass
    
    return result


def convert_asset(raw_asset: dict) -> dict:
    """원본 자산 데이터를 새 스키마 형식으로 변환"""
    a_type = raw_asset.get('type', 'ETC')
    
    # 공통 필드
    asset = {
        'id': raw_asset.get('id'),
        'type': a_type,
        'name': raw_asset.get('name', ''),
        'current_value': safe_float(raw_asset.get('currentValue')),
        'acquisition_date': raw_asset.get('acquisitionDate'),
        'acquisition_price': safe_float(raw_asset.get('acquisitionPrice')),
        'disposal_date': raw_asset.get('disposalDate') or None,
        'disposal_price': safe_float(raw_asset.get('disposalPrice')),
        'quantity': safe_float(raw_asset.get('quantity'))
    }
    
    # 유형별 상세 필드 추가
    if a_type == 'REAL_ESTATE':
        asset.update(convert_real_estate(raw_asset))
    elif a_type == 'STOCK':
        asset.update(convert_stock(raw_asset))
    elif a_type == 'PENSION':
        asset.update(convert_pension(raw_asset))
    elif a_type == 'SAVINGS':
        asset.update(convert_savings(raw_asset))
    
    return asset


def convert_history(raw_history) -> list:
    """이력 데이터 변환"""
    if isinstance(raw_history, str):
        try:
            raw_history = json.loads(raw_history)
        except:
            return []
    
    if not isinstance(raw_history, list):
        return []
    
    result = []
    for h in raw_history:
        item = {
            'date': h.get('date'),
            'value': safe_float(h.get('value')) if 'value' in h else None,
            'price': safe_float(h.get('price')) if 'price' in h else None,
            'quantity': safe_float(h.get('quantity')) if 'quantity' in h else None
        }
        result.append(item)
    
    return result


# -----------------------------------------------------------------------------------------------------
# 메인 마이그레이션 로직
# -----------------------------------------------------------------------------------------------------
def load_from_gsheet():
    """Google Sheets에서 데이터 로드"""
    if not os.path.exists(KEY_FILE):
        print(f"❌ 인증 파일 {KEY_FILE}이 없습니다.")
        return [], {}
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, SCOPE)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        print(f"❌ 구글 시트 '{SPREADSHEET_NAME}'를 찾을 수 없습니다.")
        return [], {}
    
    ws = sh.sheet1
    all_values = ws.get_all_values()
    
    if not all_values or len(all_values) < 8:
        print("❌ 시트에 데이터가 없습니다.")
        return [], {}
    
    # 헤더 행 찾기
    header_index = -1
    header_row = []
    for i, row in enumerate(all_values):
        row_lower = [str(c).lower().strip() for c in row]
        if "id" in row_lower and "type" in row_lower:
            header_index = i
            header_row = row
            break
    
    if header_index == -1:
        if len(all_values) > 7:
            header_index = 7
            header_row = all_values[7]
        else:
            return [], {}
    
    # 설정 로드
    settings = {"current_age": 40, "retirement_age": 60}
    for i in range(header_index):
        row = all_values[i]
        if len(row) >= 3 and row[0] == "CONFIG":
            sheet_key = row[1]
            val = row[2]
            if sheet_key in SETTINGS_MAP:
                try:
                    settings[SETTINGS_MAP[sheet_key]] = int(val)
                except:
                    pass
    
    # 데이터 파싱
    data_rows = all_values[header_index + 1:]
    assets = []
    
    for row in data_rows:
        if not any(row):
            continue
        
        asset = {}
        for idx, col_name in enumerate(header_row):
            if idx < len(row):
                raw_val = row[idx]
                col_key = col_name.strip()
                app_key = HEADER_MAP.get(col_key, col_key)
                
                if app_key == col_key:
                    for k, v in HEADER_MAP.items():
                        if k.lower() == col_key.lower():
                            app_key = v
                            break
                
                val = raw_val
                if app_key == "history":
                    try:
                        if val.startswith("[") or val.startswith("{"):
                            val = json.loads(val)
                        else:
                            val = []
                    except:
                        val = []
                
                asset[app_key] = val
        
        assets.append(asset)
    
    return assets, settings


def migrate():
    """마이그레이션 실행"""
    print("=" * 60)
    print("📦 Google Sheets → SQLite 마이그레이션 시작")
    print("=" * 60)
    
    # 1. DB 초기화
    print("\n[1/4] 데이터베이스 초기화...")
    init_db()
    
    # 2. Google Sheets에서 데이터 로드
    print("\n[2/4] Google Sheets에서 데이터 로드...")
    raw_assets, settings = load_from_gsheet()
    
    if not raw_assets:
        print("❌ 로드할 데이터가 없습니다.")
        return False
    
    print(f"   → {len(raw_assets)}개 자산 발견")
    
    # 3. 데이터 변환 및 저장
    print("\n[3/4] 데이터 변환 및 저장...")
    
    success_count = 0
    for raw in raw_assets:
        try:
            # 변환
            asset = convert_asset(raw)
            history = convert_history(raw.get('history', []))
            
            # 저장
            insert_asset(asset)
            if history:
                insert_history_batch(asset['id'], history)
            
            print(f"   ✅ {asset['type']}: {asset['name']}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ 실패: {raw.get('name', 'Unknown')} - {e}")
    
    # 4. 설정 저장
    print("\n[4/4] 설정 저장...")
    set_settings_batch(settings)
    print(f"   → current_age: {settings.get('current_age')}")
    print(f"   → retirement_age: {settings.get('retirement_age')}")
    
    # 완료
    print("\n" + "=" * 60)
    print(f"✅ 마이그레이션 완료: {success_count}/{len(raw_assets)}개 자산")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    migrate()
