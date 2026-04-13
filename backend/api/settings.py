from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.crud import get_settings, save_settings

router = APIRouter()


@router.get("/settings")
async def read_settings(db: AsyncSession = Depends(get_db)):
    """설정 조회"""
    return await get_settings(db)


@router.put("/settings")
async def write_settings(data: dict, db: AsyncSession = Depends(get_db)):
    """설정 저장"""
    await save_settings(db, data)
    return {"message": "설정이 저장되었습니다."}
