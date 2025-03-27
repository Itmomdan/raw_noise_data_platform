import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import mysql.connector
from config import DB_CONFIG

# 통계 페이지를 위한 클래스 정의
class Statistics_page:
    # 특정 사용자의 데이터를 DB에서 가져오는 함수
    def fetch_data_from_db(self, user_id, days=30):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT noise_type, spl_peak, spl_rms, estimated_distance, direction, 
                   latitude, longitude, alarm_triggered, audio_path, timestamp
            FROM classification_results
            WHERE user_id = %s AND timestamp > %s
            ORDER BY timestamp DESC
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute(query, (user_id, cutoff_date))
        data = cursor.fetchall()
        conn.close()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df['spl_peak'] = df['spl_peak'].astype(float)
        df['spl_rms'] = df['spl_rms'].astype(float)
        df['estimated_distance'] = pd.to_numeric(df['estimated_distance'], errors='coerce')
        df['warning'] = df['spl_peak'].apply(lambda x: '위험' if x >= 70 else '주의' if x >= 50 else None)
        df['safety_check'] = df['alarm_triggered'].apply(lambda x: True if x == 1 else False if pd.notna(x) else None)
        return df

    # 모든 사용자의 데이터를 DB에서 가져오는 함수
    def fetch_all_users_data(self, days=30):
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT user_id, noise_type, spl_peak, latitude, longitude, timestamp
            FROM classification_results
            WHERE timestamp > %s
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute(query, (cutoff_date,))
        data = cursor.fetchall()
        conn.close()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df['spl_peak'] = df['spl_peak'].astype(float)
        return df

    # 위도와 경도를 기반으로 지역명을 반환하는 함수
    def assign_region(self, lat, lon):
        """위도/경도를 기반으로 지역명 매핑, None 처리 추가"""
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            return "기타"
        lat, lon = float(lat), float(lon)
        if 37.0 <= lat <= 38.0 and 126.5 <= lon <= 127.5:
            return "서울"
        elif 34.5 <= lat <= 35.5 and 128.8 <= lon <= 129.5:
            return "부산"
        elif 35.5 <= lat <= 36.5 and 128.0 <= lon <= 129.0:
            return "대구"
        elif 37.0 <= lat <= 38.0 and 126.0 <= lon <= 126.8:
            return "인천"
        elif 34.8 <= lat <= 35.5 and 126.5 <= lon <= 127.0:
            return "광주"
        elif 33.0 <= lat <= 34.0 and 126.0 <= lon <= 127.0:
            return "제주"
        elif 36.0 <= lat <= 36.7 and 127.0 <= lon <= 127.8:
            return "대전"
        elif 36.5 <= lat <= 37.5 and 127.5 <= lon <= 128.5:
            return "충북"
        else:
            return "기타"

    # 안전지수를 계산하는 함수
    def calculate_safety_index(self, df):
        if df.empty:
            return 0
        danger_ratio = len(df[df["spl_peak"] >= 70]) / len(df) * 100
        no_response_ratio = (1 - df[df["warning"] == "위험"]["safety_check"].mean()) * 100 if len(df[df["warning"] == "위험"]) > 0 else 0
        safety_index = min(danger_ratio * 2 + no_response_ratio, 100)
        return safety_index

    # 안전지수를 신호등 UI로 표시하는 함수
    def display_traffic_light(self, safety_index):
        if safety_index <= 33:
            green, yellow, red = 1, 0.2, 0.2
            status = "안전"
            color = "#6BCB77"
            tooltip = "위험 소음이 적고 응답률이 높아요!"
        elif safety_index <= 66:
            green, yellow, red = 0.2, 1, 0.2
            status = "주의"
            color = "#FFD93D"
            tooltip = "소음이 다소 높거나 응답이 느려요."
        else:
            green, yellow, red = 0.2, 0.2, 1
            status = "위험"
            color = "#FF6B6B"
            tooltip = "위험 소음이 많고 응답이 부족해요!"
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 20px; display: flex; align-items: center; justify-content: center;">
                <h2 style="margin-right: 20px;">나의 안전지수: <span style="color: {color}">{int(safety_index)}</span> ({status})</h2>
                <div style="display: flex; justify-content: center; gap: 20px; align-items: center;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background-color: #6BCB77; opacity: {green};"></div>
                    <div style="width: 50px; height: 50px; border-radius: 50%; background-color: #FFD93D; opacity: {yellow};"></div>
                    <div class="tooltip" style="width: 50px; height: 50px; border-radius: 50%; background-color: #FF6B6B; opacity: {red};">
                        <span class="tooltiptext">{tooltip}</span>
                    </div>
                    <span style="font-size: 14px; cursor: pointer; color: #1E90FF;" class="tooltip">❓
                        <span class="tooltiptext">안전지수는 소음 강도와 경고 응답 여부를 기반으로 계산됩니다.<br>- 0-33: 안전 (초록)<br>- 34-66: 주의 (노랑)<br>- 67-100: 위험 (빨강)<br>계산: (70dB 이상 소음 비율 × 2) + (위험 경고 미응답 비율)</span>
                    </span>
                </div>
            </div>
            <style>
                .tooltip {{ position: relative; display: inline-block; }}
                .tooltip .tooltiptext {{ visibility: hidden; width: 250px; background-color: #555; color: #fff; text-align: left; border-radius: 6px; padding: 5px; position: absolute; z-index: 1; top: 125%; left: 50%; margin-left: -125px; opacity: 0; transition: opacity 0.3s; }}
                .tooltip:hover .tooltiptext {{ visibility: visible; opacity: 1; }}
            </style>
            """, unsafe_allow_html=True
        )

    # 통계 페이지의 메인 함수 (웹 UI 구성)
    def statistics_page(self):
        user_id = st.session_state['user_info']['id']

        with st.expander("🔍 데이터 필터 설정", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                time_range = st.slider("시간 범위 (최근 며칠)", 1, 30, 7, key="time_range")
            with col2:
                noise_types = ["차량경적", "이륜차경적", "차량사이렌", "차량주행음", "이륜차주행음", "기타소음"]
                selected_types = st.multiselect("소음 유형", noise_types, default=noise_types, key="noise_types")

        df = self.fetch_data_from_db(user_id, days=time_range)
        if df.empty:
            st.warning("선택한 기간 내 데이터가 없습니다.")
            return
        filtered_df = df[df["noise_type"].isin(selected_types)]

      # 선택된 소음 유형이 데이터프레임에 있는지 확인
        valid_noise_types = [t for t in selected_types if t in df['noise_type'].unique()]

        if not valid_noise_types:
            st.warning("선택한 소음 유형에 대한 사용자 측정 기록이 없습니다.")
            return

        filtered_df = df[df["noise_type"].isin(valid_noise_types)]

        if filtered_df.empty:
          st.warning("선택하신 조건에 맞는 데이터가 없습니다.")
          return

        with st.expander("📌 한눈에 보는 통계", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 소음 이벤트", len(filtered_df))
            with col2:
                st.metric("평균 소음 강도", f"{filtered_df['spl_peak'].mean():.1f} dB")
            with col3:
                safety_index = self.calculate_safety_index(filtered_df)
                st.metric("안전지수", int(safety_index))
            self.display_traffic_light(safety_index)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "나의 소음 경험", "소음 위치와 방향", "소음 강도 분석", 
            "경고와 응답", "지역과 커뮤니티", "트렌드와 예측"
        ])

        with tab1:
            st.subheader("나의 소음 경험")
            col1, col2, col3 = st.columns(3)
            with col1:
                type_counts = filtered_df["noise_type"].value_counts()
                fig_pie = px.pie(names=type_counts.index, values=type_counts.values, title="소음 유형 분포", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
                st.info("ℹ️ 소음 유형별 발생 비율을 원형 차트로 표시합니다.")
            with col2:
                hourly_df = filtered_df.groupby(filtered_df["timestamp"].dt.strftime('%H:00')).size().reset_index(name='count')
                all_hours = pd.DataFrame({'timestamp': [f"{h:02d}:00" for h in range(24)]})
                hourly_df = all_hours.merge(hourly_df, on='timestamp', how='left').fillna({'count': 0})
                fig_line = px.line(hourly_df, x="timestamp", y="count", title="시간대별 소음 발생")
                st.plotly_chart(fig_line, use_container_width=True)
                st.info("ℹ️ 하루 중 소음 발생 건수를 시간별로 보여줍니다 (0-23시).")
            with col3:
                danger_count = len(filtered_df[filtered_df["spl_peak"] >= 70])
                fig_gauge = go.Figure(go.Indicator(mode="gauge+number", value=danger_count, 
                                                   domain={'x': [0, 1], 'y': [0, 1]}, title={'text': "위험 소음 횟수"},
                                                   gauge={'axis': {'range': [0, max(10, danger_count+1)]}, 'bar': {'color': "#FF4D4D"}}))
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.info("ℹ️ 위험 소음 발생 횟수를 게이지로 표시합니다.")
            st.markdown(f"📝 *분석 리포트*: 가장 자주 감지된 소음은 '{type_counts.index[0]}' (일 평균 {type_counts[0]/time_range:.1f}회)입니다.")

        with tab2:
            st.subheader("소음 위치와 방향")
            col1, col2 = st.columns(2)

            with col1:
                # 방향별 소음 빈도를 레이더 차트로 표시
                direction_counts = filtered_df["direction"].value_counts()
                if direction_counts.empty:
                    st.warning("방향 데이터가 부족합니다.")
                    fig_radar = px.line_polar(r=[0], theta=["없음"], line_close=True, title="방향별 소음 분포")
                else:
                    # 방향과 값 정의
                    directions = ["오른쪽", "없음", "왼쪽", "중앙"]  # 데이터 순서
                    values = [direction_counts.get(d, 0) for d in directions]  # 각 방향의 값, 없으면 0
                    angles = [0, 90, 180, 270]  # 각도: 오른쪽(0°), 아래(90°), 왼쪽(180°), 위(270°)
                    
                    fig_radar = px.line_polar(
                        r=values,
                        theta=angles,  # 숫자 각도로 설정
                        line_close=True,
                        title="방향별 소음 분포"
                    )
                    fig_radar.update_traces(fill="toself")
                    
                    # 각도와 라벨 위치를 사용자 정의로 설정
                    fig_radar.update_layout(
                        polar=dict(
                            angularaxis=dict(
                                tickmode="array",
                                tickvals=[0, 90, 180, 270],  # 각도 위치
                                ticktext=["오른쪽", "없음", "왼쪽", "중앙"],  # 라벨: 오른쪽, 아래, 왼쪽, 위
                                rotation=90,  # 0°를 오른쪽에서 위로 90° 회전 (270°가 위)
                                direction="clockwise"  # 시계 방향
                            )
                        )
                    )

                st.plotly_chart(fig_radar, use_container_width=True)
                st.info("ℹ️ 소음이 들리는 방향별 빈도를 레이더 차트로 보여줍니다.")

            with col2:
                # 추정 거리별 분포를 막대 차트로 표시 (0-25m 범위, 5m 단위)
                distance_bins = pd.cut(
                    filtered_df["estimated_distance"],
                    bins=[0, 5, 10, 15, 20, float("inf")],
                    labels=["0-5m", "6-10m", "11-15m", "16-20m", "20m 이상"],
                    include_lowest=True
                )
                distance_counts = distance_bins.value_counts().sort_index()
                fig_bar = px.bar(
                    x=distance_counts.index,
                    y=distance_counts.values,
                    title="추정 거리 분포"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                st.info("ℹ️ 소음 발생 추정 거리 구간별 분포를 막대 차트로 표시합니다.")

            # 지도 데이터 표시
            map_df = filtered_df.dropna(subset=["latitude", "longitude"])
            if not map_df.empty:
                fig_map = px.scatter_mapbox(
                    map_df, lat="latitude", lon="longitude", color="spl_peak",
                    size="spl_peak", color_continuous_scale=px.colors.sequential.Reds,
                    title="소음 발생 지도", zoom=10, height=400, mapbox_style="open-street-map"
                )
                st.plotly_chart(fig_map, use_container_width=True)
                st.info("ℹ️ 소음 발생 위치를 지도에 표시하며, 색상과 크기로 강도를 나타냅니다.")
            else:
                st.warning("위치 데이터가 없습니다.")

            # 가장 많이 감지된 방향 표시
            most_common_dir = direction_counts.index[0] if not direction_counts.empty else "없음"
            st.markdown(f"📝 *분석 리포트*: 가장 많이 감지된 방향은 '{most_common_dir}'입니다.")
            
        with tab3:
            st.subheader("소음 강도 분석")
            col1, col2 = st.columns(2)
            with col1:
                avg_db, max_db = filtered_df["spl_peak"].mean(), filtered_df["spl_peak"].max()
                fig_box = px.box(filtered_df, y="spl_peak", title=f"평균 {avg_db:.1f}dB | 최대 {max_db:.1f}dB")
                st.plotly_chart(fig_box, use_container_width=True)
                st.info("ℹ️ 소음 강도의 분포와 평균/최대값을 박스 플롯으로 보여줍니다.")
            with col2:
                level_bins = pd.cut(filtered_df["spl_peak"], bins=[0, 50, 70, 120], labels=["안전", "주의", "위험"])
                level_counts = level_bins.value_counts(normalize=True) * 100
                fig_stack = px.bar(x=level_counts.index, y=level_counts.values, title="위험 수준별 비율",
                                   color=level_counts.index, color_discrete_map={"안전": "#6BCB77", "주의": "#FFD93D", "위험": "#FF6B6B"})
                st.plotly_chart(fig_stack, use_container_width=True)
                st.info("ℹ️ 소음 강도를 안전/주의/위험으로 나눠 비율을 표시합니다.")
            max_noise_row = filtered_df.loc[filtered_df["spl_peak"].idxmax()]
            st.markdown(f"📝 *분석 리포트*: 최대 소음은 {max_noise_row['timestamp'].strftime('%Y-%m-%d %H:%M')}에 {max_noise_row['spl_peak']:.1f}dB ({max_noise_row['noise_type']})로 기록됨.")

        with tab4:
            st.subheader("경고와 응답")
            sos_count = len(filtered_df[(filtered_df["warning"] == "위험") & (filtered_df["safety_check"] == False)])
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(
                    f"<h3 style='text-align: left;'>🚨 SOS 발송: <span style='color: #FF6B6B;'>{sos_count}회</span></h3>",
                    unsafe_allow_html=True
                )
            with col2:
                if sos_count > 0:
                    latest_sos = filtered_df[(filtered_df["warning"] == "위험") & (filtered_df["safety_check"] == False)].iloc[0]["timestamp"]
                    st.markdown(
                        f"<p style='text-align: right;'>최근 발송: {latest_sos.strftime('%Y-%m-%d %H:%M')}</p>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<p style='text-align: right;'>최근 발송: 없음</p>",
                        unsafe_allow_html=True
                    )
            st.info("ℹ️ 응답 없는 위험 경고로 발송된 SOS 횟수와 가장 최근 발송 시점입니다.")
            col3, col4 = st.columns(2)
            with col3:
                danger_alerts = len(filtered_df[filtered_df["warning"] == "위험"])
                caution_alerts = len(filtered_df[filtered_df["warning"] == "주의"])
                fig_timeline = px.scatter(
                    filtered_df[filtered_df["warning"].notnull()], 
                    x="timestamp", 
                    y="spl_peak", 
                    color="warning",
                    title=f"경고: 위험 {danger_alerts}회, 주의 {caution_alerts}회",
                    color_discrete_map={"위험": "#FF6B6B", "주의": "#FFD93D"}
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
                st.info("ℹ️ 경고 발생 시점과 강도를 타임라인으로 표시합니다.")
            with col4:
                response_rate = filtered_df[filtered_df["warning"] == "위험"]["safety_check"].mean() * 100 if len(filtered_df[filtered_df["warning"] == "위험"]) > 0 else 0
                fig_pie_response = px.pie(
                    values=[response_rate, 100 - response_rate], 
                    names=["응답", "미응답"],
                    title=f"응답률: {response_rate:.1f}%", 
                    hole=0.4,
                    color_discrete_sequence=["#6BCB77", "#FF6B6B"]
                )
                st.plotly_chart(fig_pie_response, use_container_width=True)
                st.info("ℹ️ 위험 경고에 대한 응답 비율을 원형 차트로 보여줍니다.")
            if not filtered_df[filtered_df["warning"].notnull()].empty:
                latest_alert = filtered_df[filtered_df["warning"].notnull()].iloc[0]
                st.markdown(f"📝 *분석 리포트*: 최근 경고는 {latest_alert['timestamp'].strftime('%Y-%m-%d %H:%M')}에 발생 ({latest_alert['warning']}).")

        with tab5:
            st.subheader("지역과 커뮤니티")
            all_users_df = self.fetch_all_users_data(days=time_range)
            if not all_users_df.empty:
                all_users_df['region'] = all_users_df.apply(lambda row: self.assign_region(row['latitude'], row['longitude']), axis=1)
                total_users = all_users_df['user_id'].nunique()
                total_noises = len(all_users_df)
                noise_type_counts = all_users_df["noise_type"].value_counts()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="👤 전체 유저 수", value=total_users)
                with col2:
                    st.metric(label="📢 현재까지 담긴 소음 개수", value=total_noises)
                col3, col4 = st.columns(2)
                with col3:
                    fig_noise_pie = px.pie(names=noise_type_counts.index, values=noise_type_counts.values, 
                                           title="전체 유저 소음 유형", hole=0.3)
                    st.plotly_chart(fig_noise_pie, use_container_width=True)
                with col4:
                    region_avg = all_users_df.groupby('region')['spl_peak'].mean().reset_index()
                    fig_region_bar = px.bar(region_avg, x="region", y="spl_peak", title="지역별 평균 소음", 
                                            color="spl_peak", color_continuous_scale="Reds")
                    st.plotly_chart(fig_region_bar, use_container_width=True)
                region_map = all_users_df.dropna(subset=["latitude", "longitude"])
                fig_region_map = px.scatter_mapbox(
                    region_map, lat="latitude", lon="longitude", color="spl_peak",
                    size="spl_peak", color_continuous_scale=px.colors.sequential.Reds,
                    title="전국 소음 분포", zoom=6, center={"lat": 36.5, "lon": 127.5}, height=400, mapbox_style="open-street-map"
                )
                st.plotly_chart(fig_region_map, use_container_width=True)
                st.info("ℹ️ 모든 사용자 데이터를 기반으로 전국 소음 발생 위치를 지도에 표시합니다.")
            avg_spl = filtered_df["spl_peak"].mean()
            st.markdown(f"📝 *분석 리포트*: 당신의 평균 소음은 {avg_spl:.1f}dB로, 전체 사용자 평균 {all_users_df['spl_peak'].mean():.1f}dB와 비교됩니다.")

        with tab6:
            st.subheader("트렌드와 예측")
            filtered_df['year'] = filtered_df["timestamp"].dt.year
            filtered_df['week'] = filtered_df["timestamp"].dt.isocalendar().week
            weekly_df = filtered_df.groupby(['year', 'week'])["spl_peak"].mean().reset_index()
            if weekly_df.empty:
                st.warning("주간 데이터가 부족합니다.")
                fig_trend = px.line(x=["없음"], y=[0], title="주간 소음 트렌드")
            else:
                weekly_df['week'] = weekly_df['week'].astype(int)
                weekly_df['week_label'] = weekly_df.apply(lambda row: f"{int(row['year'])}-W{int(row['week']):02d}", axis=1)
                fig_trend = px.line(weekly_df, x="week_label", y="spl_peak", title="주간 소음 트렌드")
                increase = (weekly_df["spl_peak"].iloc[-1] - weekly_df["spl_peak"].iloc[0]) / weekly_df["spl_peak"].iloc[0] * 100 if len(weekly_df) > 1 else 0
                st.markdown(f"📝 *분석 리포트*: 지난주 대비 소음 강도 {increase:.1f}% {'증가' if increase > 0 else '감소'}.")
            st.plotly_chart(fig_trend, use_container_width=True)
            st.info("ℹ️ 주 단위로 평균 소음 강도의 변화를 선 그래프로 보여줍니다.")
            st.warning("⚠️ 내일 18:00-20:00에 소음 증가 예상 (AI 예측, 개발 중)")

# 실행: Statistics_page 클래스의 인스턴스 생성 후 통계 페이지 표시
if __name__ == "__main__":
    m = Statistics_page()
    m.statistics_page()