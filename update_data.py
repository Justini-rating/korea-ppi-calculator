import pandas as pd
import requests
import os
import datetime

# --------------------------------------------------------------------------
# 1. 설정 (사용자 제공 코드 기반)
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY") # GitHub Secret 사용
ORG_ID = "301"
TBL_ID = "DT_404Y016"  # [수정됨] 014 -> 016
ITM_ID = "13103134764999" # [수정됨] T1 -> 긴 번호

# --------------------------------------------------------------------------
# 2. 날짜 계산
# --------------------------------------------------------------------------
start_date = "201901"
end_date = datetime.datetime.now().strftime("%Y%m")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출 (사용자 코드 파라미터 적용)
# --------------------------------------------------------------------------
url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
params = {
    "method": "getList",
    "apiKey": API_KEY,
    "itmId": ITM_ID,
    "objL1": "ALL",
    "objL2": "", # 빈 값으로 명시 (중요)
    "objL3": "",
    "objL4": "",
    "objL5": "",
    "objL6": "",
    "objL7": "",
    "objL8": "",
    "format": "json",
    "jsonVD": "Y",
    "prdSe": "M",
    "orgId": ORG_ID,
    "tblId": TBL_ID,
    "startPrdDe": start_date,
    "endPrdDe": end_date
}

print(f"데이터 다운로드 시작... (기간: {start_date} ~ {end_date})")

try:
    response = requests.get(url, params=params, timeout=60)
    
    # 응답 체크
    if response.status_code != 200:
        print(f"❌ 서버 접속 실패: {response.status_code}")
        exit(1)
        
    data = response.json()
    
    # 데이터 유효성 체크
    if isinstance(data, dict) and 'err' in data:
        print(f"❌ API 오류 발생: {data.get('errMsg')}")
        # 디버깅을 위해 URL 출력 (키는 가림)
        print(f"요청 URL: {response.url.replace(API_KEY, '***')}")
        exit(1)
        
    if not data:
        print("❌ 데이터가 없습니다.")
        exit(1)

    # --------------------------------------------------------------------------
    # 4. 데이터 가공 (사용자 코드 로직 적용)
    # --------------------------------------------------------------------------
    df = pd.DataFrame(data)
    print(f"✅ 다운로드 성공! 총 {len(df)}건")

    # [중요] 품목명 생성 로직 (C1_NM + ITM_NM)
    # 사용자 코드: df_new['C1_NM'].astype(str) + "_" + df_new['ITM_NM'].astype(str)
    if 'C1_NM' in df.columns:
        df['Item_Name'] = df['C1_NM'].astype(str) + "_" + df['ITM_NM'].astype(str)
    else:
        df['Item_Name'] = df['ITM_NM'].astype(str)

    # 불필요한 문구 제거
    df['Item_Name'] = df['Item_Name'].str.replace('_생산자물가지수(품목별)', '', regex=False)

    # 숫자형 변환
    df['DT'] = pd.to_numeric(df['DT'], errors='coerce')

    # 피벗 (행: 품목, 열: 날짜, 값: 지수)
    df_pivot = df.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    
    # 인덱스 이름 설정 (App.py와 호환되게)
    df_pivot.index.name = '품목 / 시점'

    # CSV 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("💾 data.csv 업데이트 및 저장 완료!")

except Exception as e:
    print(f"❌ 처리 중 치명적 오류: {e}")
    exit(1)
