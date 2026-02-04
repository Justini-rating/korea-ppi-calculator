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
TBL_ID = "DT_404Y016"       # 생산자물가지수 (품목별)
ITM_ID = "13103134764999"   # 항목 ID

FILE_NAME = "data.csv"

# --------------------------------------------------------------------------
# 2. 날짜 계산 (최근 3개월만 조회하여 40,000셀 에러 회피)
# --------------------------------------------------------------------------
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")

# 검증을 위해 '지난달'과 '지지난달'도 포함해서 최근 3~4개월치를 가져옵니다.
# 이렇게 하면 기존 데이터와 겹치는 부분이 생겨서 제대로 매칭되는지 확인할 수 있습니다.
start_dt = now - relativedelta(months=3)
start_date = start_dt.strftime("%Y%m")

print(f"🔄 스마트 업데이트 시작: {start_date} ~ {end_date} 데이터만 요청합니다.")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출
# --------------------------------------------------------------------------
url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
params = {
    "method": "getList",
    "apiKey": API_KEY,
    "itmId": ITM_ID,
    "objL1": "ALL",
    "objL2": "", 
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

try:
    response = requests.get(url, params=params, timeout=60)
    data = response.json()
    
    if isinstance(data, dict) and 'err' in data:
        print(f"❌ API 오류: {data.get('errMsg')}")
        exit(1)
        
    if not data:
        print("⚠️ 신규 데이터가 없거나 서버 응답이 비어있습니다.")
        exit(0) # 에러는 아니므로 정상 종료

    # --------------------------------------------------------------------------
    # 4. 신규 데이터 가공 (df_new)
    # --------------------------------------------------------------------------
    df_fetched = pd.DataFrame(data)
    
    # 품목명 생성 (C1_NM + ITM_NM)
    if 'C1_NM' in df_fetched.columns:
        df_fetched['Item_Name'] = df_fetched['C1_NM'].astype(str) + "_" + df_fetched['ITM_NM'].astype(str)
    else:
        df_fetched['Item_Name'] = df_fetched['ITM_NM'].astype(str)

    df_fetched['Item_Name'] = df_fetched['Item_Name'].str.replace('_생산자물가지수(품목별)', '', regex=False)
    df_fetched['DT'] = pd.to_numeric(df_fetched['DT'], errors='coerce')

    # 피벗 (새로운 데이터셋)
    df_new = df_fetched.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    print(f"✅ 신규 데이터 확보: {len(df_new)}개 품목, 기간: {df_new.columns.tolist()}")

    # --------------------------------------------------------------------------
    # 5. [핵심] 기존 데이터와 병합 (Validation & Merge)
    # --------------------------------------------------------------------------
    if not os.path.exists(FILE_NAME):
        print("📂 기존 파일이 없습니다. 새로 생성합니다.")
        df_final = df_new
    else:
        print("📂 기존 data.csv를 읽어와서 병합을 시도합니다...")
        # 기존 데이터 로드 (인덱스를 '품목 / 시점'으로 지정하지 않고 일단 읽음)
        df_old = pd.read_csv(FILE_NAME, encoding='utf-8')
        
        # 인덱스 설정 (기존 파일의 첫 번째 컬럼이 품목명이라고 가정)
        if '품목 / 시점' in df_old.columns:
            df_old.set_index('품목 / 시점', inplace=True)
        else:
            df_old.set_index(df_old.columns[0], inplace=True)

        # 1) 검증: 행(품목)이 제대로 매칭되는지 확인
        # df_old와 df_new의 인덱스(품목명) 교집합 확인
        common_items = df_old.index.intersection(df_new.index)
        print(f"🔎 매칭 검증: 기존 {len(df_old)}개 중 {len(common_items)}개 품목이 신규 데이터와 일치합니다.")
        
        if len(common_items) == 0:
            print("❌ [경고] 기존 데이터와 품목명이 하나도 일치하지 않습니다! 병합을 중단합니다.")
            # 데이터 구조가 완전히 바뀌었거나 파일이 꼬인 경우 방어
            exit(1)

        # 2) 업데이트 (병합) 로직
        # 방식: 기존 데이터(df_old)를 유지하되, df_new에 있는 날짜(컬럼)가 있으면 덮어쓰거나 추가함
        
        # (A) 기존에 없던 새로운 '달(Month)' 컬럼 추가
        new_months = [col for col in df_new.columns if col not in df_old.columns]
        
        if new_months:
            print(f"🆕 새로운 업데이트 발견! 추가될 기간: {new_months}")
            # df_new에서 새로운 달만 잘라내어 df_old에 붙임 (인덱스 기준 자동 매칭)
            df_final = df_old.join(df_new[new_months])
        else:
            print("ℹ️ 새로운 날짜 데이터는 없습니다. (기존 데이터 값만 최신으로 갱신합니다)")
            df_final = df_old.copy()

        # (B) 겹치는 기간(최근 3개월)의 데이터 최신화 (Update)
        # 혹시 통계청에서 수치를 정정한 경우를 대비해 겹치는 기간은 신규 데이터로 덮어씁니다.
        common_months = [col for col in df_new.columns if col in df_old.columns]
        if common_months:
            df_final.update(df_new[common_months])
    
    # --------------------------------------------------------------------------
    # 6. 저장
    # --------------------------------------------------------------------------
    df_final.index.name = '품목 / 시점'
    
    # 날짜(컬럼) 기준 정렬 (옛날 -> 최신)
    # 컬럼명이 숫자(202301) 문자열이므로 정렬 가능
    df_final = df_final.sort_index(axis=1)
    
    df_final.to_csv(FILE_NAME, encoding='utf-8-sig')
    print("💾 data.csv 업데이트 및 저장 완료! (증분 업데이트 성공)")

except Exception as e:
    print(f"❌ 실행 중 오류 발생: {e}")
    exit(1)
