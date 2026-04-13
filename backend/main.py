from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import CORS_ORIGINS
from backend.db.database import init_db
from backend.api.assets   import router as assets_router
from backend.api.history   import router as history_router
from backend.api.stocks    import router as stocks_router
from backend.api.settings  import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="My Asset Manager",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(assets_router,  prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(stocks_router,  prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "My Asset Manager"}


# 프론트엔드 정적 파일 서빙 — 반드시 마지막에 마운트
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
