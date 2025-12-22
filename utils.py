# -----------------------------------------------------------------------------------------------------
# Import
# -----------------------------------------------------------------------------------------------------
import gspread
import pandas as pd
import json
import os
import streamlit as st
import csv

from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


# -----------------------------------------------------------------------------------------------------
# [설정]
# -----------------------------------------------------------------------------------------------------

SPREADSHEET_NAME = "MyAssetData" 
KEY_FILE         = "service_account.json"
LOCAL_CSV_FILE   = "my_assets-20251217.csv"

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# [핵심 수정] 헤더 매핑 강화 (오타 및 다양한 표기 허용)
HEADER_MAP = {
    # 날짜 관련
    "acqDate": "acquisitionDate",
    "acquisitionDate": "acquisitionDate",
    "aquisitionDate": "acquisitionDate", # 오타 방어
    "AcquisitionDate": "acquisitionDate",
    "취득일": "acquisitionDate",
    "날짜": "acquisitionDate",
    
    # 가격 관련
    "acqPrice": "acquisitionPrice",
    "acquisitionPrice": "acquisitionPrice",
    "aquisitionPrice": "acquisitionPrice", # 오타 방어
    "취득가": "acquisitionPrice",
    
    # 매각 관련
    "disposalDate": "disposalDate",
    "dispDate": "disposalDate",
    "매각일": "disposalDate",
    "disposalPrice": "disposalPrice",
    "dispPrice": "disposalPrice",
    "매각가": "disposalPrice",

    # 기타
    "currentValue": "currentValue",
    "현재가": "currentValue",
    "quantity": "quantity",
    "수량": "quantity",
    "detail1": "detail1",
    "detail2": "detail2",
    "detail3": "detail3",
    "detail4": "detail4",
    "detail5": "detail5",
    "history": "history"
}

SETTINGS_MAP = {
    "CurrentAge": "current_age",
    "RetirementAge": "retirement_age"
}

# -----------------------------------------------------------------------------------------------------
# Client & Helper
# -----------------------------------------------------------------------------------------------------

def get_client():
    # 1. [로컬/서버] 파일이 존재하면 파일에서 인증 (기존 방식)
    if os.path.exists(KEY_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, SCOPE)
        return gspread.authorize(creds)
    
    # 2. [Streamlit Cloud] 파일이 없으면 st.secrets에서 인증 정보 찾기
    elif "gcp_service_account" in st.secrets:
        try:
            # st.secrets는 딕셔너리 형태이므로 바로 사용
            creds_dict = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Streamlit Cloud 인증 오류: {e}")
            return None
            
    else:
        st.error("❌ 인증 파일(service_account.json)도 없고, Streamlit Secrets 설정도 없습니다.")
        return None

# -----------------------------------------------------------------------------------------------------
# Load Data
# -----------------------------------------------------------------------------------------------------

