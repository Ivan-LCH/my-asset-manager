# -----------------------------------------------------------------------------------------------------
# Stock Updater - yfinance 기반 주가/환율 자동 업데이트
# -----------------------------------------------------------------------------------------------------
import yfinance as yf
from datetime import datetime, timedelta
import time
from database import get_connection, insert_history_batch, update_asset

# -----------------------------------------------------------------------------------------------------
# 환율 캐시 (한 번 실행 동안 재사용)
# -----------------------------------------------------------------------------------------------------
EXCHANGE_RATES = {}

def get_exchange_rate(currency='USD') -> float:
    """실시간 환율 조회 (KRW는 1.0)"""
    if currency == 'KRW':
        return 1.0
    
    if currency in EXCHANGE_RATES:
        return EXCHANGE_RATES[currency]
    
    try:
        # Yahoo Finance 환율 심볼 (예: USDKRW=X)
        ticker = f"{currency}KRW=X"
        dat    = yf.Ticker(ticker)
        
        # fast_info가 불안정할 경우 history 사용
        rate = dat.fast_info.get('last_price')
        if not rate:
            hist = dat.history(period="1d")
            if not hist.empty:
                rate = hist['Close'].iloc[-1]
            else:
                rate = 1300.0  # Fallback
        
        EXCHANGE_RATES[currency] = float(rate)
        return float(rate)
    except Exception as e:
        print(f"⚠️ 환율 조회 실패 ({currency}): {e}")
        return 1300.0 if currency == 'USD' else 1.0


