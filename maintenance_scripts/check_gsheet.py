import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# 설정
KEY_FILE = "service_account.json"
SPREADSHEET_NAME = "MyAssetData"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def debug_connection():
    print("---------------------------------------------------")
    print("🔍 구글 시트 연결 진단 시작")
    print("---------------------------------------------------")

    # 1. 키 파일 존재 확인
    if not os.path.exists(KEY_FILE):
        print(f"❌ [에러] '{KEY_FILE}' 파일이 없습니다.")
        return

    try:
        # 2. 인증 시도
        creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, SCOPE)
        client = gspread.authorize(creds)
        print(f"✅ [인증 성공] 접속 계정: {creds.service_account_email}")
        print("   (위 이메일 주소가 구글 시트 '공유' 목록에 편집자로 추가되어 있어야 합니다!)")
        
        # 3. 시트 열기 시도
        try:
            sh = client.open(SPREADSHEET_NAME)
            print(f"✅ [시트 찾기 성공] 파일명: {sh.title}")
        except gspread.SpreadsheetNotFound:
            print(f"❌ [에러] 시트 '{SPREADSHEET_NAME}'를 찾을 수 없습니다.")
            print("   -> 구글 드라이브에 있는 파일명과 정확히 일치하는지(띄어쓰기 등) 확인하세요.")
            print("   -> 봇 계정(위 이메일)에 공유가 되어있는지 확인하세요.")
            return

        # 4. 데이터 읽기
        ws = sh.sheet1
        print(f"✅ [워크시트 접속] 시트 이름: {ws.title}")
        
        all_values = ws.get_all_values()
        row_count = len(all_values)
        print(f"📊 [데이터 확인] 총 {row_count}개의 행(Row)을 읽었습니다.")
        
        if row_count > 0:
            print("\n--- [상위 5줄 데이터 미리보기] ---")
            for i, row in enumerate(all_values[:5]):
                print(f"Row {i+1}: {row}")
            print("-----------------------------------")
        else:
            print("⚠️ [경고] 시트가 완전히 비어있습니다!")

    except Exception as e:
        print(f"❌ [치명적 오류] {e}")

if __name__ == "__main__":
    debug_connection()
