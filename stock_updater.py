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
    """DB의 모든 주식 자산에 대해 시세 업데이트"""
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
                    # 기록이 있으면 그 다음 날부터
                    d = datetime.strptime(last_db_date, "%Y-%m-%d")
                    start_date_candidates.append(d + timedelta(days=1))
            
            # 가장 과거의 날짜 채택 (단, 오늘보다 미래면 패스)
            min_start_date = min(start_date_candidates)
            if min_start_date >= today:
                # 이미 최신임, 오늘 현재가만 가져오면 됨
                fetch_start = None
                print(f"   ℹ️ 최신 데이터 보유 중. 현재가만 갱신.")
            else:
                fetch_start = min_start_date
                print(f"   📥 과거 데이터 다운로드 시작 (from {fetch_start.strftime('%Y-%m-%d')})")

            # (2) 데이터 다운로드
            yf_ticker = yf.Ticker(ticker)
            
            # 현재가용
            current_price = 0
            try:
                current_price = yf_ticker.fast_info.get('last_price')
            except: pass
            
            # 과거 데이터 (Backfill)
            hist_data = None
            if fetch_start:
                # end는 exclusive이므로 오늘(포함 안됨)까지 하면 어제 데이터까지 옴
                # 하지만 장중이라면 오늘 데이터도 포함될 수 있음.
                hist_data = yf_ticker.history(start=fetch_start, end=today + timedelta(days=1))
                
            # 만약 current_price를 못 구했으면 hist 데이터나 최근 5일 데이터에서 조회
            if (current_price == 0 or current_price is None):
                if hist_data is not None and not hist_data.empty:
                     current_price = hist_data['Close'].iloc[-1]
                else:
                    # 백필이 필요없는 경우에도 현재가를 못 구했으면 최근 데이터를 조회
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
            
            # (3) 처리 및 저장
            for asset in asset_list:
                qty = float(asset['quantity'])
                if qty == 0: continue
                
                # ---------------------------------------------------------------------------------
                # [Smart Update] 수량이 변경되었는지 확인 (마지막 히스토리의 수량 vs 현재 수량)
                # 수량이 달라졌다면, 과거 히스토리가 현재 수량과 맞지 않게 되므로
                # 2023-01-01 부터의 데이터를 전부 다시 계산해서 덮어씀 (Backfill/Rewrite Logic)
                # ---------------------------------------------------------------------------------
                try:
                    need_rewrite = False
                    with get_connection() as conn:
                        lh = conn.execute("SELECT quantity FROM asset_history WHERE asset_id = ? ORDER BY date DESC LIMIT 1", (asset['id'],)).fetchone()
                        if lh:
                             last_hist_qty = float(lh[0])
                             if last_hist_qty != qty: need_rewrite = True
                    
                    if need_rewrite:
                        print(f"      🔄 수량 변경 감지 ({last_hist_qty} -> {qty}). 전체 히스토리 재계산 진행...")
                        
                        # 1. 기존 히스토리 삭제 (2023년 이후)
                        with get_connection() as conn:
                             conn.execute("DELETE FROM asset_history WHERE asset_id = ? AND date >= '2023-01-01'", (asset['id'],))
                        
                        # 2. yfinance 데이터 다시 가져오기 (월단위 전체)
                        full_hist = yf_ticker.history(start="2023-01-01", interval="1mo", auto_adjust=True)
                        if not full_hist.empty:
                             # 취득일 파싱
                             acq_date_str = asset.get('acquisition_date')
                             acq_date     = None
                             if acq_date_str:
                                 try: acq_date = datetime.strptime(acq_date_str[:10], "%Y-%m-%d")
                                 except: pass
                                 
                             bf_records = []
                             for ts, row in full_hist.iterrows():
                                 r_date     = ts.to_pydatetime().replace(tzinfo=None)
                                 r_date_str = r_date.strftime("%Y-%m-%d")
                                 
                                 # 수량 결정 (취득일 전이면 0)
                                 r_qty = qty
                                 if acq_date and r_date < acq_date: r_qty = 0
                                 
                                 # 가격 및 가치 계산
                                 r_price    = row['Close']
                                 r_val      = r_price * r_qty * rate
                                 
                                 bf_records.append({
                                     'date'    : r_date_str, 
                                     'price'   : r_price, 
                                     'quantity': r_qty, 
                                     'value'   : r_val
                                 })
                             
                             if bf_records:
                                 insert_history_batch(asset['id'], bf_records)
                                 print(f"      ✅ 히스토리 {len(bf_records)}건 재작성 완료.")

                except Exception as e:
                    print(f"      ⚠️ 재계산 실패: {e}")


                
                # 3-1. 현재가 업데이트
                # 현재 가치는 항상 최신 수량 * 최신 가격
                new_value = qty * current_price * rate
                
                # 상세 정보가 날라가지 않도록 값만 업데이트하는 함수 사용
                from database import update_asset_value_only
                update_asset_value_only(asset['id'], new_value, qty)
                
                # 3-2. 일반 Backfill 데이터 저장
                # (위의 재계산 로직이 실행되었다면, 여기서 추가되는 데이터는 중복 방지 로직에 의해 걸러짐)
                if hist_data is not None and not hist_data.empty:
                    batch_history = []
                    
                    # 자산의 마지막 기록 날짜 확인
                    last_db_date_str = get_last_history_date(asset['id'])
                    last_db_val      = datetime.strptime(last_db_date_str, "%Y-%m-%d") if last_db_date_str else (today - timedelta(days=365))
                    
                    for ts, row in hist_data.iterrows():
                        row_date = ts.to_pydatetime()
                        if row_date.tzinfo is not None:
                            row_date = row_date.replace(tzinfo=None)
                        
                        # DB에 있는 마지막 날짜보다 미래인 경우만 추가 (중복 방지)
                        if row_date > last_db_val:
                            h_price = row['Close']
                            
                            batch_history.append({
                                'date'    : row_date.strftime("%Y-%m-%d"),
                                'price'   : h_price,
                                'quantity': qty,
                                'value'   : h_price * qty * rate
                            })
                    
                    if batch_history:
                        insert_history_batch(asset['id'], batch_history)
                        print(f"      + {len(batch_history)}일치 이력 추가 ({asset['name']})")
                
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
