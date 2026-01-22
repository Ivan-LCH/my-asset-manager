# -----------------------------------------------------------------------------------------------------
# Utils - SQLite 기반 데이터 로드/저장
# -----------------------------------------------------------------------------------------------------
import json
from database import (
    get_all_assets, insert_asset, update_asset, delete_asset,
    insert_history_batch, delete_asset_history,
    get_settings, set_settings_batch, get_connection
)


# -----------------------------------------------------------------------------------------------------
# 헬퍼 함수: DB 컬럼명 → app.py 필드명 변환
# -----------------------------------------------------------------------------------------------------
def _db_to_app(asset: dict) -> dict:
    """DB 스네이크 케이스 → app.py 카멜 케이스 변환"""
    mapping = {
        'current_value': 'currentValue',
        'acquisition_date': 'acquisitionDate',
        'acquisition_price': 'acquisitionPrice',
        'disposal_date': 'disposalDate',
        'disposal_price': 'disposalPrice',
        # real_estate
        'is_owned': 'isOwned',
        'has_tenant': 'hasTenant',
        'tenant_deposit': 'tenantDeposit',
        'loan_amount': 'loanAmount',
        # stock
        'account_name': 'accountName',
        'is_balance_adjustment': 'isBalanceAdjustment',
        'is_pension_like': 'isPensionLike',
        'pension_start_year': 'expectedStartYear',
        'pension_monthly': 'expectedMonthlyPayout',
        # pension
        'pension_type': 'pensionType',
        'expected_start_year': 'expectedStartYear',
        'expected_end_year': 'expectedEndYear',
        'expected_monthly_payout': 'expectedMonthlyPayout',
        'annual_growth_rate': 'annualGrowthRate',
    }
    
    result = {}
    for k, v in asset.items():
        new_key = mapping.get(k, k)
        # Boolean 변환 (SQLite에서 0/1로 저장됨)
        if k in ['is_owned', 'has_tenant', 'is_balance_adjustment', 'is_pension_like']:
            result[new_key] = bool(v) if v else False
        else:
            result[new_key] = v
    
    return result


def _app_to_db(asset: dict) -> dict:
    """app.py 카멜 케이스 → DB 스네이크 케이스 변환"""
    mapping = {
        'currentValue': 'current_value',
        'acquisitionDate': 'acquisition_date',
        'acquisitionPrice': 'acquisition_price',
        'disposalDate': 'disposal_date',
        'disposalPrice': 'disposal_price',
        # real_estate
        'isOwned': 'is_owned',
        'hasTenant': 'has_tenant',
        'tenantDeposit': 'tenant_deposit',
        'loanAmount': 'loan_amount',
        'address': 'address',
        # stock
        'accountName': 'account_name',
        'currency': 'currency',
        'isBalanceAdjustment': 'is_balance_adjustment',
        'isPensionLike': 'is_pension_like',
        # pension
        'pensionType': 'pension_type',
        'expectedStartYear': 'expected_start_year',
        'expectedEndYear': 'expected_end_year',
        'expectedMonthlyPayout': 'expected_monthly_payout',
        'annualGrowthRate': 'annual_growth_rate',
    }
    
    result = {}
    for k, v in asset.items():
        new_key = mapping.get(k, k)
        # Boolean → Integer 변환
        if k in ['isOwned', 'hasTenant', 'isBalanceAdjustment', 'isPensionLike']:
            result[new_key] = 1 if v else 0
        else:
            result[new_key] = v
    
    return result


# -----------------------------------------------------------------------------------------------------
# Load Data
# -----------------------------------------------------------------------------------------------------
def load_data():
    """SQLite에서 모든 자산과 설정 로드"""
    try:
        assets = get_all_assets()
        
        # DB 포맷 → app.py 포맷 변환
        converted_assets = []
        for asset in assets:
            converted = _db_to_app(asset)
            
            # detail5 호환성 (app.py에서 아직 참조하는 부분 대응)
            a_type = converted.get('type')
            if a_type == 'STOCK':
                if converted.get('isBalanceAdjustment'):
                    converted['detail5'] = 'BALANCE_ADJUSTMENT'
                elif converted.get('isPensionLike'):
                    converted['detail5'] = 'Y'
            
            converted_assets.append(converted)
        
        # 설정 로드
        settings_raw = get_settings()
        settings = {
            'current_age': int(settings_raw.get('current_age', 40)),
            'retirement_age': int(settings_raw.get('retirement_age', 60))
        }
        
        # 계좌별 총액 설정도 로드
        for k, v in settings_raw.items():
            if k.startswith('ACC_TOTAL_'):
                try:
                    settings[k] = float(v)
                except:
                    pass
        
        return converted_assets, settings
        
    except Exception as e:
        print(f"❌ 데이터 로드 오류: {e}")
        import traceback
        traceback.print_exc()
        return [], {}


# -----------------------------------------------------------------------------------------------------
# Save Data
# -----------------------------------------------------------------------------------------------------
def save_data(assets, settings):
    """모든 자산과 설정을 SQLite에 저장"""
    try:
        with get_connection() as conn:
            # 기존 자산 ID 목록
            existing_ids = set(row['id'] for row in conn.execute("SELECT id FROM assets").fetchall())
            incoming_ids = set(a.get('id') for a in assets if a.get('id'))
            
            # 삭제된 자산 처리
            deleted_ids = existing_ids - incoming_ids
            for asset_id in deleted_ids:
                conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        
        # 자산 저장/업데이트
        for asset in assets:
            converted = _app_to_db(asset)
            asset_id = converted.get('id')
            
            if not asset_id:
                continue
            
            # 이력 처리
            history = asset.get('history', [])
            if isinstance(history, str):
                try:
                    history = json.loads(history)
                except:
                    history = []
            
            # 기존 자산인지 확인
            with get_connection() as conn:
                exists = conn.execute("SELECT 1 FROM assets WHERE id = ?", (asset_id,)).fetchone()
            
            if exists:
                update_asset(converted)
            else:
                insert_asset(converted)
            
            # 이력 업데이트 (전체 교체)
            if history:
                delete_asset_history(asset_id)
                insert_history_batch(asset_id, history)
        
        # 설정 저장
        set_settings_batch(settings)
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터 저장 오류: {e}")
        import traceback
        traceback.print_exc()
        return False