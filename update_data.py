import pandas as pd
import requests
import os
import datetime
from dateutil.relativedelta import relativedelta

# --------------------------------------------------------------------------
# 1. 설정
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"
TBL_ID = "DT_404Y016"
ITM_ID = "13103134764999"
FILE_NAME = "data.csv"

# --------------------------------------------------------------------------
# 2. 날짜 계산 (최근 3개월 데이터 요청)
# --------------------------------------------------------------------------
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")
start_dt = now - relativedelta(months=3)
start_date = start_dt.strftime("%Y%m")

print(f"🔄 2026년 개편 대응 동기화 시작: {start_date} ~ {end_date}")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출
# --------------------------------------------------------------------------
url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
params = {
    "method": "getList",
    "apiKey": API_KEY,
    "itmId": ITM_ID,
    "objL1": "ALL", "objL2": "", "objL3": "", "objL4": "",
    "objL5": "", "objL6": "", "objL7": "", "objL8": "",
    "format": "json", "jsonVD": "Y", "prdSe": "M",
    "orgId": ORG_ID, "tblId": TBL_ID,
    "startPrdDe": start_date, "endPrdDe": end_date
}

try:
    response = requests.get(url, params=params, timeout=60)
    data = response.json()
    
    if isinstance(data, dict) and 'err' in data:
        print(f"❌ API 오류: {data.get('errMsg')}")
        exit(1)
        
    if not data or len(data) == 0:
        print("ℹ️ 아직 이번 달 신규 데이터가 발표되지 않았습니다.")
        exit(0)

    # --------------------------------------------------------------------------
    # 4. 신규 데이터 가공
    # --------------------------------------------------------------------------
    df_fetched = pd.DataFrame(data)
    
    if 'C1_NM' in df_fetched.columns:
        df_fetched['Item_Name'] = df_fetched['C1_NM'].astype(str) + "_" + df_fetched['ITM_NM'].astype(str)
    else:
        df_fetched['Item_Name'] = df_fetched['ITM_NM'].astype(str)

    df_fetched['Item_Name'] = df_fetched['Item_Name'].str.replace('_생산자물가지수(품목별)', '', regex=False)
    df_fetched['DT'] = pd.to_numeric(df_fetched['DT'], errors='coerce')

    # 피벗 (최신 조사 품목 기준)
    df_new = df_fetched.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    current_items = df_new.index # 현재 유효한 품목 리스트
    print(f"✅ API로부터 {len(df_new)}개 품목 수신 완료")

    # --------------------------------------------------------------------------
    # 5. 기존 데이터와 병합 (삭제/추가 반영)
    # --------------------------------------------------------------------------
    if not os.path.exists(FILE_NAME):
        print("📂 기존 파일이 없어 새로 생성합니다.")
        df_final = df_new
    else:
        df_old = pd.read_csv(FILE_NAME, encoding='utf-8')
        df_old.set_index(df_old.columns[0], inplace=True)

        # [검토 핵심] 1. 사라진 품목 제거
        df_old_filtered = df_old.loc[df_old.index.isin(current_items)]
        removed_count = len(df_old) - len(df_old_filtered)
        if removed_count > 0:
            print(f"🗑️ 조사 제외된 {removed_count}개 품목 삭제 완료.")

        # [검토 핵심] 2. 병합 (신규 품목은 행 추가, 겹치는 값은 최신치로 갱신)
        df_final = df_new.combine_first(df_old_filtered)
        
        # [검토 핵심] 3. 최종적으로 현재 API 리스트에 있는 품목만 남김 (완벽 동기화)
        df_final = df_final.loc[df_final.index.isin(current_items)]

    # --------------------------------------------------------------------------
    # 6. 저장 및 검증
    # --------------------------------------------------------------------------
    df_final.index.name = '품목 / 시점'
    df_final = df_final.sort_index(axis=1) # 날짜순 정렬
    
    # 2026년 데이터 포함 여부 확인
    cols_2026 = [c for c in df_final.columns if str(c).startswith('2026')]
    if cols_2026:
        print(f"✨ 2026년 데이터 포함 성공: {cols_2026}")
    
    df_final.to_csv(FILE_NAME, encoding='utf-8-sig')
    print(f"💾 {FILE_NAME} 업데이트 완료! (최종 품목 수: {len(df_final)})")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    exit(1)