# -----------------------------------------------------------------------------------------------------
# 주가 업데이트 로직
# -----------------------------------------------------------------------------------------------------
def update_all_stocks():
    """DB의 모든 주식 자산에 대해 시세 업데이트 (Safe Update)"""
    print("🚀 주식 시세 업데이트 시작...")
    
    with get_connection() as conn:
        # 1. Ticker가 있는 주식 자산 조회
        sql = """
            SELECT a.id, a.name, a.quantity, s.ticker, s.currency, a.current_value
            FROM assets a
            JOIN stock_details s ON a.id = s.asset_id
            WHERE a.type = 'STOCK' AND s.ticker IS NOT NULL AND s.ticker != ''
        """
        assets = [dict(row) for row in conn.execute(sql).fetchall()]
    
    if not assets:
        print("ℹ️ 업데이트할 종목(Ticker 설정됨)이 없습니다.")
        return 0

    # 2. Ticker별로 그룹화 (API 호출 최소화)
    ticker_map = {}  # ticker -> list of assets
    for a in assets:
        t = a['ticker'].upper().strip()
        if t not in ticker_map:
            ticker_map[t] = []
        ticker_map[t].append(a)
    
    print(f"📋 총 {len(assets)}개 자산, {len(ticker_map)}개 종목(Ticker) 식별됨.")
    
    updated_count = 0
    today         = datetime.now()
    
    # 3. 종목별 처리
    for ticker, asset_list in ticker_map.items():
        try:
            print(f"⏳ 처리 중: {ticker}")
            
            # (1) Backfill 필요 기간 산출
            # 이 종목(Ticker)을 가진 모든 자산들 중, 가장 데이터가 오래된(업데이트가 필요한) 날짜를 찾음
            start_date_candidates = []
            for asset in asset_list:
                from database import get_last_history_date
                last_db_date = get_last_history_date(asset['id'])
                
                if not last_db_date:
                    # 기록이 아예 없으면 30일 전부터
                    start_date_candidates.append(today - timedelta(days=30))
                else:
                    # 기록이 있으면 [마지막 날짜] 부터 다시 조회 (Overlap Update)
                    # 그래야 마지막 날짜의 단가(장중/미완성)를 최신으로 보정할 수 있음
                    d = datetime.strptime(last_db_date, "%Y-%m-%d")
                    start_date_candidates.append(d)
            
            # 가장 과거의 날짜 채택
            # 최소 시작일이 오늘보다 미래라면, 데이터가 이미 최신인 상태지만
            # 장중 업데이트를 고려해 오늘 데이터는 다시 가져오는 것이 좋음
            fetch_start = min(start_date_candidates)
            print(f"   📥 데이터 확인 기간: {fetch_start.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}")

            # (2) 데이터 다운로드
            yf_ticker = yf.Ticker(ticker)
            
            # 현재가 (Current Price) - 항상 가져옴
            current_price = 0
            try:
                current_price = yf_ticker.fast_info.get('last_price')
            except: pass
            
            # 히스토리 데이터 다운로드 (Start ~ Today+1)
            hist_data = yf_ticker.history(start=fetch_start, end=today + timedelta(days=1), auto_adjust=True)
                
            # 만약 current_price를 못 구했으면 hist 데이터에서 조회
            if (current_price == 0 or current_price is None):
                if not hist_data.empty:
                     current_price = hist_data['Close'].iloc[-1]
                else:
                    try:
                        temp_hist = yf_ticker.history(period="5d")
                        if not temp_hist.empty:
                            current_price = temp_hist['Close'].iloc[-1]
                    except: pass

            if not current_price:
                print(f"   ❌ 가격 정보 없음: {ticker}")
                continue

            # 통화 및 환율
            currency = asset_list[0]['currency'] 
            rate     = get_exchange_rate(currency)
            
            # (3) 처리 및 저장 (Safe Logic)
            for asset in asset_list:
                # DB의 "마지막 수량"을 가져옴 (Forward Fill용)
                last_qty = float(asset['quantity']) 
                # 하지만, 더 정확하게는 히스토리상 '마지막 날짜의 수량'을 가져와야 함.
                # 왜냐하면 asset['quantity']는 현재 수량인데, 이게 과거 데이터에는 적용되면 안될 수도 있지만
                # 여기서는 'Gap Filling'이므로 가장 최신 상태를 이어받는 것이 맞음.
                
                # 안전 로직: 기존 히스토리를 절대 삭제하지 않음.
                # 날짜별로 DB에 존재하는지 확인 후, 존재하면 Price Update, 없으면 Insert
                
                if not hist_data.empty:
                    # 일괄 처리를 위해 DB 조회를 최소화하고 싶지만, 
                    # 안전을 위해 날짜별로 INSERT or UPDATE 수행
                    
                    for ts, row in hist_data.iterrows():
                        r_date = ts.to_pydatetime().replace(tzinfo=None)
                        r_date_str = r_date.strftime("%Y-%m-%d")
                        
                        h_price = row['Close']
                        
                        # 해당 날짜의 기록이 있는지 확인
                        with get_connection() as conn:
                            exist_row = conn.execute(
                                "SELECT id, quantity FROM asset_history WHERE asset_id = ? AND date = ?", 
                                (asset['id'], r_date_str)
                            ).fetchone()
                            
                            if exist_row:
                                # [Overlap Update]
                                # 이미 존재하면: 수량은 절대 건드리지 않고, 가격/가치만 업데이트
                                exist_qty = float(exist_row['quantity']) if exist_row['quantity'] is not None else 0
                                new_val   = exist_qty * h_price * rate
                                
                                conn.execute(
                                    "UPDATE asset_history SET price = ?, value = ? WHERE id = ?",
                                    (h_price, new_val, exist_row['id'])
                                )
                                # 마지막 날짜였다면, 다음 날(Gap) 채울때 이 수량을 기준으로 함
                                last_qty = exist_qty
                                
                            else:
                                # [Gap Filling]
                                # 존재하지 않으면: 신규 추가 (수량은 직전 수량 계승)
                                # 단, 직전 수량(last_qty) 사용
                                new_val = last_qty * h_price * rate
                                
                                conn.execute(
                                    "INSERT INTO asset_history (asset_id, date, price, quantity, value) VALUES (?, ?, ?, ?, ?)",
                                    (asset['id'], r_date_str, h_price, last_qty, new_val)
                                )
                    
                    print(f"      ✅ 시세 동기화 완료 ({asset['name']})")


                # 3-1. 자산 현재가 업데이트 (Asset Table)
                # 현재 가치는 항상 [해당 자산의 DB상 수량] * [최신 가격]
                # (주의: asset['quantity']는 사용자가 수정한 것일 수 있으므로 그대로 사용)
                final_qty = float(asset['quantity'])
                new_value = final_qty * current_price * rate
                
                # 상세 정보가 날라가지 않도록 값만 업데이트하는 함수 사용
                from database import update_asset_value_only
                update_asset_value_only(asset['id'], new_value, final_qty)
                
                updated_count += 1
                
        except Exception as e:
            print(f"   ⚠️ 오류 발생 ({ticker}): {e}")
            import traceback
            traceback.print_exc()
            
    print(f"✅ 총 {updated_count}개 자산 업데이트 완료.")
    return updated_count


# -----------------------------------------------------------------------------------------------------
# 실행
# -----------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    update_all_stocks()
