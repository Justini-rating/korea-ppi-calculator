import streamlit as st
import pandas as pd

# --------------------------------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="PPI 상승률 계산기",
    page_icon="📈",
    layout="centered"
)

st.title("📈 생산자물가지수(PPI) 상승률 계산기")
st.markdown("매월 업데이트되는 KOSIS 데이터를 기반으로 **과거 시점 대비 물가 상승률**을 계산합니다.")

# --------------------------------------------------------------------------
# 2. 데이터 불러오기 함수 (엑셀/CSV 읽기)
# --------------------------------------------------------------------------
@st.cache_data  # 속도를 위해 데이터를 캐시(임시저장)해둡니다.
def load_data():
    # GitHub에 올릴 때는 파일명을 영어로 변경하는 것이 좋습니다 (예: ppi_data.csv)
    # 현재는 예시로 'data.csv'라고 가정합니다.
    df = pd.read_csv("data.csv", encoding='utf-8') 
    
    # '품목 / 시점' 컬럼을 인덱스(기준)로 설정
    if '품목 / 시점' in df.columns:
        df.set_index('품목 / 시점', inplace=True)
    else:
        # 혹시 컬럼명이 깨질 경우 첫번째 컬럼을 인덱스로 잡음
        df.set_index(df.columns[0], inplace=True)
    
    # 데이터 전처리: 쉼표(,) 제거 및 숫자로 변환
    df = df.replace(',', '', regex=True)
    df = df.apply(pd.to_numeric, errors='coerce')
    
    return df

# --------------------------------------------------------------------------
# 3. 화면 구현 및 계산 로직
# --------------------------------------------------------------------------
try:
    df = load_data()
    
    # (1) 최신 데이터 시점 확인 (가장 오른쪽 컬럼)
    latest_date = df.columns[-1]
    
    # (2) 품목 선택 (사이드바 또는 메인 화면)
    st.markdown("### 1️⃣ 품목 선택")
    item_list = df.index.tolist()
    # 기본값으로 '총지수'가 있다면 그것을, 아니면 첫 번째 항목을 선택
    default_index = item_list.index("총지수") if "총지수" in item_list else 0
    selected_item = st.selectbox("분석할 품목을 선택해주세요:", item_list, index=default_index)

    # (3) 기준 시점 선택
    st.markdown("### 2️⃣ 비교 기준 시점 선택")
    date_list = df.columns.tolist()
    # 최신 날짜부터 거꾸로 보여주기
    selected_past_date = st.selectbox("언제와 비교하시겠습니까?", date_list[::-1])

    # (4) 구분선
    st.divider()

    # (5) 결과 계산 및 출력
    if selected_item and selected_past_date:
        # 데이터 추출
        past_value = df.loc[selected_item, selected_past_date]
        current_value = df.loc[selected_item, latest_date]
        
        # 값이 없는 경우(NaN) 처리
        if pd.isna(past_value) or pd.isna(current_value):
            st.error(f"⚠️ 선택하신 시점({selected_past_date})에는 데이터가 없습니다.")
        else:
            # 엑셀의 수식 구현: (현시점 / 과거시점)
            ratio = current_value / past_value
            # 퍼센트 변화율: (비율 - 1) * 100
            percent_change = (ratio - 1) * 100
            
            st.subheader(f"📊 분석 결과: {selected_item}")
            
            # 보기 좋게 3개 컬럼으로 나열
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("과거 지수", f"{past_value}", f"{selected_past_date} 기준")
            with col2:
                st.metric("최신 지수", f"{current_value}", f"{latest_date} 기준")
            with col3:
                # 상승이면 빨간색, 하락이면 파란색으로 자동 표시됨
                st.metric("상승률(배수)", f"{ratio:.4f} 배", f"{percent_change:+.2f}%")
            
            # 최종 문장 출력
            st.info(f"""
            **{selected_item}**의 물가는 **{selected_past_date}** 대비 
            약 **{ratio:.3f}배** ({percent_change:+.2f}%) 변동되었습니다.
            """)

except FileNotFoundError:
    st.warning("⚠️ 'data.csv' 파일이 없습니다. 엑셀 파일을 'data.csv'로 저장해서 같은 폴더에 넣어주세요.")
except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")