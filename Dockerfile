FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# (중요) 소스 코드는 COPY 하지 않습니다.
# docker-compose에서 '볼륨'으로 연결해야 수정 사항이 바로 반영됩니다.

# Streamlit 기본 포트 노출
EXPOSE 8502

# 실행 명령
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]