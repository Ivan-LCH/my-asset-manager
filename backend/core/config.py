import os
from pathlib import Path

# 프로젝트 루트
BASE_DIR = Path(__file__).parent.parent.parent

# DB 설정
DB_DIR  = os.getenv("DB_DIR", str(BASE_DIR / "data"))
DB_NAME = os.getenv("DB_FILE_NAME", "assets.db")
DB_PATH = os.path.join(DB_DIR, DB_NAME)
DB_URL  = f"sqlite+aiosqlite:///{DB_PATH}"

# 서버 설정
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))

# CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:8090"
).split(",")
