#!/bin/bash
set -e

echo "[Entrypoint] Starting My Asset Manager container..."

# 1. 환경변수 로드
if [ -f /app/.env ]; then
    set -a
    source /app/.env
    set +a
fi

# 2. 필수 디렉토리 생성
mkdir -p /app/data /app/logs /app/static

# 3. SSH 데몬 시작 (컨테이너 유지 + SSH 접속용)
echo "[Entrypoint] Starting SSH Daemon..."
exec /usr/sbin/sshd -D
