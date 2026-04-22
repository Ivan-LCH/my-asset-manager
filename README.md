# 💼 My Asset Manager

개인 자산 통합 관리 + 은퇴 현금흐름 시뮬레이션 시스템.
부동산·주식·연금·예적금·실물·기타 6가지 자산 유형을 하나의 대시보드에서 관리하며, 은퇴 후 생활비 계획까지 지원합니다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| UI 컴포넌트 | Recharts (차트), React Router v6, React Query v5 |
| Backend | Python 3.11 + FastAPI + Uvicorn (async) |
| DB | SQLAlchemy 2.0 (async) + aiosqlite + SQLite3 |
| 주가 데이터 | yfinance (Yahoo Finance) + APScheduler |
| 인프라 | Docker (포트 8090=웹, 1040=SSH) |

---

## 주요 기능

### 대시보드
- 총자산 / 부채 / 순자산 KPI 카드
- 자산 비중 도넛 차트 + 유형별 비율 바
- 전체 자산 성장 추이 Area Chart (기간 필터: 1개월~전체)

### 자산 유형별 페이지

#### 📈 주식
- 계좌 카드 그리드 → 종목 타일 → 모달 상세 3단 구조
- 계좌 선택 시 해당 계좌 종목별 성장 추이 차트로 자동 전환
- 실시간 시세 업데이트 (yfinance, 장중/종가 지원)
- 계좌별 합산 손익 / 수익률 표시

#### 🏠 부동산
- 순자산 기준 집계 (매매가 - 대출 - 전세보증금)
- 타일 내 순자산·부채·손익률 시각화

#### 🛡️ 연금
- 연금 자산 + 연금형 주식/예적금 통합 관리
- 2029년부터 100세까지 연금별 누적 막대차트 시뮬레이션
- 항목별 색상 구분, 커스텀 툴팁

#### 💰 예적금 / 💎 실물자산 / 🎸 기타
- 공통 타일 그리드 + 모달 상세 뷰

### 차트 공통
- 모든 차트 항목을 최근 평가액 기준 내림차순 정렬
- 커스텀 툴팁 (항목별 금액 + 합계)

### 🌅 은퇴 계획 (신규)
은퇴 후 현금흐름을 연도별로 시뮬레이션하는 전용 페이지.

**지출 설정**
- 월 생활비 항목별 입력 (2인 가구 기본값 preset, 초기화 버튼)
- 여행비: 여행 종류별로 "N회/년 → YYYY년까지, 이후 M회/년" 2단계 설정
- 의료비 월 적립액

**수입 설정**
- 목돈 수입 (전세금 반환·희망퇴직금 등): 수령연도 ~ 사용종료연도 기간 내 월 균등 환산
- 연금 수령액 자동 연동 (연금 페이지 데이터 재사용)

**긴급자금**
- 특정 연도 일회성 지출 (아들 결혼, 부모 간병비 등)

**연도별 현금흐름 테이블**

| 컬럼 | 설명 |
|------|------|
| 연금/월 | 해당 연도 연금 월 수령액 |
| 목돈/월 | 목돈의 기간 내 월 환산액 |
| 총수입/월 | 연금 + 목돈 합계 |
| 생활비·여행·의료/월 | 지출 항목별 월 금액 |
| 총지출/월 | 지출 합계 |
| 여유/부족 | 수입 - 지출 (초록/빨강) |
| 긴급지출 | 해당 연도 일회성 지출 |
| 누적자금 | 전년도 이월 + 당해 연간여유 - 긴급지출 |

은퇴 연도 행은 파란색으로 하이라이트. 모든 설정값은 DB에 영구 저장.

---

## 프로젝트 구조

```
backend/
├── api/
│   ├── assets.py      # 자산 CRUD + 차트 집계 (account 필터 지원)
│   ├── history.py     # 이력 관리
│   ├── stocks.py      # 주가 업데이트
│   ├── settings.py    # 앱 설정
│   └── retirement.py  # 은퇴 계획 데이터 저장/조회
├── core/config.py
├── db/
│   ├── models.py      # ORM 모델
│   ├── database.py    # async 엔진/세션
│   └── crud.py        # CRUD + 차트 집계 로직
├── services/
│   └── stock_updater.py  # yfinance 업데이트 (장중 실시간 포함)
└── main.py

frontend/src/
├── components/
│   ├── layout/        # Sidebar, Header, AppLayout
│   ├── assets/        # AssetCreateForm, AssetModal 등
│   └── common/        # AssetChart, KpiCard, PeriodFilter 등
├── hooks/             # useAssets, useHistory, useSettings, useRetirement 등
├── pages/
│   ├── Dashboard.tsx
│   ├── StockPage.tsx
│   ├── PensionPage.tsx
│   ├── RealEstatePage.tsx
│   ├── AssetPage.tsx  # 예적금/실물/기타 공통
│   ├── RetirementPage.tsx  # 은퇴 계획
│   └── Settings.tsx
├── types/index.ts
└── lib/
    ├── api.ts         # axios 클라이언트 + API 함수
    └── utils.ts       # 포맷팅 유틸
```

---

## DB 테이블

| 테이블 | 설명 |
|--------|------|
| `assets` | 자산 기본 정보 (UUID, type, name, current_value 등) |
| `real_estate_details` | 부동산 상세 (대출, 전세 등) |
| `stock_details` | 주식 상세 (계좌명, 통화, ticker 등) |
| `pension_details` | 연금 상세 (수령기간, 월수령액, 증가율) |
| `savings_details` | 예적금 상세 |
| `asset_history` | 자산별 날짜-금액 이력 |
| `settings` | 앱 설정 + 은퇴 계획 JSON (`retirement_plan` 키) |

---

## 빌드 & 실행

```bash
# 최초 실행
docker compose up --build

# 컨테이너 내 빌드 + 배포 (코드 변경 후)
docker exec my-asset-manager bash -c "cd /app && bash start_server.sh"

# 로그 확인
docker exec my-asset-manager tail -f /app/logs/server.log
```

접속: http://localhost:8090

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/assets` | 자산 목록 (type 필터) |
| POST | `/api/assets` | 자산 추가 |
| PUT | `/api/assets/{id}` | 자산 수정 |
| DELETE | `/api/assets/{id}` | 자산 삭제 |
| GET | `/api/assets/chart` | 차트 집계 (type, period, group_by, account 필터) |
| GET/POST/PUT/DELETE | `/api/assets/{id}/history` | 이력 관리 |
| POST | `/api/stocks/update` | 주가 일괄 업데이트 |
| GET/PUT | `/api/settings` | 앱 설정 |
| GET/PUT | `/api/retirement` | 은퇴 계획 저장/조회 |
