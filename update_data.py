import pandas as pd
import requests
import os
import datetime
from dateutil.relativedelta import relativedelta

# 설정
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"
TBL_ID = "DT_404Y016"  # 생산자물가지수 (품목별)
ITM_ID = "13103134764999"
FILE_NAME = "data.csv"

# 1. 날짜 설정 (최근 3개월 데이터 요청)
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")
start_date = (now - relativedelta(months=3)).strftime("%Y%m")

print(f"🚀 2026 개편 대응 동기화 가동: {start_date} ~ {end_date}")

# 2. KOSIS API 호출
url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
params = {
    "method": "getList", "apiKey": API_KEY, "itmId": ITM_ID,
    "objL1": "ALL", "format": "json", "jsonVD": "Y", "prdSe": "M",
    "orgId": ORG_ID, "tblId": TBL_ID, "startPrdDe": start_date, "endPrdDe": end_date
}

try:
    response = requests.get(url, params=params, timeout=60)
    data = response.json()
    
    if isinstance(data, dict) and 'err' in data:
        print(f"❌ API 오류: {data.get('errMsg')}"); exit(1)
    if not data:
        print("ℹ️ 신규 데이터가 아직 발표되지 않았습니다."); exit(0)

    # 3. 데이터 가공
    df_fetched = pd.DataFrame(data)
    df_fetched['Item_Name'] = (df_fetched['C1_NM'].astype(str) + "_" + df_fetched['ITM_NM'].astype(str)).str.replace('_생산자물가지수(품목별)', '', regex=False)
    df_fetched['DT'] = pd.to_numeric(df_fetched['DT'], errors='coerce')
    
    # 최신 품목 리스트 및 값 피벗
    df_new = df_fetched.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    current_items = df_new.index

    # 4. 스마트 병합 (삭제된 행은 지우고, 신규 행은 추가)
    if os.path.exists(FILE_NAME):
        df_old = pd.read_csv(FILE_NAME, index_col=0, encoding='utf-8')
        
        # [핵심] 현재 API 응답에 있는 품목만 남기고 나머지는 과감히 삭제 (동기화)
        df_old_filtered = df_old[df_old.index.isin(current_items)]
        
        # [핵심] 신규 데이터와 합치기 (새로운 품목은 행이 추가됨)
        df_final = df_new.combine_first(df_old_filtered)
        
        # 한 번 더 필터링 (완벽한 동기화)
        df_final = df_final.loc[df_final.index.isin(current_items)]
    else:
        df_final = df_new

    # 5. 저장
    df_final.index.name = '품목 / 시점'
    df_final.sort_index(axis=1).to_csv(FILE_NAME, encoding='utf-8-sig')
    print(f"✅ {FILE_NAME} 업데이트 완료! (최종 품목: {len(df_final)}개)")

except Exception as e:
    print(f"❌ 실행 오류: {e}"); exit(1)
