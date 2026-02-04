import pandas as pd
import requests
import os
import datetime

# --------------------------------------------------------------------------
# 1. 설정 (한국은행 생산자물가지수 - 품목별)
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY") # GitHub Secrets에서 가져옴
ORG_ID = "301" # 한국은행
TBL_ID = "DT_404Y014" # 생산자물가지수(품목별)

# --------------------------------------------------------------------------
# 2. 날짜 계산 (2019.01 ~ 현재)
# --------------------------------------------------------------------------
# 시작일은 201901로 고정 (필요시 수정)
start_date = "201901"

# 종료일은 넉넉하게 '다음 달'로 설정 (KOSIS가 알아서 최신 데이터까지만 줌)
now = datetime.datetime.now()
end_date = (now + datetime.timedelta(days=30)).strftime("%Y%m")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출
# --------------------------------------------------------------------------
url = (
    f"https://kosis.kr/openapi/Param/statisticsParameterData.do"
    f"?method=getList&apiKey={API_KEY}"
    f"&itmId=T1&objL1=ALL&objL2=&objL3=&objL4=&objL5=&objL6=&objL7=&objL8="
    f"&format=json&jsonVD=Y&prdSe=M&startPrdDe={start_date}&endPrdDe={end_date}"
    f"&orgId={ORG_ID}&tblId={TBL_ID}"
)

print(f"데이터 다운로드 중... (기간: {start_date} ~ {end_date})")

try:
    response = requests.get(url)
    data = response.json()

    if "err" in data:
        print("API 오류:", data)
        exit(1)
        
    # --------------------------------------------------------------------------
    # 4. 데이터 가공 (Long Format -> Wide Format)
    # --------------------------------------------------------------------------
    df_raw = pd.DataFrame(data)
    
    # 필요한 컬럼만 선택: C1_NM(품목명), PRD_DE(시점), DT(값)
    df = df_raw[['C1_NM', 'PRD_DE', 'DT']].copy()
    
    # 숫자형 변환
    df['DT'] = pd.to_numeric(df['DT'])
    
    # 피벗 (행: 품목, 열: 시점, 값: 지수)
    df_pivot = df.pivot(index='C1_NM', columns='PRD_DE', values='DT')
    
    # 인덱스 이름 설정
    df_pivot.index.name = '품목 / 시점'
    
    # 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("✅ data.csv 업데이트 완료!")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    # 오류 나면 기존 파일 보호를 위해 강제 종료
    exit(1)
