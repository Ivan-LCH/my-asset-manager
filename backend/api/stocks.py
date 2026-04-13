from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.services.stock_updater import update_all_stocks

router = APIRouter()


@router.post("/stocks/update")
async def run_stock_update(db: AsyncSession = Depends(get_db)):
    """
    Ticker가 설정된 모든 주식 자산의 시세 업데이트.
    yfinance에서 마지막 이력 날짜부터 현재까지 Backfill.
    """
    result = await update_all_stocks(db)
    count  = result["updated_count"]
    failed = result["failed_tickers"]
    msg    = f"{count}개 자산 업데이트 완료"
    if failed:
        msg += f" (실패: {', '.join(failed)})"
    return {**result, "message": msg}
