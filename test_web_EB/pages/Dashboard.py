import streamlit as st
import pandas as pd
import plotly.express as px

def run():
    # 페이지 제목
    st.title("📊 Noise Analysis Dashboard")

    st.write("🔍 **분석한 소음 데이터를 한눈에 확인하세요!** 📈")

    # 예제 데이터 (실제 데이터와 연동 가능)
    df = pd.DataFrame({
        "시간": ["10:00", "10:05", "10:10", "10:15", "10:20", "10:20"],
        "소음 크기 (dB)": [50, 65, 70, 85, 70, 50],
        "소음 유형": ["이륜차경적", "이륜차주행음", "차량경적", "차량사이렌", "차량주행음", "기타소음"]
    })

    # 소음 크기(dB) 변화를 시각화
    fig = px.line(df, x="시간", y="소음 크기 (dB)", markers=True, title="📊 소음 크기 변화 추이", color_discrete_sequence=pastel_colors)
    st.plotly_chart(fig)

    # 소음 유형별 데이터 개수 시각화
    fig_bar = px.bar(df, x="소음 유형", y="소음 크기 (dB)", color="소음 유형", title="🔊 소음 유형별 크기", color_discrete_sequence=pastel_colors)
    st.plotly_chart(fig_bar)