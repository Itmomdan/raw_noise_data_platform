import streamlit as st
import numpy as np
import pandas as pd

def run():
    # 이메일 입력 받기 (알람 서비스 설정)
    st.header("📩 소음 알람 서비스 설정")
    email = st.text_input("이메일을 입력하세요", placeholder="example@email.com")


    # 기준 소음 크기 (1m에서의 소음 크기 dB)
    # 🎯 기준 소음 크기 설정 (1m 거리에서의 소음 크기)
    # 기준 소음 크기란? 🔊
    # - 소음이 발생하는 지점(1m 거리)에서 측정한 소음 크기(dB).
    # - 예를 들어, 차량 경적이 1m 거리에서 80dB이라면, 10m에서는 소리가 더 작아짐.
    # - 거리 증가에 따른 소음 감쇠는 일반적으로 `20 * log10(거리비율)`로 계산됨.
    base_noise_level = st.slider("🔊 기준 소음 크기 (1m에서 dB)", min_value=40, max_value=120, value=80)


    # 사용자가 설정할 수 있는 거리 범위를 1m부터 30m까지 지정
    max_distance = 30  # 최대 거리
    distance_range = np.linspace(1, max_distance, num=30)

    # 거리별 예상 소음 크기 계산
    # - 거리 증가에 따라 소음 크기는 줄어듦 (이론적으로 6dB 감소 per 2배 거리)
    # - 공식: `소음(dB) = 기준 소음 크기 - 20 * log10(거리 / 기준 거리(1m))`
    noise_at_distance = [base_noise_level - 20 * np.log10(d / 1) for d in distance_range]

    # 🚨 알람을 받을 거리 기준 설정 (사용자가 설정)
    # - 사용자가 알람을 받을 최대 거리를 설정할 수 있음.
    # - 예: 사용자가 10m로 설정하면, 10m에서의 예상 소음 크기를 계산하여 경고
    selected_distance = st.slider("📏 알람을 받을 거리 기준 (m)", min_value=1, max_value=max_distance, value=10)
    estimated_noise_at_distance = base_noise_level - 20 * np.log10(selected_distance / 1)

    st.write(f"🚨 **{selected_distance}m 거리에서 예상 소음 크기:** {estimated_noise_at_distance:.1f} dB")

    # 소음 강도 기준 (dB) - 사용자 선택
    time_noise_levels = {
        "약(🔵)": {"이륜차경적": 50, "이륜차주행음": 45, "차량경적": 60, "차량사이렌": 65, "차량주행음": 55, "기타소음": 50},
        "중(🟡)": {"이륜차경적": 70, "이륜차주행음": 65, "차량경적": 80, "차량사이렌": 85, "차량주행음": 75, "기타소음": 70},
        "강(🔴)": {"이륜차경적": 90, "이륜차주행음": 85, "차량경적": 100, "차량사이렌": 110, "차량주행음": 95, "기타소음": 90}
    }

    # 소음 강도 기준 선택 (약/중/강)
    selected_level = st.radio("📢 알람 기준 선택", ["약(🔵)", "중(🟡)", "강(🔴)"], index=1)

    # 선택된 강도 기준 출력 (표로 표시)
    st.subheader("📌 소음 유형별 설정 기준 (dB)")
    st.write(f"선택한 기준: **{selected_level}**")
    st.table(pd.DataFrame(time_noise_levels[selected_level], index=["dB"]).T)

    # 알람 서비스 설정 버튼
    if st.button("✅ 설정 완료"):
        if email:
            st.success(f"📬 {email} 로 소음 알람이 전송됩니다! 🚀 (알람 기준: {selected_distance}m 거리, {estimated_noise_at_distance:.1f} dB)")
        else:
            st.warning("⚠️ 이메일을 입력하세요!")

    st.write("📢 설정한 거리 내에서 소음이 감지되면 이메일로 알람이 전송됩니다!")
