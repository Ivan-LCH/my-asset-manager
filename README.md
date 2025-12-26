# 💰 My Asset Manager (Personal Wealth Dashboard)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![License](https://img.shields.io/badge/License-MIT-green)

## 📖 프로젝트 개요 (Overview)
**My Asset Manager**는 흩어져 있는 개인의 자산을 통합하여 관리하는 **Python Streamlit 기반의 웹 대시보드**입니다.

부동산, 주식, 연금 등 다양한 자산군을 하나의 플랫폼에서 모니터링하며, **`app.py`**를 통해 직관적인 UI로 현재 자산 상태와 포트폴리오 비중을 시각화하여 보여줍니다.

## 🚀 주요 기능 (Key Features)

프로그램 실행 시 탭(Tab) 또는 사이드바 메뉴의 순서는 다음과 같습니다.

### 1. 📊 통합 대시보드 (Dashboard)
- **자산 현황 요약:** 총 자산(Total Net Worth) 및 전월 대비 증감액 자동 계산
- **포트폴리오 비중:** 부동산, 주식, 연금 등 자산군별 구성 비율 시각화 (Pie Chart)
- **트렌드 분석:** 자산 변동 추이 그래프 제공

### 2. 🏠 부동산 관리 (Real Estate)
- **보유 부동산 목록:** 아파트, 오피스텔 등 매입가 및 현재 시세 관리
- **가치 변동 추적:** 실거래가 정보(또는 입력된 시세)를 기반으로 자산 가치 평가

### 3. 📈 주식 포트폴리오 (Stocks)
- **투자 현황:** 국내(KRW) 및 해외(USD) 주식 종목별 평가 금액 확인
- **수익률 분석:** 매입가 대비 현재 평가 손익 및 수익률 계산
- **환율 적용:** `utils.py`를 통해 실시간/고시 환율을 적용한 원화 환산 가치 제공

### 4. 🛡️ 연금 및 노후 자산 (Pension)
- **연금 계좌 통합:** 개인연금, 퇴직연금(IRP/DC) 누적 자산 합산
- **노후 준비 상태:** 장기 투자 자산의 현재 가치 확인

## 🛠️ 기술 스택 (Tech Stack)
- **Frontend/App:** Python, Streamlit (`app.py`)
- **Data Processing:** Pandas, NumPy
- **Utility Modules:** `utils.py` (환율 조회, 데이터 전처리 로직)
- **Visualization:** Plotly, Altair

## 📂 프로젝트 구조 (Project Structure)
```bash
my-asset-manager/
├── app.py               # 🚀 메인 애플리케이션 (Streamlit Entry Point)
├── utils.py             # ⚙️ 데이터 로드, 환율 계산 등 유틸리티 함수
├── data/                # 🗃️ 자산 데이터 파일 (csv/excel) *Git 제외 (.gitignore)
├── requirements.txt     # 📦 프로젝트 의존성 라이브러리 목록
└── README.md            # 📄 프로젝트 문서
```

## ⚙️ 설치 및 실행 (Installation & Run)

### 1. 저장소 복제 (Clone)
```bash
git clone https://github.com/Ivan-LCH/my-asset-manager.git
cd my-asset-manager
```

### 2. 라이브러리 설치 (Install Dependencies)
```bash
pip install -r requirements.txt
```

### 3. 애플리케이션 실행 (Run App)
```bash
streamlit run app.py
```
실행 후 브라우저가 자동으로 열리며 `http://localhost:8501`에서 대시보드를 확인할 수 있습니다.

## 🔒 보안 및 데이터 (Security)
- 개인 자산 데이터가 포함된 파일(`data/*.csv`, `secrets.toml` 등)은 `.gitignore` 처리가 되어 있어 리포지토리에 업로드되지 않습니다.
- 본 프로젝트는 로컬 환경에서의 실행을 권장합니다.

---
**Author:** [Ivan-LCH](https://github.com/Ivan-LCH)
**Last Updated:** 2025-12-26