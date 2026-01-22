# 📂 Asset Manager 프로젝트 구조

**기술 스택:** Python + Streamlit + SQLite + Plotly + Docker

---

## 📁 주요 파일들

| 파일 | 역할 |
|------|------|
| `app.py` | 메인 Streamlit 애플리케이션. UI 및 비즈니스 로직 담당 |
| `database.py` | SQLite DB 연결, 스키마 정의, CRUD 함수 (SQL 쿼리) |
| `utils.py` | `database.py`를 래핑하여 앱에 맞는 데이터 포맷으로 변환 및 로드/저장 |
| `migrate_from_gsheet.py` | Google Sheets 데이터를 SQLite로 이관하는 일회성 스크립트 |
| `docker-compose.yml` | Docker 컨테이너 배포 및 볼륨 설정 |
| `data/assets.db` | 실제 자산 데이터가 저장되는 SQLite 데이터베이스 파일 |

---

## 🏗️ 데이터베이스 스키마 (SQLite)

### 1. `assets` (공통 테이블)
모든 자산의 기본 정보 저장 (ID, 유형, 이름, 현재가, 취득일 등)

### 2. 세부 정보 테이블 (1:1 관계)
- `real_estate_details`: 부동산 (소유여부, 세입자, 대출금 등)
- `stock_details`: 주식 (계좌명, 통화, 잔고보정 여부 등)
- `pension_details`: 연금 (유형, 수령시작년도, 월수령액 등)
- `savings_details`: 예적금 (연금성 여부 등)

### 3. `asset_history` (이력 테이블)
자산별 날짜, 가치, 가격, 수량 이력 저장 (JSON이 아닌 RDB 정규화 구조)

### 4. `settings` (키-값 저장)
사용자 나이, 은퇴 목표 나이, 계좌별 목표 금액 등 설정 저장

---

## 📱 앱 구조 (app.py)

| 기능 | 설명 |
|------|------|
| **자산 파싱** | `utils.load_data()`에서 받은 데이터를 UI 표시용으로 추가 가공 (`parse_asset_details`) |
| **차트 생성** | `asset_history` 데이터를 기반으로 시계열 데이터프레임 생성 및 Plotly 차트 렌더링 |
| **상세 렌더링** | `render_asset_detail()` 함수를 통해 각 자산 유형별 맞춤형 편집 UI 제공 |
| **저장 로직** | 사이드바의 "저장하기" 버튼 클릭 시 `utils.save_data()` 호출 → DB 업데이트 |

---

## 📊 데이터 흐름

```mermaid
graph TD
    DB[(SQLite assets.db)]
    
    subgraph Backend
        DB <--> |SQL| DatabasePY[database.py]
        DatabasePY <--> |Dict/Obj| UtilsPY[utils.py]
    end
    
    subgraph Frontend
        UtilsPY --> |List[Dict]| AppPY[app.py]
        AppPY --> |UI Render| User((User))
        User --> |Edit & Save| AppPY
        AppPY --> |Updated List| UtilsPY
    end
```

---

## 🔒 배포 및 보안

1. **Docker**: `python:3.9-slim` 기반 이미지 사용, 포트 8502 노출
2. **볼륨 마운트**: 호스트의 `./data`를 컨테이너의 `/app/data`로 마운트하여 데이터 영구 보존
3. **네트워크**: Tailscale을 통해 외부에서 안전하게 접근 (권장)

---

**Last Updated:** 2026-01-22
