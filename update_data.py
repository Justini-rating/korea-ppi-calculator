import pandas as pd
import requests
import os
import datetime

# --------------------------------------------------------------------------
# 1. 설정 (한국은행 생산자물가지수 - 기본분류)
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"        # 한국은행
TBL_ID = "DT_404Y014" # 생산자물가지수(기본분류)

# --------------------------------------------------------------------------
# 2. 날짜 계산
# --------------------------------------------------------------------------
# 시작일 고정
start_date = "201901"

# 종료일: '오늘' 기준으로 설정 (미래 날짜 에러 방지)
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출 (수정됨: 불필요한 파라미터 삭제)
# --------------------------------------------------------------------------
# 핵심 수정: objL2, objL3 등을 모두 제거하고 objL1(품목)만 남김
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

    # KOSIS 에러 체크
    if "err" in data:
        print(f"❌ API 오류 발생: {data}")
        exit(1)
        
    # --------------------------------------------------------------------------
    # 4. 데이터 가공
    # --------------------------------------------------------------------------
    df_raw = pd.DataFrame(data)
    print(f"다운로드 성공! 총 {len(df_raw)}개 데이터를 가져왔습니다.")

    # 필요한 컬럼만 선택
    # C1_NM: 품목명 (예: 쌀, TV 등)
    # PRD_DE: 시점 (202301)
    # DT: 값 (지수)
    
    # 간혹 컬럼명이 다를 수 있어 확인 후 처리
    item_col = 'C1_NM'
    if item_col not in df_raw.columns:
        print("⚠️ 품목 컬럼(C1_NM)을 찾을 수 없습니다. 데이터 구조를 확인하세요.")
        print("컬럼 목록:", df_raw.columns)
        exit(1)
        
    df = df_raw[[item_col, 'PRD_DE', 'DT']].copy()
    df.columns = ['품목명', 'PRD_DE', 'DT'] # 알기 쉽게 변경
    
    # 숫자형 변환
    df['DT'] = pd.to_numeric(df['DT'], errors='coerce')
    
    # 피벗 (행: 품목, 열: 시점, 값: 지수)
    df_pivot = df.pivot(index='품목명', columns='PRD_DE', values='DT')
    
    # 인덱스 이름 설정 (엑셀 파일과 통일)
    df_pivot.index.name = '품목 / 시점'
    
    # CSV 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("✅ data.csv 업데이트 및 저장 완료!")

except Exception as e:
    print(f"❌ 처리 중 치명적 오류 발생: {e}")
    exit(1)
