"""배당금 이력 및 예상 배당 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import DividendHistory, StockDetail

router = APIRouter()


# ── 배당 이력 조회 ─────────────────────────────────────────
@router.get("/dividends/{asset_id}")
async def get_dividends(asset_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DividendHistory)
        .where(DividendHistory.asset_id == asset_id)
        .order_by(DividendHistory.date.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id":               r.id,
            "asset_id":         r.asset_id,
            "date":             r.date,
            "amount_krw":       r.amount_krw,
            "amount_original":  r.amount_original,
            "currency":         r.currency,
            "exchange_rate":    r.exchange_rate,
            "memo":             r.memo,
        }
        for r in rows
    ]


# ── 배당 이력 추가 ─────────────────────────────────────────
@router.post("/dividends/{asset_id}", status_code=201)
async def add_dividend(asset_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    if not data.get("date") or data.get("amount_krw") is None:
        raise HTTPException(status_code=422, detail="date, amount_krw는 필수입니다.")
    row = DividendHistory(
        asset_id        = asset_id,
        date            = data["date"],
        amount_krw      = float(data["amount_krw"]),
        amount_original = float(data.get("amount_original") or 0),
        currency        = data.get("currency", "KRW"),
        exchange_rate   = float(data.get("exchange_rate") or 1.0),
        memo            = data.get("memo", ""),
    )
    db.add(row)
    await db.flush()
    return {"id": row.id, "message": "배당금이 기록되었습니다."}


# ── 배당 이력 삭제 ─────────────────────────────────────────
@router.delete("/dividends/{asset_id}/{dividend_id}")
async def delete_dividend(asset_id: str, dividend_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DividendHistory).where(
            DividendHistory.id == dividend_id,
            DividendHistory.asset_id == asset_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="배당 이력을 찾을 수 없습니다.")
    await db.delete(row)
    return {"message": "삭제되었습니다."}


# ── 전체 배당 요약 (주식 페이지 KPI용) ────────────────────
@router.get("/dividends")
async def get_all_dividends_summary(db: AsyncSession = Depends(get_db)):
    """계좌/종목별 연간 예상 배당금 집계 (stock_details 기반)"""
    result = await db.execute(
        text("""
            SELECT
                a.id, a.name, a.current_value, a.quantity,
                sd.currency, sd.dividend_yield, sd.dividend_dps, sd.dividend_cycle,
                sd.account_name,
                COALESCE((
                    SELECT value FROM settings WHERE key = 'exchange_rate_' || sd.currency
                ), CASE sd.currency WHEN 'USD' THEN 1450 WHEN 'JPY' THEN 9.5 ELSE 1 END) AS exchange_rate
            FROM assets a
            JOIN stock_details sd ON a.id = sd.asset_id
            WHERE a.type = 'STOCK' AND a.disposal_date IS NULL
        """)
    )
    rows = result.fetchall()

    cycle_map = {"월": 12, "분기": 4, "반기": 2, "연간": 1}
    items = []
    for r in rows:
        rate = float(r.exchange_rate or 1)
        qty  = float(r.quantity or 0)
        val  = float(r.current_value or 0)
        dy   = float(r.dividend_yield or 0)
        dps  = float(r.dividend_dps or 0)
        cycle = r.dividend_cycle or "연간"
        times = cycle_map.get(cycle, 1)

        # DPS 우선, 없으면 수익률로 계산
        if dps > 0:
            annual_krw = dps * qty * times
        elif dy > 0:
            annual_krw = val * dy / 100
        else:
            annual_krw = 0

        items.append({
            "asset_id":      r.id,
            "name":          r.name,
            "account_name":  r.account_name,
            "currency":      r.currency,
            "exchange_rate": rate,
            "dividend_yield": dy,
            "dividend_dps":   dps,
            "dividend_cycle": cycle,
            "annual_krw":    annual_krw,
            "monthly_krw":   annual_krw / 12,
        })

    return {
        "items":          items,
        "total_annual":   sum(i["annual_krw"] for i in items),
        "total_monthly":  sum(i["monthly_krw"] for i in items),
    }


# ── 배당 설정 업데이트 (yield/dps/cycle) ──────────────────
@router.put("/dividends/{asset_id}/settings")
async def update_dividend_settings(asset_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StockDetail).where(StockDetail.asset_id == asset_id))
    detail = result.scalar_one_or_none()
    if not detail:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    if "dividend_yield" in data:
        detail.dividend_yield = float(data["dividend_yield"] or 0)
    if "dividend_dps" in data:
        detail.dividend_dps = float(data["dividend_dps"] or 0)
    if "dividend_cycle" in data:
        detail.dividend_cycle = data["dividend_cycle"]
    return {"message": "배당 설정이 저장되었습니다."}
