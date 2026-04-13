# 🔧 3단계 기술 규격 및 API 상세 명세

## 1. TypeScript 타입 정의 (`frontend/src/types/index.ts`)

```typescript
// 자산 유형
export type AssetType = 'REAL_ESTATE' | 'STOCK' | 'PENSION' | 'SAVINGS' | 'PHYSICAL' | 'ETC';

// 통화
export type Currency = 'KRW' | 'USD' | 'JPY';

// 공통 자산
export interface Asset {
  id: string;
  type: AssetType;
  name: string;
  currentValue: number;
  acquisitionDate: string;       // YYYY-MM-DD
  acquisitionPrice: number;
  disposalDate?: string;         // null이면 보유중
  disposalPrice?: number;
  quantity: number;
  createdAt: string;
  updatedAt: string;
  history: HistoryItem[];
  // 유형별 상세 (JOIN 결과)
  detail?: RealEstateDetail | StockDetail | PensionDetail | SavingsDetail;
}

// 이력
export interface HistoryItem {
  date: string;      // YYYY-MM-DD
  value?: number;    // 평가액 (KRW)
  price?: number;    // 단가
  quantity?: number; // 수량
}

// 부동산 상세
export interface RealEstateDetail {
  isOwned: boolean;
  hasTenant: boolean;
  tenantDeposit: number;
  address: string;
  loanAmount: number;
}

// 주식 상세
export interface StockDetail {
  accountName: string;
  currency: Currency;
  isPensionLike: boolean;
  pensionStartYear?: number;
  pensionMonthly?: number;
  ticker?: string;
}

// 연금 상세
export interface PensionDetail {
  pensionType?: string;
  expectedStartYear: number;
  expectedEndYear: number;
  expectedMonthlyPayout: number;
  annualGrowthRate: number;
}

// 예적금 상세
export interface SavingsDetail {
  isPensionLike: boolean;
  pensionStartYear?: number;
  pensionMonthly?: number;
}

// 차트 데이터
export interface ChartDataPoint {
  date: string;
  value: number;
  name?: string;
  type?: AssetType;
  account?: string;
}

// 카테고리 KPI
export interface CategoryKpi {
  totalAsset: number;
  totalLiability: number;
  netWorth: number;
}

// 설정
export interface Settings {
  currentAge: number;
  retirementAge: number;
  [key: string]: number | string; // ACC_TOTAL_{계좌명} 등
}

// 차트 요청 파라미터
export interface ChartParams {
  type?: AssetType;
  period?: 'all' | '10y' | '3y' | '1y' | '3m' | '1m';
  group_by?: 'type' | 'name' | 'account';
}

// API 응답 래퍼
export interface ApiResponse<T> {
  data: T;
  message?: string;
}
```

> **네이밍 컨벤션**: Backend API 응답은 **snake_case** (Python 표준), Frontend 타입은 **camelCase** (TypeScript 표준).
> API 클라이언트(`lib/api.ts`)에서 응답 수신 시 snake_case → camelCase 자동 변환 유틸 적용.
> (예: `current_value` → `currentValue`). 요청 전송 시에는 camelCase → snake_case 역변환.

---

## 2. API 엔드포인트 상세 명세

### 2.1 자산 조회 (`GET /api/assets`)

**Response 200**:
```json
[
  {
    "id": "uuid-string",
    "type": "STOCK",
    "name": "삼성전자",
    "current_value": 5000000,
    "acquisition_date": "2023-01-15",
    "acquisition_price": 65000,
    "disposal_date": null,
    "disposal_price": 0,
    "quantity": 77,
    "created_at": "2023-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00",
    "detail": {
      "account_name": "키움증권",
      "currency": "KRW",
      "ticker": "005930.KS",
      "is_pension_like": false
    },
    "history": [
      {"date": "2023-01-15", "price": 65000, "quantity": 77, "value": 5005000},
      {"date": "2024-01-15", "price": 75000, "quantity": 77, "value": 5775000}
    ]
  }
]
```

### 2.2 자산 추가 (`POST /api/assets`)

**Request Body**:
```json
{
  "type": "STOCK",
  "name": "삼성전자",
  "current_value": 5005000,
  "acquisition_date": "2023-01-15",
  "acquisition_price": 65000,
  "quantity": 77,
  "detail": {
    "account_name": "키움증권",
    "currency": "KRW",
    "ticker": "005930.KS"
  },
  "initial_history": {
    "date": "2023-01-15",
    "price": 65000,
    "quantity": 77,
    "value": 5005000
  }
}
```

