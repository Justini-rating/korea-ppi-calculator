import pandas as pd
import requests
import os
import datetime
import time

# --------------------------------------------------------------------------
# 1. 설정
# --------------------------------------------------------------------------
API_KEY = os.environ.get("KOSIS_API_KEY")
ORG_ID = "301"        # 한국은행
TBL_ID = "DT_404Y014" # 생산자물가지수(기본분류)
START_DATE = "201901"
END_DATE = datetime.datetime.now().strftime("%Y%m")

def get_kosis_data(params):
    """KOSIS API를 호출하는 함수"""
    base_url = "https://kosis.kr/openapi/Param/statisticsParameterData.do"
    # 기본 필수 파라미터
    default_params = {
        "method": "getList",
        "apiKey": API_KEY,
        "format": "json",
        "jsonVD": "Y",
        "prdSe": "M",
        "startPrdDe": START_DATE,
        "endPrdDe": END_DATE,
        "orgId": ORG_ID,
        "tblId": TBL_ID
    }
    # 입력받은 파라미터 병합
    final_params = {**default_params, **params}
    
    print(f"📡 요청 시도: {params}")
    try:
        response = requests.get(base_url, params=final_params, timeout=30)
        if response.status_code != 200:
            return False, f"서버 오류 ({response.status_code})"
            
        data = response.json()
        if "err" in data:
            return False, data['errMsg']
            
        return True, data
    except Exception as e:
        return False, str(e)

# --------------------------------------------------------------------------
# 2. 스마트 탐색 시작
# --------------------------------------------------------------------------
print("🔍 통계청 서버 접속 및 분류 체계 탐색 중...")

# [Step 1] 분류(objL1) 없이 '항목(itmId=T1)'만 요청해보기 (총지수 확인)
# 만약 여기서 성공하면, 이 통계표는 objL1 대신 다른 변수명을 쓴다는 뜻입니다.
success, result = get_kosis_data({"itmId": "T1"})

if not success:
    print(f"❌ 1단계 실패: {result}")
    print("⚠️ 'itmId=T1'이 틀렸을 가능성이 높습니다. KOSIS 공유서비스에서 URL을 확인해야 합니다.")
    exit(1)

print("✅ 1단계 성공! 기본 데이터 수신 완료. 이제 상세 분류를 찾습니다.")
df_sample = pd.DataFrame(result)

# [Step 2] 데이터에서 '분류 변수명' 찾기 (C1_NM, C2_NM 등)
# 통계청 데이터에는 C1, C2, C3 등의 컬럼에 분류 정보가 들어있습니다.
target_obj_var = None
for col in ['objL1', 'objL2', 'objL3', 'objL4', 'objL5']: # URL 파라미터 후보
    # (주의) 여기서는 단순 매핑이 아니라, 실제로는 URL 파라미터가 objL1~8로 정해져 있습니다.
    # 하지만 21번 에러가 났던 건 'objL1=ALL'이 안 먹혔기 때문입니다.
    pass

# 전략 수정: 1단계에서 데이터를 받았다는 건, '총지수' 데이터가 왔다는 뜻입니다.
# 하지만 우리는 '품목별'이 필요하죠. 
# KOSIS 규칙상 objL1=ALL을 넣어야 하위 분류가 나옵니다.
# 그런데 아까 에러가 났으니, objL1 말고 objL2 등을 써야 할 수도 있습니다.

# [Step 3] 재시도: objL1~objL5까지 'ALL'을 넣어가며 맞는 열쇠 찾기
final_df = None

# 후보군: 보통 objL1이지만, 안되면 objL2, objL3... 순서대로 시도
candidates = ["objL1", "objL2", "objL3", "objL4"]

for var_name in candidates:
    print(f"🔄 '{var_name}=ALL'로 전체 데이터 요청 시도 중...")
    success, result = get_kosis_data({"itmId": "T1", var_name: "ALL"})
    
    if success:
        print(f"🎉 성공! 올바른 분류 변수는 '{var_name}'였습니다.")
        final_df = pd.DataFrame(result)
        break
    else:
        print(f"   -> 실패 ({result}). 다음 후보 시도...")

# --------------------------------------------------------------------------
# 3. 데이터 저장
# --------------------------------------------------------------------------
if final_df is None:
    print("❌ 모든 시도가 실패했습니다. (총지수는 불러와지지만, 품목별 상세 호출 실패)")
    # 실패 시 총지수(1단계 데이터)라도 저장할지, 아니면 종료할지 결정
    # 여기서는 1단계 데이터(df_sample)라도 저장해서 사이트가 꺼지지 않게 방어합니다.
    print("⚠️ 대신 '총지수' 데이터만이라도 저장하여 사이트 오류를 방지합니다.")
    final_df = df_sample

# 컬럼 정리 및 저장
print("💾 데이터 가공 및 저장 중...")

# 품목명 컬럼 찾기 (C1_NM, C2_NM 등 값이 있는 컬럼)
item_col = 'C1_NM' # 기본값
for col in ['C1_NM', 'C2_NM', 'C3_NM', 'ITM_NM']:
    if col in final_df.columns:
        # 해당 컬럼의 데이터가 1개 이상이고 다양하다면 채택
        if final_df[col].nunique() > 1:
            item_col = col
            break

# 필요한 컬럼만 추출
try:
    df = final_df[[item_col, 'PRD_DE', 'DT']].copy()
    df.columns = ['품목명', 'PRD_DE', 'DT']
    
    # 숫자 변환
    df['DT'] = pd.to_numeric(df['DT'], errors='coerce')
    
    # 피벗
    df_pivot = df.pivot(index='품목명', columns='PRD_DE', values='DT')
    df_pivot.index.name = '품목 / 시점'
    
    # CSV 저장
    df_pivot.to_csv("data.csv", encoding='utf-8-sig')
    print("✅ data.csv 업데이트 완료! (웹사이트에 곧 반영됩니다)")
    
except Exception as e:
    print(f"❌ 데이터 가공 중 오류: {e}")
    # 디버깅을 위해 컬럼 목록 출력
    print(f"현재 데이터 컬럼: {final_df.columns}")
    exit(1)
