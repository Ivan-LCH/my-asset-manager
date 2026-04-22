from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.crud import (
    get_all_assets, get_asset_by_id,
    create_asset, update_asset, delete_asset,
    generate_chart_data,
)

router = APIRouter()


@router.get("/assets")
async def list_assets(
    type: Optional[str] = Query(None, description="자산 유형 필터 (REAL_ESTATE|STOCK|PENSION|SAVINGS|PHYSICAL|ETC)"),
    db: AsyncSession = Depends(get_db),
):
    """전체 자산 조회 (이력 + 상세 포함). type 쿼리파람으로 유형 필터."""
    return await get_all_assets(db, asset_type=type)


@router.get("/assets/chart")
async def asset_chart(
    type:     Optional[str] = Query(None),
    period:   str           = Query("all", description="all|10y|3y|1y|3m|1m"),
    group_by: str           = Query("type", description="type|name|account"),
    account:  Optional[str] = Query(None, description="계좌명 필터 (STOCK 전용)"),
    db: AsyncSession = Depends(get_db),
):
    """차트 집계 데이터. Forward Fill 후 group_by 기준으로 합산."""
    assets = await get_all_assets(db, asset_type=type)
    if account:
        assets = [
            a for a in assets
            if (a.get("detail") or {}).get("account_name") == account
        ]
    return generate_chart_data(assets, period=period, group_by=group_by)


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    """단일 자산 조회"""
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="자산을 찾을 수 없습니다.")
    return asset


@router.post("/assets", status_code=201)
async def add_asset(data: dict, db: AsyncSession = Depends(get_db)):
    """자산 추가"""
    if not data.get("type") or not data.get("name"):
        raise HTTPException(status_code=422, detail="type, name은 필수입니다.")
    asset_id = await create_asset(db, data)
    return {"id": asset_id, "message": "자산이 추가되었습니다."}


@router.put("/assets/{asset_id}")
async def modify_asset(asset_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """자산 수정"""
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="자산을 찾을 수 없습니다.")
    data["type"] = asset["type"]  # type 변경 불가
    await update_asset(db, asset_id, data)
    return {"message": "수정되었습니다."}


@router.delete("/assets/{asset_id}")
async def remove_asset(asset_id: str, db: AsyncSession = Depends(get_db)):
    """자산 삭제 (이력 + 상세 CASCADE)"""
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="자산을 찾을 수 없습니다.")
    await delete_asset(db, asset_id)
    return {"message": "삭제되었습니다."}
