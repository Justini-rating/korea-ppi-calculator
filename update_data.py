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
# 2. 날짜 계산 (최근 3개월만 조회 -> 가볍고 빠름)
# --------------------------------------------------------------------------
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")

# 지난달, 지지난달 포함 3개월치 요청 (수정된 데이터 반영 및 검증용)
start_dt = now - relativedelta(months=3)
start_date = start_dt.strftime("%Y%m")

print(f"🔄 월간 업데이트 모드 가동: {start_date} ~ {end_date}")

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
        print("ℹ️ 아직 이번 달 신규 데이터가 발표되지 않았습니다.")
        exit(0) # 에러 아님, 정상 종료

    # --------------------------------------------------------------------------
    # 4. 신규 데이터 가공 (규칙 통일)
    # --------------------------------------------------------------------------
    df_fetched = pd.DataFrame(data)
    
    # (1) 품목명 생성 (C1_NM + ITM_NM)
    if 'C1_NM' in df_fetched.columns:
        df_fetched['Item_Name'] = df_fetched['C1_NM'].astype(str) + "_" + df_fetched['ITM_NM'].astype(str)
    else:
        df_fetched['Item_Name'] = df_fetched['ITM_NM'].astype(str)

    # (2) [핵심] 기존 파일과 똑같이 꼬리표 제거! (매칭을 위해 필수)
    df_fetched['Item_Name'] = df_fetched['Item_Name'].str.replace('_생산자물가지수(품목별)', '', regex=False)
    
    # 숫자형 변환
    df_fetched['DT'] = pd.to_numeric(df_fetched['DT'], errors='coerce')

    # 피벗 (새로운 데이터셋)
    df_new = df_fetched.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    print(f"✅ 신규 데이터 확보: {len(df_new)}개 품목")

    # --------------------------------------------------------------------------
    # 5. 기존 데이터와 병합 (Smart Merge)
    # --------------------------------------------------------------------------
    if not os.path.exists(FILE_NAME):
        print("📂 기존 파일이 없어서 새 파일로 저장합니다.")
        df_final = df_new
    else:
        print("📂 기존 data.csv에 업데이트를 반영합니다...")
        # 기존 데이터 로드
        df_old = pd.read_csv(FILE_NAME, encoding='utf-8')
        
        # 인덱스 설정
        if '품목 / 시점' in df_old.columns:
            df_old.set_index('품목 / 시점', inplace=True)
        else:
            df_old.set_index(df_old.columns[0], inplace=True)

        # [검증] 이름이 같은지 확인
        common = df_old.index.intersection(df_new.index)
        print(f"🔎 매칭 확인: {len(common)}개 품목이 일치합니다. (정상)")
        
        # 1) 겹치는 기간(최근 3개월) 값 갱신 (Update)
        # 통계청에서 값을 정정한 경우 반영됨
        df_final = df_old.copy()
        df_final.update(df_new)
        
        # 2) 새로운 기간(Month) 추가 (Append Columns)
        new_months = [col for col in df_new.columns if col not in df_old.columns]
        if new_months:
            print(f"🆕 새로운 달({new_months}) 데이터가 추가됩니다!")
            # join을 사용하여 새로운 열을 붙임
            df_final = df_final.join(df_new[new_months])
        else:
            print("ℹ️ 새로운 달은 없습니다. (기존 값만 최신화)")

    # --------------------------------------------------------------------------
    # 6. 저장
    # --------------------------------------------------------------------------
    df_final.index.name = '품목 / 시점'
    
    # 날짜순 정렬
    df_final = df_final.sort_index(axis=1)
    
    df_final.to_csv(FILE_NAME, encoding='utf-8-sig')
    print(f"💾 {FILE_NAME} 업데이트 완료! (최종 데이터 기준: {df_final.columns[-1]})")

except Exception as e:
    print(f"❌ 실행 중 오류 발생: {e}")
    exit(1)
