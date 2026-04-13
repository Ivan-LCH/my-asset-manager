#!/bin/bash
echo "========================================"
echo "  My Asset Manager - Starting Server"
echo "========================================"

PID_FILE="/app/server.pid"

# 0. 기존 서버 종료
echo "[0/3] Stopping existing server processes..."
if [ -f "$PID_FILE" ]; then
    kill -9 $(cat "$PID_FILE") 2>/dev/null || true
    rm -f "$PID_FILE"
fi
pkill -9 -f "uvicorn backend.main" 2>/dev/null || true
sleep 1

# 1. Frontend 빌드
echo "[1/3] Building Frontend..."
cd /app/frontend
npm run build

# 2. 빌드 결과물 → /app/static 복사
echo "[2/3] Copying build output to /app/static/..."
cd /app
rm -rf /app/static
cp -r /app/frontend/dist /app/static

# 3. Backend 시작
echo "[3/3] Starting Backend Server..."
mkdir -p /app/logs
setsid nohup python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8090 \
    >> /app/logs/server.log 2>&1 &
echo $! > "$PID_FILE"

echo "========================================"
echo "  Deployment Complete!"
echo "  Server PID : $(cat $PID_FILE)"
echo "  URL        : http://localhost:8090"
echo "  Logs       : tail -f /app/logs/server.log"
echo "========================================"
