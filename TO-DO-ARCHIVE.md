# TO-DO ARCHIVE — My Asset Manager

> 완료된 작업들의 기록

---

## 2026-04-10 — 프로젝트 초기화

- [C] Streamlit 기반 기존 프로젝트 분석 (app.py 1359줄, database.py)
- [C] 기존 프로젝트 백업 (`/root/my_prog/backup_asset_manager`)
- [C] 신규 프로젝트 디렉토리 구조 생성 (FastAPI + React + TypeScript)
- [C] 문서 6종 작성
  - [C] 1단계 요구사항 정의서
  - [C] 2단계 시스템 설계서 (DB 스키마, 아키텍처)
  - [C] 3단계 기술 규격 및 API 상세 명세
  - [C] 4단계 구현 상세 가이드
  - [C] 5단계 기능 완료 보고서 (체크리스트)
  - [C] 6단계 운영 매뉴얼
- [C] CLAUDE.md 작성
- [C] TO-DO-LIST.md 초안 작성

---

## 2026-04-22 — Phase 7: UI 전면 개선 확인완료

### 버그 수정
- [C] 7-1. 전체 자산현황 차트 미표시 버그 수정 — `acquisition_date` None 처리 (`crud.py`)

### 대시보드
- [C] 7-2. 자산 비중 차트 — 도넛 + 가로 비율 바 테이블 조합으로 개선
- [C] 7-3. 레이아웃 모바일 대응 — 자산비중 / 자산성장추이 각 1줄씩 배치

### 공통 모달 시스템
- [C] 7-4. `AssetModal.tsx` 공통 모달 컴포넌트 (ESC 닫기, 배경 클릭 닫기, 스크롤)
- [C] 7-5. 전체 페이지 일관된 모달 상세 뷰 적용

### 부동산 페이지
- [C] 7-6. 자산 목록 타일 그리드 + 모달 상세
- [C] 7-7. 타일 내 순자산/부채/손익률 핵심 지표 시각화

### 주식 페이지
- [C] 7-8. 계좌 카드 그리드 → 종목 타일 → 모달 3단 구조
- [C] 7-9. 계좌 카드 — 보유 종목 미리보기 3개 + 계좌 합산 손익
- [C] 7-10. 브레드크럼 네비게이션 (전체 → 계좌명)
- [C] 7-11. 계좌 요약 배너 (계좌 선택 후 상단 고정)
- [C] 7-12 (추가). 계좌 선택 시 해당 계좌 차트 연동 — `account` 쿼리 파라미터 추가, `groupBy="name"` 전환
- [C] 7-13 (추가). 차트 항목 최근 평가액 기준 내림차순 정렬

### 연금 페이지
- [C] 7-14. 연금 자산 타일 그리드 + 모달 상세
- [C] 7-15. 연금형 포함 자산 별도 타일 섹션

### 예적금 / 실물 / 기타 페이지
- [C] 7-16. 자산 타일 그리드 + 모달 상세 (공통 AssetPage 적용)

### 이력 관리
- [C] 7-17. 이력 테이블 고정 높이(max-h-64) + 내부 스크롤 + thead sticky

### 공통 컴포넌트
- [C] 7-18. KpiCard — 상단 컬러 바 + 컬러별 배경 tint
- [C] 7-19. AssetDetail — InfoCell 카드 스타일, 정보 밀도 개선
- [C] 7-20. 전체 기능 테스트 (사용자 확인완료)
- [C] 7-21. TO-DO-ARCHIVE.md 정리

---

## 2026-04-10 — Phase 1~6 전체 구현 완료

### Phase 1: 백엔드 기반
- [C] 1-1. `backend/core/config.py` — 환경설정 (DB 경로, CORS 등)
- [C] 1-2. `backend/db/database.py` — SQLAlchemy async 엔진, 세션, init_db()
- [C] 1-3. `backend/db/models.py` — ORM 모델 7개 테이블
- [C] 1-4. `backend/db/crud.py` — CRUD 함수 전체
- [C] 1-5. `backend/api/assets.py` — 자산 CRUD + 차트 집계 API
- [C] 1-6. `backend/api/history.py` — 이력 API (수량 전파 포함)
- [C] 1-7. `backend/api/stocks.py` — 주가 업데이트 API
- [C] 1-8. `backend/api/settings.py` — 설정 API
- [C] 1-9. `backend/services/stock_updater.py` — yfinance 업데이트 서비스
- [C] 1-10. `backend/main.py` — FastAPI 앱 진입점
- [C] 1-11. `requirements.txt` 작성

### Phase 2: 프론트엔드 기반 구조
- [C] 2-1. `frontend/` — Vite + React + TypeScript 프로젝트 생성
- [C] 2-2. Tailwind CSS 설정 (shadcn 미사용, 직접 구현)
- [C] 2-3. `src/types/index.ts` — TypeScript 타입 정의
- [C] 2-4. `src/lib/api.ts` — API 클라이언트
- [C] 2-5. `src/lib/utils.ts` — 포맷팅 유틸
- [C] 2-6. React Query 설정 (QueryClientProvider)
- [C] 2-7. `src/hooks/` — useAssets, useHistory, useSettings, useChart, useStocks
- [C] 2-8. `src/App.tsx` — React Router 라우팅
- [C] 2-9. `src/components/layout/` — AppLayout, Sidebar
- [C] 2-10. `vite.config.ts` — 프록시 설정

### Phase 3: 대시보드
- [C] 3-1. `src/pages/Dashboard.tsx`
- [C] 3-2. KPI 카드 3종 (총자산/부채/순자산)
- [C] 3-3. 자산 비중 도넛 차트
- [C] 3-4. 자산 성장 추이 Area Chart
- [C] 3-5 ~ 3-8. 공통 컴포넌트 4종

### Phase 4: 자산 유형별 페이지 (공통)
- [C] 4-1 ~ 4-8. AssetPage, AssetDetail, HistoryTable, AssetForm, AssetCreateForm 전체

### Phase 5: 특수 기능
- [C] 5-1 ~ 5-5. StockPage (계좌별/종목별), PensionPage (시뮬레이션) 전체

### Phase 6: 인프라
- [C] 6-1. `src/pages/Settings.tsx` — 설정 페이지
- [C] 6-2. `Dockerfile` 작성
- [C] 6-3. `docker-compose.yml` 작성
- [C] 6-4. `start_server.sh` 작성
- [C] 6-5. 기존 DB 데이터 이관 확인 (자산 36개 정상 조회)
- [C] 6-6. Docker 빌드 & 배포 검증
