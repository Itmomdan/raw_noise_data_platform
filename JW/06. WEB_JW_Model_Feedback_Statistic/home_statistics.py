import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime, timedelta

class Statistics_page:
    def statistics_page(self):
        st.subheader('통계 분석')
        st.markdown("<p style='color: gray;'>* 실제 사용자 데이터가 없어 더미 데이터로 구현된 예시입니다.</p>", unsafe_allow_html=True)

        # 더미 데이터 생성 함수 (소음 종류 수정)
        def generate_dummy_data(days=30):
            np.random.seed(42)
            timestamps = [datetime.now() - timedelta(hours=i) for i in range(days * 24)]
            noise_types = ["차량 경적", "차량 주행음", "차량 사이렌", "오토바이 경적", "오토바이 주행음", "기타소음"]
            directions = ["왼쪽", "오른쪽", "중앙"]
            regions = ["서울", "부산", "대구", "광주"]

            data = {
                "시간": timestamps,
                "소음 유형": [np.random.choice(noise_types, p=[0.25, 0.25, 0.15, 0.15, 0.15, 0.05]) for _ in range(days * 24)],  # 확률 조정
                "소음 강도(dB)": np.random.uniform(40, 90, days * 24),
                "방향": [np.random.choice(directions) for _ in range(days * 24)],
                "거리(m)": np.random.uniform(5, 100, days * 24),
                "지역": [np.random.choice(regions) for _ in range(days * 24)],
                "경고": [np.random.choice(["위험", "주의", None], p=[0.1, 0.3, 0.6]) for _ in range(days * 24)],
                "안전 확인": [np.random.choice([True, False], p=[0.8, 0.2]) if x in ["위험", "주의"] else None for x in [np.random.choice(["위험", "주의", None], p=[0.1, 0.3, 0.6]) for _ in range(days * 24)]]
            }
            return pd.DataFrame(data)

        # 안전지수 계산 함수
        def calculate_safety_index(df):
            danger_ratio = len(df[df["소음 강도(dB)"] >= 70]) / len(df) * 100
            no_response_ratio = (1 - df[df["경고"] == "위험"]["안전 확인"].mean()) * 100 if len(df[df["경고"] == "위험"]) > 0 else 0
            safety_index = min(danger_ratio * 2 + no_response_ratio, 100)
            return safety_index

        # 신호등 표시 함수
        def display_traffic_light(safety_index):
            if safety_index <= 33:
                green, yellow, red = 1, 0.2, 0.2
                status = "안전"
                color = "#6BCB77"
                tooltip = "위험 소음이 적고 경고에 잘 응답했어요!"
            elif safety_index <= 66:
                green, yellow, red = 0.2, 1, 0.2
                status = "주의"
                color = "#FFD93D"
                tooltip = "소음이 다소 높거나 일부 경고에 응답하지 않았어요."
            else:
                green, yellow, red = 0.2, 0.2, 1
                status = "위험"
                color = "#FF6B6B"
                tooltip = "위험 소음이 많고 경고 미응답이 늘어났어요!"

            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2>나의 안전지수: <span style="color: {color}">{int(safety_index)}</span> ({status})</h2>
                    <div style="display: flex; justify-content: center; gap: 20px;">
                        <div class="light" style="width: 50px; height: 50px; border-radius: 50%; background-color: #6BCB77; opacity: {green}; transition: opacity 0.5s;"></div>
                        <div class="light" style="width: 50px; height: 50px; border-radius: 50%; background-color: #FFD93D; opacity: {yellow}; transition: opacity 0.5s;"></div>
                        <div class="light tooltip" style="width: 50px; height: 50px; border-radius: 50%; background-color: #FF6B6B; opacity: {red}; transition: opacity 0.5s;">
                            <span class="tooltiptext">{tooltip}</span>
                        </div>
                    </div>
                </div>
                <style>
                    .tooltip {{
                        position: relative;
                        display: inline-block;
                    }}
                    .tooltip .tooltiptext {{
                        visibility: hidden;
                        width: 200px;
                        background-color: #555;
                        color: #fff;
                        text-align: center;
                        border-radius: 6px;
                        padding: 5px;
                        position: absolute;
                        z-index: 1;
                        bottom: 125%;
                        left: 50%;
                        margin-left: -100px;
                        opacity: 0;
                        transition: opacity 0.3s;
                    }}
                    .tooltip:hover .tooltiptext {{
                        visibility: visible;
                        opacity: 1;
                    }}
                </style>
                """, unsafe_allow_html=True
            )

        # 데이터 로드 및 필터
        if "dummy_data" not in st.session_state:
            st.session_state["dummy_data"] = generate_dummy_data()
        df = st.session_state["dummy_data"]

        st.subheader("🔍 데이터 필터")
        col1, col2 = st.columns(2)
        with col1:
            time_range = st.slider(
                "시간 범위 (최근 며칠)", 1, 30, 7,
                help="분석하고 싶은 소음 데이터의 기간을 설정합니다. \n\n 슬라이더를 움직여 최근 1일부터 30일까지 선택할 수 있습니다."
            )
        with col2:
            selected_types = st.multiselect(
                "소음 유형", df["소음 유형"].unique(), default=df["소음 유형"].unique(),
                help="분석에 포함할 소음 유형을 선택합니다. \n\n 여러 유형을 선택하거나 해제하여 원하는 소음만 볼 수 있습니다."
            )
        filtered_df = df[df["시간"] > datetime.now() - timedelta(days=time_range)]
        filtered_df = filtered_df[filtered_df["소음 유형"].isin(selected_types)]

        # 안전지수 신호등
        safety_index = calculate_safety_index(filtered_df)
        st.button(
            "안전지수란?", 
            help="안전지수는 소음 강도와 경고 응답 여부를 기반으로 계산됩니다. \n\n - 0-33: 안전 (초록)\n - 34-66: 주의 (노랑)\n - 67-100: 위험 (빨강)\n\n 위험 소음(70dB 이상) 비율과 경고 미응답 비율을 합쳐 결정됩니다."
        )
        display_traffic_light(safety_index)

        # 1. 사용자 개인 소음 경험 통계
        st.subheader("1. 나의 소음 경험")
        col1, col2, col3 = st.columns(3)
        with col1:
            type_counts = filtered_df["소음 유형"].value_counts()
            fig_pie = px.pie(names=type_counts.index, values=type_counts.values, title="소음 유형 분포", hole=0.3,
                             color_discrete_sequence=px.colors.sequential.Plasma)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown(
                "ℹ️ *소음 유형별 발생 비율을 보여줍니다.*",
                help="선택한 기간 동안 어떤 소음이 얼마나 자주 발생했는지 확인할 수 있습니다."
            )
        with col2:
            hourly_df = filtered_df.groupby(filtered_df["시간"].dt.hour)["소음 유형"].count().reset_index()
            fig_line = px.line(hourly_df, x="시간", y="소음 유형", title="시간대별 소음 발생", 
                               color_discrete_sequence=["#FF6B6B"])
            st.plotly_chart(fig_line, use_container_width=True)
            st.markdown(
                "ℹ️ *시간대별 소음 발생 건수를 보여줍니다.*",
                help="하루 중 언제 소음이 많이 발생하는지 파악할 수 있습니다. (0-23시 기준)"
            )
        with col3:
            danger_count = len(filtered_df[filtered_df["소음 강도(dB)"] >= 70])
            fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=danger_count, 
                                               domain={'x': [0, 1], 'y': [0, 1]}, title={'text': "위험 소음 횟수"},
                                               gauge={'axis': {'range': [0, 10]}, 'bar': {'color': "#FF4D4D"}}))
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(
                "ℹ️ *70dB 이상 소음 횟수를 보여줍니다.*",
                help="70dB 이상은 위험 소음으로 간주되며, 이는 귀 건강에 영향을 줄 수 있는 수준입니다."
            )
        st.markdown(f"📌 *가장 자주 감지된 소음은 {type_counts.index[0]} (일 평균 {type_counts[0]//time_range:.1f}회)입니다.*")

        # 2. 소음 위치 및 방향 통계
        st.subheader("2. 소음 위치 및 방향")
        col1, col2 = st.columns(2)
        with col1:
            direction_counts = filtered_df["방향"].value_counts()
            fig_radar = px.line_polar(r=direction_counts.values, theta=direction_counts.index, line_close=True,
                                      title="방향별 소음 분포", color_discrete_sequence=["#4ECDC4"])
            fig_radar.update_traces(fill="toself")
            st.plotly_chart(fig_radar, use_container_width=True)
            st.markdown(
                "ℹ️ *소음이 발생한 방향별 빈도를 보여줍니다.*",
                help="사용자 주변에서 소음이 어느 방향에서 자주 들리는지 확인할 수 있습니다."
            )
        with col2:
            distance_bins = pd.cut(filtered_df["거리(m)"], bins=[0, 10, 50, 100], labels=["0-10m", "10-50m", "50m 이상"])
            distance_counts = distance_bins.value_counts()
            fig_bar = px.bar(x=distance_counts.index, y=distance_counts.values, title="추정 거리 분포",
                             color=distance_counts.index, color_discrete_sequence=px.colors.sequential.Viridis)
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown(
                "ℹ️ *소음 발생 추정 거리 분포를 보여줍니다.*",
                help="소음이 얼마나 가까이에서 발생했는지 파악할 수 있습니다."
            )
        st.markdown(f"📌 *오른쪽에서 발생한 소음이 지난주 대비 {np.random.randint(5, 15)}% 증가했어요.*")

        # 3. 소음 강도 분석
        st.subheader("3. 소음 강도 분석")
        col1, col2 = st.columns(2)
        with col1:
            avg_db, max_db = filtered_df["소음 강도(dB)"].mean(), filtered_df["소음 강도(dB)"].max()
            fig_box = px.box(filtered_df, y="소음 강도(dB)", title=f"평균 {avg_db:.1f}dB | 최대 {max_db:.1f}dB",
                             color_discrete_sequence=["#FFD93D"])
            st.plotly_chart(fig_box, use_container_width=True)
            st.markdown(
                "ℹ️ *소음 강도의 평균과 최대값을 보여줍니다.*",
                help="소음 강도(dB)는 데시벨 단위로, 높을수록 소리가 큽니다."
            )
        with col2:
            level_bins = pd.cut(filtered_df["소음 강도(dB)"], bins=[0, 50, 70, 120], labels=["안전", "주의", "위험"])
            level_counts = level_bins.value_counts(normalize=True) * 100
            fig_stack = px.bar(x=level_counts.index, y=level_counts.values, title="위험 수준별 비율",
                               color=level_counts.index, color_discrete_map={"안전": "#6BCB77", "주의": "#FFD93D", "위험": "#FF6B6B"})
            st.plotly_chart(fig_stack, use_container_width=True)
            st.markdown(
                "ℹ️ *소음 강도별 위험 수준 비율을 보여줍니다.*",
                help="0-50dB: 안전, 50-70dB: 주의, 70dB 이상: 위험으로 분류됩니다."
            )
        max_noise_row = filtered_df.loc[filtered_df["소음 강도(dB)"].idxmax()]
        st.markdown(f"📌 *이번 주 최대 소음은 {max_noise_row['시간'].strftime('%A %H:%M')}에 기록된 {max_noise_row['소음 강도(dB)']:.1f}dB ({max_noise_row['소음 유형']})입니다.*")

        # 4. 경고 시스템 통계
        st.subheader("4. 경고 시스템 통계")
        col1, col2, col3 = st.columns(3)
        with col1:
            danger_alerts = len(filtered_df[filtered_df["경고"] == "위험"])
            caution_alerts = len(filtered_df[filtered_df["경고"] == "주의"])
            fig_timeline = px.scatter(filtered_df[filtered_df["경고"].notnull()], x="시간", y="소음 강도(dB)", color="경고",
                                      title=f"경고 발생: 위험 {danger_alerts}회, 주의 {caution_alerts}회",
                                      color_discrete_map={"위험": "#FF6B6B", "주의": "#FFD93D"})
            st.plotly_chart(fig_timeline, use_container_width=True)
            st.markdown(
                "ℹ️ *경고 발생 시점과 강도를 보여줍니다.*",
                help="위험(70dB 이상)과 주의(50-70dB) 경고가 언제 발생했는지 확인할 수 있습니다."
            )
        with col2:
            response_rate = filtered_df[filtered_df["경고"] == "위험"]["안전 확인"].mean() * 100 if len(filtered_df[filtered_df["경고"] == "위험"]) > 0 else 0
            fig_pie_response = px.pie(values=[response_rate, 100 - response_rate], names=["응답", "미응답"],
                                      title=f"안전 확인 응답률: {response_rate:.1f}%", hole=0.4,
                                      color_discrete_sequence=["#6BCB77", "#FF6B6B"])
            st.plotly_chart(fig_pie_response, use_container_width=True)
            st.markdown(
                "ℹ️ *위험 경고에 대한 응답률을 보여줍니다.*",
                help="경고 후 5분 내 응답 여부를 기준으로 계산됩니다."
            )
        with col3:
            sos_count = len(filtered_df[(filtered_df["경고"] == "위험") & (filtered_df["안전 확인"] == False)])
            st.markdown(f"<h3 style='text-align: center;'>SOS 이메일 발송</h3><p style='text-align: center; font-size: 24px; color: #FF6B6B;'>{sos_count}회</p>", unsafe_allow_html=True)
            st.markdown(
                "ℹ️ *SOS 이메일 발송 횟수를 보여줍니다.*",
                help="위험 경고 후 5분간 응답이 없으면 SOS 이메일이 발송됩니다."
            )
        latest_alert = filtered_df[filtered_df["경고"].notnull()].iloc[0]
        st.markdown(f"📌 *가장 최근 경고는 {latest_alert['시간'].strftime('%Y-%m-%d %H:%M')}에 발생했으며, 5분 내 안전 확인 완료!*")

        # 5. 지역/커뮤니티 비교
       
        st.subheader("5. 지역별 소음 수준")
        region_avg = df.groupby("지역")["소음 강도(dB)"].mean().reset_index()
        fig_map = px.bar(region_avg, x="지역", y="소음 강도(dB)", title="지역별 평균 소음",
                        color="소음 강도(dB)", color_continuous_scale="Reds")
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown(f"📌 *당신의 동네는 소음 상위 {np.random.randint(10, 30)}%에 속해요.*")
        st.info("ℹ️ 실제 구현 시 위치 데이터 수집 동의 필요, 데이터는 익명화 처리됩니다.")

        # 6. 트렌드 및 예측
        st.subheader("6. 트렌드 및 예측")
        weekly_df = filtered_df.groupby(filtered_df["시간"].dt.isocalendar().week)["소음 강도(dB)"].mean().reset_index()
        fig_trend = px.line(weekly_df, x="week", y="소음 강도(dB)", title="주간 소음 트렌드",
                            color_discrete_sequence=["#4ECDC4"])
        trend_placeholder = st.empty()
        for i in range(len(weekly_df)):
            temp_df = weekly_df.iloc[:i+1]
            fig_temp = px.line(temp_df, x="week", y="소음 강도(dB)", color_discrete_sequence=["#4ECDC4"])
            trend_placeholder.plotly_chart(fig_temp, use_container_width=True)
            time.sleep(0.3)
        increase = np.random.randint(10, 20)
        st.markdown(f"📌 *지난달 대비 소음 발생 {increase}% 증가.*")
        st.warning(f"⚠️ 내일 18:00-20:00에 차량 소음 증가 예상 (AI 예측)")

if __name__ == "__main__":
    m = Statistics_page()
    m.statistics_page()