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

st.title("📈 국내생산자 물가지수 (품목별)")
st.markdown("매월 업데이트되는 KOSIS 데이터를 기반으로 **상승률 계산** 및 **추세 그래프**를 제공합니다.")

# --------------------------------------------------------------------------
# 2. 데이터 불러오기 함수
# --------------------------------------------------------------------------
@st.cache_data
def load_data():
    # CSV 파일 읽기
    df = pd.read_csv("data.csv", encoding='utf-8') 
    
    # '품목 / 시점' 컬럼을 인덱스로 설정
    if '품목 / 시점' in df.columns:
        df.set_index('품목 / 시점', inplace=True)
    else:
        df.set_index(df.columns[0], inplace=True)
    
    # 데이터 전처리 (콤마 제거 및 숫자 변환)
    df = df.replace(',', '', regex=True)
    df = df.apply(pd.to_numeric, errors='coerce')
    
    return df

# --------------------------------------------------------------------------
# 3. 화면 구현
# --------------------------------------------------------------------------
try:
    df = load_data()
    
    # 사이드바에서 품목 선택하게 변경 (공간 활용을 위해)
    st.sidebar.header("🔍 설정")
    
    item_list = df.index.tolist()
    default_index = item_list.index("총지수") if "총지수" in item_list else 0
    selected_item = st.sidebar.selectbox("품목 선택", item_list, index=default_index)

    # 기준 시점 선택
    date_list = df.columns.tolist()
    selected_past_date = st.sidebar.selectbox("비교할 과거 시점", date_list[::-1]) # 최신순

    latest_date = df.columns[-1]

    # 본문 시작
    if selected_item and selected_past_date:
        # ------------------------------------------------------------------
        # (1) 핵심 지표 (Metric) 표시
        # ------------------------------------------------------------------
        past_value = df.loc[selected_item, selected_past_date]
        current_value = df.loc[selected_item, latest_date]
        
        if pd.isna(past_value) or pd.isna(current_value):
            st.error("데이터가 비어있어 계산할 수 없습니다.")
        else:
            ratio = current_value / past_value
            percent_change = (ratio - 1) * 100
            
            st.subheader(f"📊 {selected_item} 분석 결과")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("과거 지수", f"{past_value}", f"{selected_past_date}")
            with col2:
                st.metric("최신 지수", f"{current_value}", f"{latest_date}")
            with col3:
                st.metric("상승률", f"{ratio:.4f} 배", f"{percent_change:+.2f}%")
            
            st.divider() # 구분선

            # ------------------------------------------------------------------
            # (2) 그래프 그리기 (New!)
            # ------------------------------------------------------------------
            st.subheader("📈 기간별 물가 변동 추이")
            
            # 그래프를 위해 데이터 가공 (행: 날짜, 열: 지수값)
            chart_data = df.loc[selected_item]
            
            # 인덱스(201901 등 문자열)를 날짜 형식으로 변환 -> 그래프 X축이 예뻐짐
            chart_data.index = pd.to_datetime(chart_data.index, format='%Y%m')
            
            # 선 그래프 그리기 (Streamlit 내장 함수)
            st.line_chart(chart_data, color="#FF4B4B") # 색상은 빨간 계열

            # 상세 데이터 보기 (접기/펴기 기능)
            with st.expander("📄 전체 데이터 표로 보기"):
                st.dataframe(df.loc[selected_item].T)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")



