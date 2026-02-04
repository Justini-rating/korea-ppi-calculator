import pandas as pd
import requests
import os
import datetime
import time

# --------------------------------------------------------------------------
# 1. 설정 (한국은행 생산자물가지수 - 품목별)
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301" # 한국은행
TBL_ID = "DT_404Y014" # 생산자물가지수(기본분류)

# --------------------------------------------------------------------------
# 2. 날짜 계산
# --------------------------------------------------------------------------
# 시작일 고정
start_date = "201901"

# 종료일: '오늘' 기준으로 설정 (미래 날짜 요청 시 에러 방지)
now = datetime.datetime.now()
end_date = now.strftime("%Y%m")

# --------------------------------------------------------------------------
# 3. KOSIS API 호출 (URL 수정됨)
# --------------------------------------------------------------------------
# 핵심 수정: 비어있는 objL2~8 파라미터를 아예 삭제했습니다.
# objL1=ALL : 대분류부터 세세한 품목까지 모두 가져오도록 시도
# 만약 데이터가 너무 많아 에러가 나면 objL1~objL5 등 레벨 조정이 필요할 수 있음
url = (
    f"https://kosis.kr/openapi/Param/statisticsParameterData.do"
    f"?method=getList&apiKey={API_KEY}"
    f"&itmId=T1"  # 지수
    f"&objL1=ALL" # 모든 분류 가져오기
    f"&objL2=ALL" # 하위 분류 포함 (필요시 추가)
    f"&objL3=ALL" # 더 하위 분류 포함
    f"&format=json&jsonVD=Y&prdSe=M&startPrdDe={start_date}&endPrdDe={end_date}"
    f"&orgId={ORG_ID}&tblId={TBL_ID}"
)

print(f"데이터 다운로드 시작... (기간: {start_date} ~ {end_date})")
print(f"요청 URL (키 숨김): {url.replace(API_KEY, '***')}")

try:
    response = requests.get(url)
    
    # 응답 확인
    if response.status_code != 200:
        print(f"서버 접속 오류: {response.status_code}")
        exit(1)

    data = response.json()

    # KOSIS 에러 메시지 감지
    if "err" in data:
        print(f"❌ API 오류 발생: {data}")
        exit(1)
        
    # --------------------------------------------------------------------------
    # 4. 데이터 가공
    # --------------------------------------------------------------------------
    df_raw = pd.DataFrame(data)
    print(f"다운로드 성공! 총 {len(df_raw)}개의 데이터 행을 가져왔습니다.")

    # 필요한 컬럼만 선택: C1_NM(품목명), PRD_DE(시점), DT(값)
    # 품목명이 C1_NM, C2_NM, C3_NM 중 가장 상세한 것에 있을 수 있음.
    # 보통 가장 마지막 분류명(C1~C3 중)을 품목명으로 씁니다.
    
    # 팁: 품목명이 들어있는 컬럼 찾기 (C1_NM, C2_NM, C3_NM 중 값이 있는 가장 마지막 컬럼)
    # 여기서는 간단히 'C1_NM'을 기준으로 하되, 데이터 구조에 따라 수정 가능
    # (API 결과에 따라 C1, C2, C3 등이 섞여 나옵니다)
    
    # 일단 'C1_NM' 사용 (기본) - 필요시 데이터 확인 후 'C3_NM' 등으로 변경
    target_col = 'C1_NM' 
    if 'C3_NM' in df_raw.columns:
        target_col = 'C3_NM'
    elif 'C2_NM' in df_raw.columns:
        target_col = 'C2_NM'
        
    df = df_raw[[target_col, 'PRD_DE', 'DT']].copy()
    df.columns = ['품목명', 'PRD_DE', 'DT'] # 컬럼명 통일
    
    # 숫자형 변환
    df['DT'] = pd.to_numeric(df['DT'])
    
    # 피벗 (행: 품목, 열: 시점, 값: 지수)
    df_pivot = df.pivot(index='품목명', columns='PRD_DE', values='DT')
    
    # 인덱스 이름 설정
    df_pivot.index.name = '품목 / 시점'
    
    # 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("✅ data.csv 업데이트 및 저장 완료!")

except Exception as e:
    print(f"❌ 처리 중 오류 발생: {e}")
    exit(1)