**Response 201**:
```json
{"id": "generated-uuid", "message": "자산이 추가되었습니다."}
```

### 2.3 자산 수정 (`PUT /api/assets/{id}`)

**Request Body**: 추가와 동일한 구조 (id 제외)

**Response 200**:
```json
{"message": "수정되었습니다."}
```

### 2.4 이력 수정 (`PUT /api/assets/{id}/history/{date}`)

**Request Body**:
```json
{
  "price": 75000,
  "quantity": 77,
  "value": null
}
```
- `value`가 null이면 `price * quantity * exchange_rate`로 자동 계산
- 수량이 변경되면 해당 날짜 이후 모든 이력의 수량 전파

**Response 200**:
```json
{
  "message": "수정되었습니다.",
  "propagated_count": 3
}
```

### 2.5 차트 데이터 (`GET /api/assets/chart`)

**Query Parameters**:
- `type`: AssetType (optional, 없으면 전체)
- `period`: `all` | `10y` | `3y` | `1y` | `3m` | `1m` (default: `all`)
- `group_by`: `type` | `name` | `account` (default: `type`)

**Response 200**:
```json
[
  {"date": "2024-01-01", "label": "📈 주식", "value": 50000000},
  {"date": "2024-01-01", "label": "🏠 부동산", "value": 300000000},
  {"date": "2024-01-02", "label": "📈 주식", "value": 51000000}
]
```

### 2.6 주식 업데이트 (`POST /api/stocks/update`)

**Request Body**: 없음 (또는 `{"force": true}` for full refresh)

**Response 200**:
```json
{
  "updated_count": 5,
  "failed_tickers": ["INVALID_TICKER"],
  "message": "5개 종목 업데이트 완료"
}
```

### 2.7 설정 (`GET /api/settings`, `PUT /api/settings`)

**GET Response 200**:
```json
{
  "current_age": 42,
  "retirement_age": 60,
  "ACC_TOTAL_키움증권": 5000000
}
```

**PUT Request Body**:
```json
{
  "current_age": 42,
  "retirement_age": 60
}
```

---

## 3. 백엔드 패키지 명세 (`requirements.txt`)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
pandas>=2.2.0
yfinance>=0.2.36
apscheduler>=3.10.0
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
```

---

## 4. 프론트엔드 패키지 명세 (`package.json`)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "@tanstack/react-query": "^5.20.0",
    "recharts": "^2.10.0",
    "react-hook-form": "^7.50.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "date-fns": "^3.3.0",
    "axios": "^1.6.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "lucide-react": "^0.330.0",
    "class-variance-authority": "^0.7.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

---

## 5. 환경 설정 (`.env`)

```bash
# 서버 설정
HOST=0.0.0.0
PORT=8090

# DB 설정
DB_FILE_NAME=assets.db
DB_DIR=data

# 개발 환경 (프론트 dev server CORS 허용)
CORS_ORIGINS=http://localhost:5173,http://localhost:8090
```

---

## 6. Docker 설정

### `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node.js 설치 (프론트엔드 빌드용)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# 소스 복사
COPY . .

# 프론트엔드 빌드
RUN cd frontend && npm install && npm run build && \
    cp -r dist/* /app/static/

# 포트 노출
EXPOSE 8090

# 시작
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8090"]
```

### `docker-compose.yml`
```yaml
version: '3.8'
services:
  asset-manager:
    build: .
    container_name: my-asset-manager
    ports:
      - "8090:8090"
      - "1040:22"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - PORT=8090
    restart: unless-stopped
```

---

## 7. start_server.sh (개발/배포 스크립트)

```bash
#!/bin/bash
set -e

echo "▶ 기존 서버 종료..."
pkill -f "uvicorn backend.main" || true
sleep 1

echo "▶ 프론트엔드 빌드..."
cd /app/frontend
npm run build
cp -r dist/* /app/static/
cd /app

echo "▶ 백엔드 시작..."
mkdir -p logs data
nohup uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8090 \
  --log-level info \
  > logs/server.log 2>&1 &
echo $! > server.pid
echo "✅ 서버 시작 완료 (PID: $(cat server.pid))"
```
