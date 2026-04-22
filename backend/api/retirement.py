import json
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db

router = APIRouter()

_KEY = "retirement_plan"


@router.get("/retirement")
async def get_retirement(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT value FROM settings WHERE key = :k"), {"k": _KEY})
    row = result.fetchone()
    if not row:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}


@router.put("/retirement")
async def save_retirement(data: dict, db: AsyncSession = Depends(get_db)):
    serialized = json.dumps(data, ensure_ascii=False)
    await db.execute(
        text("INSERT INTO settings (key, value) VALUES (:k, :v) "
             "ON CONFLICT(key) DO UPDATE SET value = :v"),
        {"k": _KEY, "v": serialized},
    )
    await db.commit()
    return {"message": "저장되었습니다."}
