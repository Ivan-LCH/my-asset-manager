import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.core.config import DB_DIR, DB_URL


class Base(DeclarativeBase):
    pass


# 엔진 & 세션 팩토리
engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    """FastAPI 의존성 주입용 DB 세션"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """DB 초기화 (테이블 생성 + 신규 컬럼 migration)"""
    os.makedirs(DB_DIR, exist_ok=True)
    from backend.db import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 기존 stock_details에 배당 컬럼 추가 (이미 있으면 무시)
        for col, defval in [
            ("dividend_yield", "0"),
            ("dividend_dps",   "0"),
            ("dividend_cycle", "'연간'"),
        ]:
            try:
                await conn.execute(
                    __import__("sqlalchemy", fromlist=["text"]).text(
                        f"ALTER TABLE stock_details ADD COLUMN {col} REAL DEFAULT {defval}"
                    )
                )
            except Exception:
                pass  # 이미 존재하는 컬럼
    print(f"✅ DB initialized: {DB_URL}")
