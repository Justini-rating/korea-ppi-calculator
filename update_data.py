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
# 2. 날짜 계산
# --------------------------------------------------------------------------
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")
start_dt = now - relativedelta(months=3)
start_date = start_dt.strftime("%Y%m")

print(f"🔄 2026년 개편 대응 업데이트 시작 (항목 동기화 포함): {start_date} ~ {end_date}")

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
        print("ℹ️ 신규 데이터가 없습니다.")
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

    # 피벗 (최신 조사 품목 리스트 및 값)
    df_new = df_fetched.pivot_table(index='Item_Name', columns='PRD_DE', values='DT')
    current_items = df_new.index # 현재 유효한 품목 리스트
    print(f"✅ 신규 데이터 확보: {len(df_new)}개 품목")

    # --------------------------------------------------------------------------
    # 5. 기존 데이터와 병합 및 삭제 로직 반영
    # --------------------------------------------------------------------------
    if not os.path.exists(FILE_NAME):
        print("📂 기존 파일이 없어 새 파일을 생성합니다.")
        df_final = df_new
    else:
        df_old = pd.read_csv(FILE_NAME, encoding='utf-8')
        df_old.set_index(df_old.columns[0], inplace=True)

        # [수정 사항 1] 삭제된 품목 제거
        # 기존 데이터 중에서 현재 API 응답(current_items)에 없는 품목은 삭제합니다.
        removed_items = df_old.index.difference(current_items)
        df_old_filtered = df_old.loc[df_old.index.isin(current_items)]
        
        if not removed_items.empty:
            print(f"🗑️ 더 이상 조사되지 않는 {len(removed_items)}개 품목을 삭제합니다.")
            print(f"   (삭제 예시: {list(removed_items[:3])}...)")

        # [수정 사항 2] 병합 (신규 추가 품목 포함)
        # filtered된 기존 데이터와 신규 데이터를 합칩니다.
        df_final = df_new.combine_first(df_old_filtered)
        
        new_items = df_new.index.difference(df_old.index)
        if not new_items.empty:
            print(f"🆕 신규 추가된 {len(new_items)}개 품목을 반영했습니다.")

    # --------------------------------------------------------------------------
    # 6. 저장
    # --------------------------------------------------------------------------
    df_final.index.name = '품목 / 시점'
    df_final = df_final.sort_index(axis=1)
    
    # 2026년 데이터가 포함되었는지 확인 로그
    cols_2026 = [c for c in df_final.columns if str(c).startswith('2026')]
    if cols_2026:
        print(f"✨ 2026년 데이터 업데이트 성공: {cols_2026}")
    
    df_final.to_csv(FILE_NAME, encoding='utf-8-sig')
    print(f"💾 {FILE_NAME} 저장 완료! (총 {len(df_final)}개 품목)")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    exit(1)
