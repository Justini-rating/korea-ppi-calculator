import pandas as pd
import requests
import os
import datetime

# --------------------------------------------------------------------------
# 1. 설정
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"        # 한국은행
TBL_ID = "DT_404Y014" # 생산자물가지수(기본분류)

# --------------------------------------------------------------------------
# 2. 날짜 계산
# --------------------------------------------------------------------------
start_date = "201901"
end_date = datetime.datetime.now().strftime("%Y%m")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출
# --------------------------------------------------------------------------
# [핵심] 오류 원인인 objL2, objL3 제거하고 objL1(품목)만 남김
url = (
    f"https://kosis.kr/openapi/Param/statisticsParameterData.do"
    f"?method=getList&apiKey={API_KEY}"
    f"&itmId=T1"           # 데이터 종류 (지수)
    f"&objL1=ALL"          # 모든 품목 가져오기
    f"&format=json&jsonVD=Y&prdSe=M&startPrdDe={start_date}&endPrdDe={end_date}"
    f"&orgId={ORG_ID}&tblId={TBL_ID}"
)

print(f"데이터 다운로드 시작... (기간: {start_date} ~ {end_date})")

try:
    response = requests.get(url, timeout=30)
    
    if response.status_code != 200:
        print(f"서버 접속 오류: {response.status_code}")
        exit(1)

    data = response.json()

    # 에러 체크
    if "err" in data:
        print(f"❌ API 오류 발생: {data}")
        exit(1)
        
    # --------------------------------------------------------------------------
    # 4. 데이터 가공
    # --------------------------------------------------------------------------
    df_raw = pd.DataFrame(data)
    print(f"다운로드 성공! 총 {len(df_raw)}개 데이터를 가져왔습니다.")

    # 컬럼 정리 (품목명 찾기)
    item_col = 'C1_NM'
    if item_col not in df_raw.columns:
        # 만약 C1_NM이 없으면 C2, C3 등을 찾음
        for col in ['C2_NM', 'C3_NM', 'ITM_NM']:
            if col in df_raw.columns:
                item_col = col
                break
                
    df = df_raw[[item_col, 'PRD_DE', 'DT']].copy()
    df.columns = ['품목명', 'PRD_DE', 'DT']
    
    # 숫자형 변환 및 피벗
    df['DT'] = pd.to_numeric(df['DT'], errors='coerce')
    df_pivot = df.pivot(index='품목명', columns='PRD_DE', values='DT')
    df_pivot.index.name = '품목 / 시점'
    
    # 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("✅ data.csv 업데이트 완료!")

except Exception as e:
    print(f"❌ 오류: {e}")
    exit(1)
