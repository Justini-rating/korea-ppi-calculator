import pandas as pd
import requests
import os
import datetime
import time  # 추가됨: 재시도 대기 시간을 위한 모듈
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

# [핵심 추가] 봇 차단을 피하기 위한 브라우저 위장 헤더
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

try:
    # [핵심 추가] 네트워크 오류 대비 최대 3번 재시도하는 로직 적용
    max_retries = 3
    data = None
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=60)
            response.raise_for_status()  # HTTP 에러 발생 시 예외 처리로 넘김
            data = response.json()
            break  # 정상적으로 응답받으면 반복문 탈출
        except requests.exceptions.RequestException as e:
            print(f"⚠️ API 호출 실패 ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("⏳ 5초 후 재시도합니다...")
                time.sleep(5)
            else:
                print("❌ 최종 실행 오류: KOSIS 서버 연결을 복구할 수 없습니다.")
                exit(1)

    # 응답 데이터 검증
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
    print(f"❌ 데이터 처리 중 오류 발생: {e}"); exit(1)
