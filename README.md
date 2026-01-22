# 💰 My Asset Manager (Personal Wealth Dashboard)

![Python](https://img.shields.io/badge/Python-3.9-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)

## 📖 프로젝트 개요 (Overview)
**My Asset Manager**는 흩어져 있는 개인의 자산을 통합하여 관리하는 **Python Streamlit 기반의 웹 대시보드**입니다.

기존 Google Sheets 기반에서 **SQLite 기반의 로컬 데이터베이스**로 전환되어 더욱 빠르고 안정적으로 데이터를 관리합니다. 부동산, 주식, 연금 등 다양한 자산군을 하나의 플랫폼에서 모니터링하며, 직관적인 UI로 현재 자산 상태와 포트폴리오 비중을 시각화합니다.

## 🚀 주요 기능 (Key Features)

### 1. 📊 통합 대시보드 (Dashboard)
- **자산 현황 요약:** 총 자산(Total Net Worth) 및 전월 대비 증감액 자동 계산
- **포트폴리오 비중:** 부동산, 주식, 연금 등 자산군별 구성 비율 시각화 (Pie Chart)
- **트렌드 분석:** 자산 변동 추이 그래프 제공

### 2. 🏠 부동산 관리 (Real Estate)
- **보유 부동산 목록:** 아파트, 오피스텔 등 매입가 및 현재 시세 관리
- **상세 정보:** 소유/임대 여부, 세입자 유무, 보증금, 대출금 관리

### 3. 📈 주식 포트폴리오 (Stocks)
- **투자 현황:** 국내(KRW) 및 해외(USD) 주식 종목별 평가 금액 확인
- **계좌별 관리:** 증권사 계좌별 자산 총액 및 잔고 보정 기능
- **수익률 분석:** 매입가 대비 현재 평가 손익 및 수익률 계산

### 4. 🛡️ 연금 및 노후 자산 (Pension)
- **연금 계좌 통합:** 국민연금, 개인연금, 퇴직연금 상세 관리
- **시뮬레이션:** 예상 수령 시작 년도, 월 수령액, 연간 증가율 설정

## 🛠️ 기술 스택 (Tech Stack)
- **Frontend/App:** Python 3.9, Streamlit
- **Database:** SQLite (Local)
- **Data Processing:** Pandas, NumPy
- **Utility Modules:** `database.py` (DB 스키마 및 CRUD), `utils.py` (데이터 처리)
- **Visualization:** Plotly, Altair
- **Deployment:** Docker, Docker Compose

## 📂 프로젝트 구조 (Project Structure)
```bash
my-asset-manager/
├── app.py                # 🚀 메인 애플리케이션 (UI 및 로직)
├── database.py           # 🗄️ SQLite 데이터베이스 관리 (스키마, CRUD)
├── stock_updater.py      # 📈 주식 시세 자동 업데이트 및 히스토리 관리
├── utils.py              # ⚙️ 데이터 로드/저장 유틸리티
├── data/                 # 🗃️ SQLite DB 파일 저장소 (assets.db)
├── maintenance_scripts/  # 🛠️ 유지보수 및 마이그레이션 스크립트 모음
├── requirements.txt      # 📦 의존성 목록
├── docker-compose.yml    # 🐳 Docker 배포 설정
└── README.md             # 📄 프로젝트 문서
```

## ⚙️ 설치 및 실행 (Installation & Run)

이 프로젝트는 **Docker Compose**를 사용하여 실행하는 것을 권장합니다.

### 1. 저장소 복제 (Clone)
```bash
git clone https://github.com/Ivan-LCH/my-asset-manager.git
cd my-asset-manager
```

### 2. 실행 (Run with Docker)
```bash
docker-compose up -d --build
```
실행 후 브라우저에서 `http://localhost:8502` (또는 서버 IP:8502)로 접속합니다.

> **참고:** 최초 실행 시 `data/assets.db` 파일이 자동으로 생성되며, 초기 데이터베이스 스키마가 구성됩니다.

## 🔒 보안 및 데이터 (Security)
- 모든 데이터는 로컬 `data/assets.db` 파일에 저장됩니다.
- 개인 자산 데이터 및 설정 파일은 `.gitignore` 처리되어 리포지토리에 포함되지 않습니다.
- VPN (Tailscale) 등을 활용하여 외부에서 안전하게 접속하는 것을 권장합니다.

---
**Author:** [Ivan-LCH](https://github.com/Ivan-LCH)
**Last Updated:** 2026-01-22