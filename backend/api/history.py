from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.crud import get_history, add_history, update_history, delete_history
from backend.services.stock_updater import get_exchange_rate

router = APIRouter()


@router.get("/assets/{asset_id}/history")
async def list_history(asset_id: str, db: AsyncSession = Depends(get_db)):
    """자산 이력 조회 (날짜 오름차순)"""
    return await get_history(db, asset_id)


@router.post("/assets/{asset_id}/history", status_code=201)
async def create_history(asset_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """이력 추가"""
    if not data.get("date"):
        raise HTTPException(status_code=422, detail="date는 필수입니다.")
    await add_history(db, asset_id, data)
    return {"message": "이력이 추가되었습니다."}


@router.put("/assets/{asset_id}/history/{date}")
async def modify_history(
    asset_id: str,
    date:     str,
    data:     dict,
    db: AsyncSession = Depends(get_db),
):
    """
    이력 수정. value가 없으면 price * quantity * exchange_rate로 자동 계산.
    수량 변경 시 이후 날짜 이력에 수량 전파.
    """
    # 해당 자산의 통화 확인 (환율 적용)
    from sqlalchemy import select
    from backend.db.models import StockDetail
    currency_q = select(StockDetail.currency).where(StockDetail.asset_id == asset_id)
    result     = await db.execute(currency_q)
    currency   = result.scalar_one_or_none() or "KRW"
    rate       = get_exchange_rate(currency)

    propagated = await update_history(db, asset_id, date, data, exchange_rate=rate)
    return {"message": "수정되었습니다.", "propagated_count": propagated}


@router.delete("/assets/{asset_id}/history/{date}")
async def remove_history(asset_id: str, date: str, db: AsyncSession = Depends(get_db)):
    """특정 날짜 이력 삭제"""
    await delete_history(db, asset_id, date)
    return {"message": "삭제되었습니다."}
