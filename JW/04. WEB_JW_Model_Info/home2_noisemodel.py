import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.title("우리 도시 소음 프로젝트")

# 모델 설명 및 성능 표
st.markdown("""
### 우리 도시 소음 예측 모델
우리 도시 소음 프로젝트에서는 도시 환경에서 발생하는 소음을 예측하기 위해 **딥러닝 기반의 소음 분류 모델**을 개발했습니다.
""")

metrics = {"Metric": ["Accuracy", "Precision", "Recall", "F1-Score"], "Value": [0.92, 0.89, 0.91, 0.90]}
fig = go.Figure(data=[go.Table(
    header=dict(values=["<b>Metric</b>", "<b>Value</b>"], fill_color='#FF5E00', align='center', font=dict(color='white', size=14)),
    cells=dict(values=[metrics["Metric"], [f"{val:.2f}" for val in metrics["Value"]]], fill_color='#EAEAEA', align='center', font=dict(color='#333333', size=12), height=30)
)])
fig.update_layout(title="모델 성능 지표", title_x=0.5, width=500, height=300)
st.plotly_chart(fig)

# 훈련 데이터셋 통계
df = pd.read_csv("noise_dataset.csv")
tabs = st.tabs(["데이터셋 개요", "통계 시각화", "원본 데이터"])

with tabs[0]:
    st.markdown("### 훈련 데이터셋 개요")
    st.write(f"- **데이터 크기**: {df.shape[0]} 행, {df.shape[1]} 열")
    st.write(f"- **열 이름**: {', '.join(df.columns)}")

with tabs[1]:
    fig1 = px.histogram(df, x="noise_level", nbins=20, title="소음 레벨 분포", color_discrete_sequence=['#FF5E00'])
    st.plotly_chart(fig1)

with tabs[2]:
    st.dataframe(df.head(10))