"""
yfinance 기반 주가/환율 자동 업데이트 서비스.
Ticker가 설정된 주식 자산의 이력을 Backfill하고 current_value를 동기화.
"""
from datetime import datetime, timedelta
from typing import Optional
import urllib.request
import json

import yfinance as yf
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Asset, AssetHistory, StockDetail

# 환율 캐시 (실행 당 1회만 조회)
_RATE_CACHE: dict[str, float] = {}


def get_naver_realtime_price(ticker: str) -> float | None:
    """
    네이버 금융 API로 국내 주식 실시간 현재가 조회.
    ticker: '005930.KS' 형식 → 종목코드 '005930' 추출
    """
    try:
        code = ticker.split(".")[0]
        url  = f"https://m.stock.naver.com/api/stock/{code}/basic"
        req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data  = json.loads(r.read())
            price = data.get("closePrice", "")
            if price:
                return float(str(price).replace(",", ""))
    except Exception as e:
        print(f"⚠️ 네이버 실시간가 조회 실패 ({ticker}): {e}")
    return None


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


def _fetch_rate_frankfurter(currency: str) -> float | None:
    """frankfurter.app에서 환율 조회 (무료, API 키 불필요)"""
    try:
        url = f"https://api.frankfurter.app/latest?from={currency}&to=KRW"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            rate = data.get("rates", {}).get("KRW")
            if rate:
                return float(rate)
    except Exception as e:
        print(f"⚠️ frankfurter 환율 조회 실패 ({currency}): {e}")
    return None


def _fetch_rate_yfinance(currency: str) -> float | None:
    """yfinance에서 환율 조회 (fallback)"""
    try:
        ticker = f"{currency}KRW=X"
        dat    = yf.Ticker(ticker)
        rate   = dat.fast_info.get("last_price")
        if not rate:
            hist = dat.history(period="1d")
            if not hist.empty:
                rate = float(hist["Close"].iloc[-1])
        if rate:
            return float(rate)
    except Exception as e:
        print(f"⚠️ yfinance 환율 조회 실패 ({currency}): {e}")
    return None


def get_exchange_rate(currency: str) -> float:
    """통화 → KRW 환율 조회 (frankfurter 우선, yfinance fallback)"""
    if currency == "KRW":
        return 1.0
    if currency in _RATE_CACHE:
        return _RATE_CACHE[currency]

    rate = _fetch_rate_frankfurter(currency) or _fetch_rate_yfinance(currency)
    if rate:
        _RATE_CACHE[currency] = rate
        print(f"💱 환율 조회: 1 {currency} = {rate:,.2f} KRW")
        return rate

    fallback = {"USD": 1450.0, "JPY": 9.5}
    rate = fallback.get(currency, 1.0)
    _RATE_CACHE[currency] = rate
    return rate


async def save_exchange_rates_to_settings(db: AsyncSession):
    """조회된 환율을 settings 테이블에 캐시 저장"""
    from sqlalchemy import text as _text
    for currency, rate in _RATE_CACHE.items():
        if currency == "KRW":
            continue
        key = f"exchange_rate_{currency}"
        await db.execute(
            _text("INSERT INTO settings (key, value) VALUES (:k, :v) "
                  "ON CONFLICT(key) DO UPDATE SET value = :v"),
            {"k": key, "v": str(rate)},
        )


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

            # 5-a. 장중 실시간 현재가 조회
            # hist_df에 오늘 날짜가 없으면 장이 아직 열려 있는 것 → 실시간 현재가 시도
            today_in_hist = any(
                idx.strftime("%Y-%m-%d") == today_str for idx in hist_df.index
            )
            realtime_price: float | None = None
            if not today_in_hist:
                # 국내 주식(.KS/.KQ): 네이버 금융 API 우선 사용 (yfinance fast_info는 KS 미지원)
                if ticker.endswith(".KS") or ticker.endswith(".KQ"):
                    rt = get_naver_realtime_price(ticker)
                    if rt and rt > 0:
                        realtime_price = rt
                        print(f"📡 {ticker}: 네이버 현재가 {realtime_price:,.0f} (장중)")
                else:
                    try:
                        fi = yf_ticker.fast_info
                        rt = getattr(fi, "last_price", None)
                        if rt and float(rt) > 0:
                            realtime_price = float(rt)
                            print(f"📡 {ticker}: 장중 현재가 {realtime_price:,.0f} (종가 확정 전)")
                    except Exception as e:
                        print(f"⚠️ {ticker}: 실시간 현재가 조회 실패 ({e})")

            # 5-b. 각 자산에 이력 Upsert
            for asset, detail in asset_list:
                currency = detail.currency or "KRW"
                rate     = get_exchange_rate(currency)
                qty      = asset.quantity or 0

                # (a) 확정 종가 이력 upsert (hist_df)
                for date_idx, row in hist_df.iterrows():
                    date_str = date_idx.strftime("%Y-%m-%d")
                    price    = float(row["Close"])
                    value    = price * qty * rate

                    existing_q   = select(AssetHistory).where(
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

                # (b) 장중: 오늘 날짜 실시간 현재가 upsert (장 마감 후 재업데이트 시 종가로 덮어써짐)
                if realtime_price is not None:
                    rt_value     = realtime_price * qty * rate
                    existing_q   = select(AssetHistory).where(
                        AssetHistory.asset_id == asset.id,
                        AssetHistory.date     == today_str,
                    )
                    existing_res = await db.execute(existing_q)
                    existing     = existing_res.scalar_one_or_none()

                    if existing:
                        existing.price    = realtime_price
                        existing.quantity = qty
                        existing.value    = rt_value
                    else:
                        db.add(AssetHistory(
                            asset_id = asset.id,
                            date     = today_str,
                            price    = realtime_price,
                            quantity = qty,
                            value    = rt_value,
                        ))

                # 6. current_value 동기화: 실시간가 우선, 없으면 hist_df 최신 종가
                final_price = realtime_price if realtime_price else (
                    float(hist_df["Close"].iloc[-1]) if not hist_df.empty else None
                )
                if final_price:
                    asset.current_value = final_price * qty * rate
                    asset.updated_at    = datetime.now().isoformat()

                updated_count += 1

            await db.flush()

        except Exception as e:
            print(f"❌ {ticker} 업데이트 실패: {e}")
            failed_tickers.append(ticker)

    await save_exchange_rates_to_settings(db)
    print(f"✅ 업데이트 완료: {updated_count}개 자산, 실패: {failed_tickers}")
    return {"updated_count": updated_count, "failed_tickers": failed_tickers}
