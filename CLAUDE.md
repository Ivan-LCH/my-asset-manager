# My Asset Manager - Claude Code 가이드라인

## 프로젝트 개요
개인 자산 관리 시스템. 부동산·주식·연금·예적금·실물·기타 6가지 유형의 자산을 통합 관리하는 전문가 풍 금융 대시보드.

## Tech Stack
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS
  - UI: shadcn/ui (컴포넌트), Recharts (차트), React Router v6, React Query v5
  - 폼: React Hook Form + Zod
- **Backend**: Python 3.11 + FastAPI + Uvicorn (async)
  - DB: SQLAlchemy 2.0 (async) + aiosqlite + SQLite3
  - 주가: yfinance (Yahoo Finance), APScheduler
- **Infra**: Docker (port 8090=웹, 1040=SSH)

## 프로젝트 구조
```
backend/
├── api/         # 라우터 (assets, history, stocks, settings)
├── core/        # config.py
├── db/          # models.py, database.py, crud.py
├── services/    # stock_updater.py
└── main.py

frontend/src/
├── components/
│   ├── layout/   # Sidebar, Header, AppLayout
│   ├── dashboard/ # KpiCards, PieChart, AreaChart
│   ├── assets/   # AssetCard, AssetDetail, AssetForm, HistoryTable
│   └── common/   # KpiCard, AssetChart, PeriodFilter, ConfirmDialog
├── hooks/        # useAssets, useHistory, useSettings, useChart
├── pages/        # Dashboard, RealEstate, Stock, Pension, Savings, Physical, Etc, Settings
├── types/        # index.ts (TypeScript 타입)
├── lib/          # api.ts, utils.ts, chartUtils.ts
└── App.tsx
```

## API 엔드포인트
- `GET/POST /api/assets` — 자산 목록/추가
- `PUT/DELETE /api/assets/{id}` — 자산 수정/삭제
- `GET /api/assets/chart?type=&period=&group_by=` — 차트 집계 데이터
- `GET/POST/PUT/DELETE /api/assets/{id}/history` — 이력 관리
- `POST /api/stocks/update` — 주가 자동 업데이트
- `GET/PUT /api/settings` — 설정

## DB 테이블
- `assets`: id(UUID), type, name, current_value, acquisition_date, acquisition_price, disposal_date, disposal_price, quantity
- `real_estate_details`: asset_id, is_owned, has_tenant, tenant_deposit, address, loan_amount
- `stock_details`: asset_id, account_name, currency, is_pension_like, pension_start_year, pension_monthly, ticker
- `pension_details`: asset_id, pension_type, expected_start_year, expected_end_year, expected_monthly_payout, annual_growth_rate
- `savings_details`: asset_id, is_pension_like, pension_start_year, pension_monthly
- `asset_history`: id, asset_id, date, value, price, quantity
- `settings`: key, value

## 주요 코딩 컨벤션
- 한국어 주석/문서, 영어 코드(변수명, 함수명)
- Backend API prefix: `/api/`
- DB 파일: `data/assets.db`
- 프론트엔드 빌드 결과물: `/static` 디렉토리에 서빙
- 금액 단위: 원(KRW), 만원 단위 표기 시 `formatManwon()` 사용

## 자산 유형 상수
```typescript
type AssetType = 'REAL_ESTATE' | 'STOCK' | 'PENSION' | 'SAVINGS' | 'PHYSICAL' | 'ETC'
```

## 빌드 & 실행
```bash
# 컨테이너 내 빌드+배포
docker exec my-asset-manager bash -c "cd /app && bash start_server.sh"

# 최초 실행
docker compose up --build

# 로그
docker exec my-asset-manager tail -f /app/logs/server.log
```

## 참조 문서
- `docs/1단계_요구사항_정의.md` — 기능 요구사항 전체
- `docs/2단계_시스템_설계서.md` — 아키텍처 & DB 스키마
- `docs/3단계_기술_규격_및_API.md` — API 상세 스펙, 타입 정의
- `docs/4단계_구현_상세_가이드.md` — 구현 로직 상세, 컴포넌트 구조
- `docs/5단계_기능_완료_보고서.md` — 구현 진행 상황 체크리스트
- `docs/6단계_운영_매뉴얼.md` — 배포 및 운영 가이드
