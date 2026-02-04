import pandas as pd
import requests
import os
import datetime
import time

# --------------------------------------------------------------------------
# 1. 설정
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"
TBL_ID = "DT_404Y016"       # 생산자물가지수 (품목별)
ITM_ID = "13103134764999"   # 항목 ID (지수)

FILE_NAME = "data.csv"

# --------------------------------------------------------------------------
# 2. 함수: 1년치 데이터 가져오기
# --------------------------------------------------------------------------
def fetch_kosis_data(start_ym, end_ym):
    print(f"   📡 데이터 요청: {start_ym} ~ {end_ym} ...", end=" ")
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
        "startPrdDe": start_ym,
        "endPrdDe": end_ym
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        data = response.json()
        
        # 에러 체크
        if isinstance(data, dict) and 'err' in data:
            print(f"❌ 실패 ({data.get('errMsg')})")
            return None
        
        if not data:
            print("⚠️ 데이터 없음")
            return None
            
        print(f"✅ 성공 ({len(data)}건)")
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"❌ 에러 ({e})")
        return None

# --------------------------------------------------------------------------
# 3. 메인 로직: 2019년부터 연도별 루프
# --------------------------------------------------------------------------
print("🔄 전체 데이터 새로 받기 시작 (꼬리표 제거 모드)")

now = datetime.datetime.now()
current_year = now.year
current_month = now.month

# 2019년부터 시작
start_year = 2019

all_data_frames = []

for year in range(start_year, current_year + 1):
    # 시작월
    s_date = f"{year}01"
    
    # 종료월 계산
    if year == current_year:
        e_date = now.strftime("%Y%m") # 올해는 오늘 날짜까지
    else:
        e_date = f"{year}12"          # 과거는 12월까지 꽉 채워서
        
    # 미래 날짜 요청 방지
    if int(s_date) > int(now.strftime("%Y%m")):
        break
        
    # 데이터 요청
    df_part = fetch_kosis_data(s_date, e_date)
    
    if df_part is not None and not df_part.empty:
        all_data_frames.append(df_part)
    
    # 서버에 부담 주지 않게 1초 휴식
    time.sleep(1)

# --------------------------------------------------------------------------
# 4. 데이터 병합 및 꼬리표 제거
# --------------------------------------------------------------------------
if not all_data_frames:
    print("❌ 수집된 데이터가 없습니다. 종료합니다.")
    exit(1)

print("🧩 데이터 병합 및 이름 정리 중...")
df_total = pd.concat(all_data_frames, ignore_index=True)

# (1) 품목명 생성: C1_NM + "_" + ITM_NM
# 예: 쌀 + "_" + 지수 -> "쌀_지수" (혹은 ITM_NM이 '생산자물가지수(품목별)'일 수 있음)
if 'C1_NM' in df_total.columns:
    df_total['Item_Name'] = df_total['C1_NM'].astype(str) + "_" + df_total['ITM_NM'].astype(str)
else:
    df_total['Item_Name'] = df_total['ITM_NM'].astype(str)

# (2) [핵심] 꼬리표 떼기!
# "_생산자물가지수(품목별)" 이라는 글자가 있으면 삭제해버림
df_total['Item_Name'] = df_total['Item_Name'].str.replace('_생산자물가지수(품목별)', '', regex=False)

# 숫자형 변환
df_total['DT'] = pd.to_numeric(df_total['DT'], errors='coerce')

# (3) 중복 제거 및 피벗
# 혹시 모를 중복 데이터 제거
df_total = df_total.drop_duplicates(subset=['Item_Name', 'PRD_DE'])

# 피벗 (행: 품목명, 열: 날짜, 값: 지수)
df_pivot = df_total.pivot(index='Item_Name', columns='PRD_DE', values='DT')

# 인덱스 이름 설정
df_pivot.index.name = '품목 / 시점'

# 날짜순 정렬 (201901 -> 202602)
df_pivot = df_pivot.sort_index(axis=1)

# --------------------------------------------------------------------------
# 5. 저장
# --------------------------------------------------------------------------
df_pivot.to_csv(FILE_NAME, encoding='utf-8-sig')
print(f"💾 {FILE_NAME} 저장 완료! (총 {len(df_pivot)}개 품목)")
print(f"   예시 품목명: {df_pivot.index[0]}") # 이름 잘 바뀌었는지 로그로 확인
