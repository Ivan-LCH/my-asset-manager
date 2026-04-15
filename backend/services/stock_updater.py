"""
yfinance 기반 주가/환율 자동 업데이트 서비스.
Ticker가 설정된 주식 자산의 이력을 Backfill하고 current_value를 동기화.
"""
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Asset, AssetHistory, StockDetail

# 환율 캐시 (실행 당 1회만 조회)
_RATE_CACHE: dict[str, float] = {}


def normalize_ticker(ticker: str) -> str:
    """
    yfinance용 ticker 정규화.
    - 앞뒤 공백 제거, 대문자 변환
    - 한국 거래소 suffix: .KR / .kr / .ks → .KS
    """
    t = ticker.strip().upper()
    # .KR 은 yfinance에서 인식 안 됨 → .KS 로 교정
    if t.endswith(".KR"):
        t = t[:-3] + ".KS"
    return t


def get_exchange_rate(currency: str) -> float:
    """통화 → KRW 환율 조회"""
    if currency == "KRW":
        return 1.0
    if currency in _RATE_CACHE:
        return _RATE_CACHE[currency]
    try:
        ticker = f"{currency}KRW=X"
        dat    = yf.Ticker(ticker)
        rate   = dat.fast_info.get("last_price")
        if not rate:
            hist = dat.history(period="1d")
            if not hist.empty:
                rate = hist["Close"].iloc[-1]
        if rate:
            _RATE_CACHE[currency] = float(rate)
            return float(rate)
    except Exception as e:
        print(f"⚠️ 환율 조회 실패 ({currency}): {e}")
    # Fallback
    fallback = {"USD": 1450.0, "JPY": 9.5}
    return fallback.get(currency, 1.0)


async def update_all_stocks(db: AsyncSession) -> dict:
    """
    Ticker가 설정된 모든 주식 자산의 시세 업데이트.
    반환: {"updated_count": int, "failed_tickers": list}
    """
    _RATE_CACHE.clear()  # 실행마다 환율 캐시 초기화

    # 1. Ticker 있는 주식 자산 조회
    q = (
        select(Asset, StockDetail)
        .join(StockDetail, Asset.id == StockDetail.asset_id)
        .where(Asset.type == "STOCK")
        .where(StockDetail.ticker.isnot(None))
        .where(StockDetail.ticker != "")
    )
    result = await db.execute(q)
    rows = result.all()

    if not rows:
        print("ℹ️ 업데이트할 종목(Ticker 설정됨)이 없습니다.")
        return {"updated_count": 0, "failed_tickers": []}

    # 2. Ticker별 그룹화 (동일 Ticker = API 1회 호출)
    ticker_map: dict[str, list[tuple]] = {}
    for asset, detail in rows:
        t = normalize_ticker(detail.ticker)
        if t not in ticker_map:
            ticker_map[t] = []
        ticker_map[t].append((asset, detail))

    print(f"📋 총 {len(rows)}개 자산, {len(ticker_map)}개 종목 처리 시작")

    updated_count  = 0
    failed_tickers = []
    today_str      = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str   = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    for ticker, asset_list in ticker_map.items():
        try:
            # 3. 이 Ticker를 가진 자산들 중 가장 오래된 마지막 이력 날짜 산출
            start_candidates = []
            for asset, _ in asset_list:
                last_q   = select(AssetHistory).where(
                    AssetHistory.asset_id == asset.id
                ).order_by(AssetHistory.date.desc()).limit(1)
                last_res = await db.execute(last_q)
                last     = last_res.scalar_one_or_none()
                if last:
                    start_candidates.append(datetime.strptime(last.date, "%Y-%m-%d"))
                else:
                    start_candidates.append(datetime.now() - timedelta(days=30))

            start_date = min(start_candidates)
            print(f"⏳ {ticker}: {start_date.strftime('%Y-%m-%d')} ~ {today_str}")

            # 4. yfinance 시세 조회 (end는 exclusive이므로 내일 날짜 사용 → 오늘 종가 포함)
            yf_ticker = yf.Ticker(ticker)
            hist_df   = yf_ticker.history(start=start_date.strftime("%Y-%m-%d"), end=tomorrow_str)

            if hist_df.empty:
                print(f"⚠️ {ticker}: 데이터 없음")
                continue

            # 5. 각 자산에 이력 Upsert
            for asset, detail in asset_list:
                currency = detail.currency or "KRW"
                rate     = get_exchange_rate(currency)

                for date_idx, row in hist_df.iterrows():
                    date_str = date_idx.strftime("%Y-%m-%d")
                    price    = float(row["Close"])
                    qty      = asset.quantity or 0
                    value    = price * qty * rate

                    # Upsert: 해당 날짜 존재 시 덮어쓰기
                    existing_q = select(AssetHistory).where(
                        AssetHistory.asset_id == asset.id,
                        AssetHistory.date     == date_str,
                    )
                    existing_res = await db.execute(existing_q)
                    existing     = existing_res.scalar_one_or_none()

                    if existing:
                        existing.price    = price
                        existing.quantity = qty
                        existing.value    = value
                    else:
                        db.add(AssetHistory(
                            asset_id = asset.id,
                            date     = date_str,
                            price    = price,
                            quantity = qty,
                            value    = value,
                        ))

                # 6. assets 테이블 current_value 동기화 (최신 종가 기준)
                if not hist_df.empty:
                    latest_price = float(hist_df["Close"].iloc[-1])
                    asset.current_value = latest_price * (asset.quantity or 0) * rate
                    asset.updated_at    = datetime.now().isoformat()

                updated_count += 1

            await db.flush()

        except Exception as e:
            print(f"❌ {ticker} 업데이트 실패: {e}")
            failed_tickers.append(ticker)

    print(f"✅ 업데이트 완료: {updated_count}개 자산, 실패: {failed_tickers}")
    return {"updated_count": updated_count, "failed_tickers": failed_tickers}
