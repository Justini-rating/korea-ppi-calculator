import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="PPI 상승률 계산기", page_icon="📈", layout="centered")

st.title("📈 국내생산자 물가지수 (품목별)")
st.markdown("매월 업데이트되는 KOSIS 데이터를 기반으로 **상승률 계산** 및 **추세 그래프**를 제공합니다.")

# 데이터 로드
@st.cache_data
def load_data():
    df = pd.read_csv("data.csv", encoding='utf-8') 
    if '품목 / 시점' in df.columns:
        df.set_index('품목 / 시점', inplace=True)
    else:
        df.set_index(df.columns[0], inplace=True)
    df = df.replace(',', '', regex=True)
    df = df.apply(pd.to_numeric, errors='coerce')
    return df

try:
    df = load_data()
    
    # 설정 (사이드바)
    st.sidebar.header("🔍 설정")
    item_list = df.index.tolist()
    default_index = item_list.index("총지수") if "총지수" in item_list else 0
    selected_item = st.sidebar.selectbox("품목 선택", item_list, index=default_index)

    date_list = df.columns.tolist()
    selected_past_date = st.sidebar.selectbox("비교할 과거 시점", date_list[::-1])
    latest_date = df.columns[-1]

    # 본문
    if selected_item and selected_past_date:
        past_value = df.loc[selected_item, selected_past_date]
        current_value = df.loc[selected_item, latest_date]
        
        if pd.isna(past_value) or pd.isna(current_value):
            st.error("데이터가 없습니다.")
        else:
            ratio = current_value / past_value
            percent_change = (ratio - 1) * 100
            
            st.subheader(f"📊 {selected_item} 분석 결과")
            col1, col2, col3 = st.columns(3)
            
            # 1. 과거 지수 (숫자 밑에 날짜)
            with col1:
                st.metric("과거 지수", f"{past_value}")
                st.caption(f"({selected_past_date})")
            
            # 2. 최신 지수 (숫자 밑에 날짜)
            with col2:
                st.metric("최신 지수", f"{current_value}")
                st.caption(f"({latest_date})")
                
            # 3. 상승률 (연두색, 화살표 없음)
            with col3:
                color_code = "#2ECC71" if percent_change >= 0 else "#FF4B4B"
                st.markdown('<p style="font-size: 14px; margin-bottom: -5px; color: #555;">상승률</p>', unsafe_allow_html=True)
                st.markdown(f'<p style="font-size: 32px; font-weight: 600; color: {color_code}; margin: 0;">{percent_change:+.2f}%</p>', unsafe_allow_html=True)
            
            st.divider()

            # 그래프
            st.subheader("📈 기간별 물가 변동 추이")
            chart_data = df.loc[selected_item]
            chart_data.index = pd.to_datetime(chart_data.index, format='%Y%m')
            st.line_chart(chart_data, color="#FF4B4B")

            # 상세 데이터 표 (최신순)
            with st.expander("📄 전체 데이터 표로 보기"):
                st.dataframe(df.loc[selected_item].to_frame().sort_index(ascending=False))

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