def load_data():
    try:
        client = get_client()
        if not client: return [], {}
        
        try:
            sh = client.open(SPREADSHEET_NAME)
        except gspread.SpreadsheetNotFound:
            st.error(f"❌ 구글 시트 '{SPREADSHEET_NAME}'를 찾을 수 없습니다.")
            return [], {}

        ws = sh.sheet1
        all_values = ws.get_all_values()
        
        # 데이터가 없으면 CSV 복구 시도
        if not all_values or len(all_values) < 8:
            if init_sheet_from_csv(ws):
                all_values = ws.get_all_values()
            else:
                return [], {}

        # 1. 헤더 행 찾기 (id, type이 있는 줄)
        header_index = -1
        header_row = []
        
        for i, row in enumerate(all_values):
            # 대소문자 구분 없이 찾기 위해 소문자로 변환해서 비교
            row_lower = [str(c).lower().strip() for c in row]
            if "id" in row_lower and "type" in row_lower:
                header_index = i
                header_row = row # 원본 대소문자 유지
                break
        
        # 못 찾으면 8번째 줄(index 7) 강제 지정
        if header_index == -1:
            if len(all_values) > 7:
                header_index = 7
                header_row = all_values[7]
            else:
                return [], {}

        # 2. 설정 로드
        settings = {"current_age": 40, "retirement_age": 60}
        for i in range(header_index):
            row = all_values[i]
            if len(row) >= 3 and row[0] == "CONFIG":
                sheet_key = row[1]
                val = row[2]
                if sheet_key in SETTINGS_MAP:
                    try: settings[SETTINGS_MAP[sheet_key]] = int(val)
                    except: pass

        # 3. 데이터 파싱
        data_rows = all_values[header_index + 1:]
        assets = []
        
        for row in data_rows:
            if not any(row): continue
            
            asset = {}
            for idx, col_name in enumerate(header_row):
                if idx < len(row):
                    raw_val = row[idx]
                    col_key = col_name.strip() # 공백 제거
                    
                    # [매핑] 시트 헤더 -> 앱 내부 키
                    # 매핑 테이블에 없으면 원래 이름 사용
                    app_key = HEADER_MAP.get(col_key, col_key)
                    # 혹시 매핑 키도 못 찾으면, 소문자로도 한번 더 검색 (acqDate vs acqdate)
                    if app_key == col_key:
                         for k, v in HEADER_MAP.items():
                             if k.lower() == col_key.lower():
                                 app_key = v
                                 break
                    
                    # History JSON 파싱
                    val = raw_val
                    if app_key == "history":
                        try:
                            if val.startswith("[") or val.startswith("{"):
                                val = json.loads(val)
                            else: val = []
                        except: val = []
                    
                    asset[app_key] = val
            assets.append(asset)
            
        return assets, settings

    except Exception as e:
        st.error(f"❌ 데이터 로드 오류: {e}")
        return [], {}

# -----------------------------------------------------------------------------------------------------
# Save Data
# -----------------------------------------------------------------------------------------------------

def save_data(assets, settings):
    try:
        client = get_client()
        sh = client.open(SPREADSHEET_NAME)
        ws = sh.sheet1
        current_values = ws.get_all_values()
        
        # 헤더 위치 다시 찾기
        header_index = -1
        current_header = []
        
        for i, row in enumerate(current_values):
            row_lower = [str(c).lower().strip() for c in row]
            if "id" in row_lower and "type" in row_lower:
                header_index = i
                current_header = row
                break
        
        if header_index == -1: 
            header_index = 7
            # 기본 헤더 정의
            current_header = [
                "id", "type", "name", "currentValue", 
                "acqDate", "acqPrice", "quantity", 
                "disposalDate", "disposalPrice", 
                "detail1", "detail2", "detail3", "detail4", "detail5", 
                "history"
            ]

        # 상단 설정 유지
        top_section = current_values[:header_index]
        if not top_section:
             top_section = [
                ["TYPE", "KEY", "VALUE"],
                ["CONFIG", "CurrentAge", "40"],
                ["CONFIG", "RetirementAge", "60"],
                ["CONFIG", "CurrencySymbol", "KRW"],
                ["", "", ""], ["", "", ""], ["", "", ""]
            ]
            
        new_top_section = []
        for row in top_section:
            new_row = list(row) + [""] * (3 - len(row))
            if new_row[0] == "CONFIG":
                sk = new_row[1]
                if sk in SETTINGS_MAP:
                    ak = SETTINGS_MAP[sk]
                    new_row[2] = str(settings.get(ak, ""))
            new_top_section.append(new_row)

        # 데이터 재작성
        # 주의: 기존 시트의 헤더 순서를 최대한 존중해서 저장
        asset_rows = []
        for a in assets:
            row = []
            for col_name in current_header:
                col_key = col_name.strip()
                
                # 시트 헤더 이름으로 앱 내부 키 찾기 (매핑)
                app_key = HEADER_MAP.get(col_key, col_key)
                # 대소문자 방어
                if app_key == col_key:
                     for k, v in HEADER_MAP.items():
                         if k.lower() == col_key.lower():
                             app_key = v
                             break
                
                val = a.get(app_key, "")
                
                # JSON 변환
                if app_key == "history" and isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                
                row.append(val)
            asset_rows.append(row)
            
        final_data = new_top_section + [current_header] + asset_rows
        
        ws.clear()
        ws.update(range_name='A1', values=final_data)
        return True

    except Exception as e:
        st.error(f"❌ 데이터 저장 오류: {e}")
        return False