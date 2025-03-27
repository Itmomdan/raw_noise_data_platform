import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

class About_page:
    def about_page(self):
        # 탭 생성
        tab1, tab2, tab3 = st.tabs(['About', '모델 훈련 데이터셋 통계', '개발진 소개'])
        
        # 탭 1: About (기존 유지)
        with tab1:
            st.subheader('📢 담았소 프로젝트: AI 기반 위험 소음 감지 및 분석 플랫폼')
            st.write(' ')
            st.markdown("""
                ### 🔍 담았소 프로젝트란?
                담았소 프로젝트는 **AI 기반 위험 소음 감지 및 분석 플랫폼**으로,  
                일상적인 도로환경에서 소음 데이터를 수집하고 AI 모델을 이용해 분석하여  
                **교통 소음의 종류를 분류하고, 소음의 방향과 거리를 계산하여, 사용자에게 위험 경고를 제공하는 서비스**입니다.
            """)

            st.subheader("🚀 주요 기능")
            st.markdown("""
            - 📊 **소음 분류:** 차량 경적, 사이렌, 주행음 등 교통 소음을 감지하고 분류 
            - 🎯 **소리 방향 탐지:** 소리의 크기(SPL)와 음파 패턴을 기반으로 방향 판별
            - 📏 **거리 분석:** 소음 강도를 분석하여 소리가 발생한 거리 추정정
            - 🔔 **경고 시스템:** 위험 소음 감지 시 사용자에게 실시간간 알람 제공
            - 🎙 **개인 맞춤형 서비스:** 소리의 크기에 따라 위험 소음 알람 범위를 직접 설정
            - 📡 **소음 데이터 분석 리포트:** 사용자가 경험한 소음을 분석하고 인사이트 제공
            """)

        # 탭 2: 모델 훈련 데이터셋 통계 (expander로 분리)
        with tab2:
            st.subheader('모델 훈련 데이터셋 통계')

            # CSS 스타일 정의 (마우스 오버 툴팁)
            st.markdown("""
            <style>
            .tooltip {
              position: relative;
              display: inline-block;
              cursor: pointer;
              margin-left: 5px;
            }
            .tooltip .tooltiptext {
              visibility: hidden;
              width: 300px;
              background-color: #555;
              color: #fff;
              text-align: center;
              border-radius: 6px;
              padding: 5px;
              position: absolute;
              z-index: 1;
              bottom: 125%;
              left: 50%;
              margin-left: -150px;
              opacity: 0;
              transition: opacity 0.3s;
            }
            .tooltip:hover .tooltiptext {
              visibility: visible;
              opacity: 1;
            }
            </style>
            """, unsafe_allow_html=True)

            # 1. 데이터셋 소개
            with st.expander("1️⃣ 데이터셋 소개", expanded=False):
                st.subheader("🔹 데이터 출처")
                st.markdown("""
                - **AI Hub 도시 소리 데이터셋** : 도시 내 소음 문제 해결을 위하여 구축된 73,864건의 음향 데이터셋  
                - **활용 데이터셋** : 도시 소리 데이터셋 중 도로 환경에서 접할 수 있는 소음 **17,490건**  
                            🚗 **교통소음**[이륜차 경적, 이륜차 주행음, 차량 경적, 차량 사이렌, 차량 주행음] : **총 7,950건**  (각 1,590건)  
                            🚧 **기타소음**[개, 고양이, 공구, 발전기<span class="tooltip">ℹ️<span class="tooltiptext">발전기는 전기를 만드는 기계로, 공사장에서 자주 쓰이며 윙윙 소리가 날 수 있어요!</span></span>, 콘크리트 펌프<span class="tooltip">ℹ️<span class="tooltiptext">콘크리트 펌프는 건설 현장에서 콘크리트를 높은 곳이나 멀리 보내는 기계예요. 큰 소리가 나는 게 특징이에요!</span></span>, 항타기<span class="tooltip">ℹ️<span class="tooltiptext">항타기는 건설 현장에서 기둥(말뚝)을 땅에 박는 기계로, 쾅쾅 소리가 크게 나요!</span></span>] : **총 9,540건** (각 1,590건)  
                """, unsafe_allow_html=True)

                # 데이터 시각화를 위한 DataFrame 생성
                data = {"소음 유형": ["교통 소음", "기타 소음"], "건수": [7950, 9540]}
                df = pd.DataFrame(data)

                # 파이 차트 생성
                pie_color_sequence = ["skyblue", "darkblue"]
                fig_pie = px.pie(df, values="건수", names="소음 유형", title="소음 유형별 비율",
                                color_discrete_sequence=pie_color_sequence)
                fig_pie.update_traces(marker=dict(line=dict(color='white', width=2)))
                fig_pie.update_layout(showlegend=True)

                # 각 소음 유형별 건수를 나타내는 데이터프레임 생성
                noise_data = {
                    "세부 소음 유형": ["이륜차 경적", "이륜차 주행음", "차량 경적", "차량 사이렌", "차량 주행음",
                                    "개", "고양이", "공구", "발전기", "콘크리트펌프", "항타기"],
                    "건수": [1590] * 11
                }
                noise_df = pd.DataFrame(noise_data)

                # 막대 차트 생성
                bar_color_map = {k: "darkblue" if k in ["이륜차 경적", "이륜차 주행음", "차량 경적", "차량 사이렌", "차량 주행음"] else "skyblue" for k in noise_data["세부 소음 유형"]}
                fig_bar = px.bar(noise_df, x="세부 소음 유형", y="건수", title="세부 소음 유형별 건수",
                                color="세부 소음 유형", color_discrete_map=bar_color_map)
                fig_bar.update_layout(showlegend=False)

                # 차트 배치
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(fig_pie, use_container_width=True, key="pie_chart_tab2")
                with col2:
                    st.plotly_chart(fig_bar, use_container_width=True, key="bar_chart_tab2")

                st.subheader("🔹 소음 종류 및 샘플 오디오")
                noise_labels = ["🛵 이륜차 경적", "🛴 이륜차 주행음", "🚙 차량 주행음", "🚗 차량 경적", 
                                "🚨 차량 사이렌", "🐶 개", "😺 고양이", "🔧 공구", "🔋 발전기", "🚒 콘크리트 펌프", "🏗️ 항타기"]
                audio_folder = "audio"
                sample_files = {
                    "🛵 이륜차 경적": os.path.join(audio_folder, "2.motorcycle_horn_13261_1.wav"),
                    "🛴 이륜차 주행음": os.path.join(audio_folder, "2.motorcycle_driving_sound_1860_1.wav"),
                    "🚙 차량 주행음": os.path.join(audio_folder, "1.car_driving_sound_552_1.wav"),
                    "🚗 차량 경적": os.path.join(audio_folder, "1.car_horn_10_1.wav"),
                    "🚨 차량 사이렌": os.path.join(audio_folder, "1.car_siren_293_1.wav"),
                    "🐶 개": os.path.join(audio_folder, "7.동물(개)_9156_1.wav"),
                    "😺 고양이": os.path.join(audio_folder, "7.동물(고양이)_9210_1.wav"),
                    "🔧 공구": os.path.join(audio_folder, "8.도구_7225_1.wav"),
                    "🔋 발전기": os.path.join(audio_folder, "9.공사장(발전기)_18862_1.wav"),
                    "🚒 콘크리트 펌프": os.path.join(audio_folder, "9.공사장(콘크리트펌프)_8799_1.wav"),
                    "🏗️ 항타기": os.path.join(audio_folder, "9.공사장(항타기)_8553_1.wav"),
                }

                selected_label = st.selectbox("**소음 종류를 선택하세요:**", noise_labels, key="noise_select_tab2")
                selected_file = sample_files[selected_label]
                try:
                    audio_bytes = open(selected_file, "rb").read()
                    st.audio(audio_bytes, format="audio/wav")
                except FileNotFoundError:
                    st.write("(선택한 오디오 파일이 없습니다)")

            # 2. AI 모델 소개
            with st.expander("2️⃣ AI 모델 소개", expanded=False):
                st.subheader("🔹 사용한 모델: ResNet 기반 소음 분류 모델")
                st.markdown("""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
                    📌 <b>모델 개요</b>
                    <ul style="list-style-type: disc; padding-left: 20px;">
                        <li><b>ResNet</b><span class="tooltip">ℹ️<span class="tooltiptext">ResNet은 'Residual Network'의 약자로, 컴퓨터가 소음처럼 복잡한 패턴을 쉽게 배우도록 도와주는 똑똑한 구조예요. 층이 많아도 잘 학습할 수 있게 해줍니다!</span></span> 구조 적용</li>
                        <ul style="list-style-type: circle; padding-left: 30px;">
                            <li>복잡한 패턴을 배우는 데 강한 딥러닝 모델</li>
                            <li>정보가 잘 전달되도록 도와 학습을 더 효과적으로 진행</li>
                            <li>소음의 종류를 구분하여 위험한 소음을 빠르게 감지</li>
                            <li>익숙하지 않은 새로운 소음도 감지할 수 있음 (<b>OOD 탐지</b><span class="tooltip">ℹ️<span class="tooltiptext">OOD는 'Out-of-Distribution'의 약자로, 모델이 처음 보는 새로운 소음도 알아챌 수 있게 해주는 기능이에요.</span></span> 기능)</li>
                        </ul>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
                    📊 <b>데이터셋 분포</b>
                    <ul style="list-style-type: disc; padding-left: 20px;">
                        <li>훈련 및 검증 데이터: 총 16,500건 (1,500건 × 11종)</li>
                        <ul style="list-style-type: circle; padding-left: 30px;">
                            <li>훈련 데이터(Train): 80% (13,200건, 모든 소음이 균등하게 포함)</li>
                            <li>검증 데이터(Validation): 20% (3,300건, 무작위로 선택)</li>
                            <li>검증 데이터는 훈련 데이터와 겹치지 않도록 별도로 준비</li>
                        </ul>
                        <li>테스트 데이터: 총 990건 (90건 × 11종)</li>
                        <ul style="list-style-type: circle; padding-left: 30px;">
                            <li>훈련/검증에 사용되지 않은 새로운 데이터</li>
                            <li>각 소음 유형이 균등하게 포함되도록 구성</li>
                        </ul>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
                    🏆 <b>성능 평가</b>
                    <ul style="list-style-type: disc; padding-left: 20px;">
                        <li><b>정확도(Accuracy)</b><span class="tooltip">ℹ️<span class="tooltiptext">정확도는 모델이 소음을 얼마나 잘 맞췄는지 보여줘요. 100개 소음 중 96개를 맞췄다면 정확도는 96%예요!</span></span>, <b>재현율(Recall)</b><span class="tooltip">ℹ️<span class="tooltiptext">재현율은 실제 위험한 소음 중 모델이 얼마나 많이 찾아냈는지 보여줘요. 예: 위험 소음 10개 중 9개를 잡았다면 90%예요!</span></span>, <b>F1-score</b><span class="tooltip">ℹ️<span class="tooltiptext">F1-score는 정밀도와 재현율을 합쳐서 모델의 균형 잡힌 성능을 보여줘요. 높을수록 좋답니다!</span></span>, <b>혼동 행렬(Confusion Matrix)</b><span class="tooltip">ℹ️<span class="tooltiptext">혼동 행렬은 모델이 어떤 소음을 잘 맞추고, 어떤 소음을 틀렸는지 표로 보여줘요.</span></span> 활용</li>
                        <li>학습 과정 시각화를 통해 <b>과적합</b><span class="tooltip">ℹ️<span class="tooltiptext">과적합은 모델이 학습 데이터를 너무 잘 외워서 새로운 소음을 잘 못 맞추는 경우를 말해요.</span></span> 여부 검토 (Loss 및 Accuracy 그래프 분석)</li>
                        <li>증강 데이터가 성능에 미치는 영향을 비교 분석</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
                    ✅ <b>모델의 장점</b>
                    <ul style="list-style-type: disc; padding-left: 20px;">
                        <li>기존 CNN보다 깊은 네트워크 구조를 안정적으로 학습 가능</li>
                        <li><b>잔차 학습(Residual Learning)</b><span class="tooltip">ℹ️<span class="tooltiptext">잔차 학습은 ResNet의 핵심으로, 모델이 쉬운 부분만 새로 배우고 어려운 부분은 건너뛰게 해서 학습을 쉽게 만들어줘요!</span></span>으로 빠르고 효과적인 학습 가능</li>
                        <li>다양한 소음 패턴을 학습하여 실시간 감지에 최적화</li>
                        <li>OOD 탐지 기능을 통해 새로운 소음도 분류 가능</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

            # 3. 실험 결과 및 모델 성능
            with st.expander("3️⃣ 실험 결과 및 모델 성능", expanded=False):
                st.subheader("🔹 소음 분류 모델 성능")
                st.markdown("""
                - 🎯 **정확도(Accuracy)**: 96.97%
                """)

                # 표 생성을 위한 데이터
                performance_data = {
                    "소음 종류": ["이륜차 경적", "이륜차 주행음", "차량 경적", "차량 사이렌", "차량 주행음", "기타 소음"],
                    "정밀도": [0.95, 0.93, 0.98, 0.95, 0.92, 0.99],
                    "재현율": [0.98, 0.90, 0.91, 0.98, 0.96, 0.99],
                    "F1-score": [0.96, 0.92, 0.94, 0.96, 0.94, 0.99],
                    "Support": [90, 90, 90, 90, 90, 540]
                }
                df_performance = pd.DataFrame(performance_data)

                # 테이블 생성
                fig_table = go.Figure(data=[go.Table(
                    header=dict(
                        values=["<b>소음 종류</b>", "<b>정밀도</b>", "<b>재현율</b>", "<b>F1-score</b>", "<b>Support</b>"],
                        fill_color='gray',
                        align='center',
                        font=dict(color='white', size=14)
                    ),
                    cells=dict(
                        values=[df_performance["소음 종류"], df_performance["정밀도"], df_performance["재현율"], 
                                df_performance["F1-score"], df_performance["Support"]],
                        fill_color='white',
                        align='center',
                        font=dict(color='#333333', size=12),
                        height=30
                    )
                )])
                fig_table.update_layout(title="🗒️ 분류 보고서 (Classification Report)", width=800, height=400)
                st.plotly_chart(fig_table, use_container_width=True, key="table_tab2")

                # 혼동 행렬
                st.markdown("##### 혼동 행렬 (Confusion Matrix)")
                confusion_matrix = np.array([[88, 0, 2, 0, 0, 0], [0, 81, 0, 1, 6, 2], [5, 0, 82, 2, 0, 1],
                                            [0, 1, 0, 88, 0, 1], [0, 2, 0, 1, 86, 1], [0, 3, 0, 1, 1, 535]])
                fig_cm = px.imshow(confusion_matrix, text_auto=True, labels=dict(x="Predicted Label", y="True Label", color="Count"),
                                x=["이륜차 경적", "이륜차 주행음", "차량 경적", "차량 사이렌", "차량 주행음", "기타 소음"],
                                y=["이륜차 경적", "이륜차 주행음", "차량 경적", "차량 사이렌", "차량 주행음", "기타 소음"],
                                color_continuous_scale="Greys")
                fig_cm.update_layout(height=500, width=600)
                st.plotly_chart(fig_cm, use_container_width=True, key="cm_tab2")

        # 탭 3: 개발진 소개 (기존 유지)
        with tab3:
            # 박은서 소개
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://avatars.githubusercontent.com/EunSeo35", width=100)
            with col2:
                st.markdown("""
                <h3 style="color: #000000; font-family: 'Arial', sans-serif;">박은서</h3>
                <a href="https://github.com/EunSeo35" target="_blank">
                    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="25" alt="GitHub Logo" />
                </a>                   
                <p style="font-size: 16px;margin-top: 10px;">데이터 엔지니어, 웹 개발자 </p>
                """, unsafe_allow_html=True)

            st.write("---")

            # 노은비 소개
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://avatars.githubusercontent.com/selina7704", width=100)
            with col2:
                st.markdown("""
                <h3 style="color: #000000; font-family: 'Arial', sans-serif;">노은비</h3>
                <a href="https://github.com/selina7704" target="_blank">
                    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="25" alt="GitHub Logo" />
                </a>                   
                <p style="font-size: 16px;margin-top: 10px;">데이터 엔지니어, 웹 개발자 </p>
                """, unsafe_allow_html=True)
            
            st.write("---")
            
            # 엄기영 소개
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://avatars.githubusercontent.com/Eomcoco", width=100)
            with col2:
                st.markdown("""
                <h3 style="color: #000000; font-family: 'Arial', sans-serif;">엄기영</h3>
                <a href="https://github.com/Eomcoco" target="_blank">
                    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="25" alt="GitHub Logo" />
                </a>               
                <p style="font-size: 16px;margin-top: 10px;">데이터 분석가, 웹 개발자</p>
                """, unsafe_allow_html=True)
                
            st.write("---")
            
            # 두지원 소개
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://avatars.githubusercontent.com/JiwonDu", width=100)
            with col2:
                st.markdown("""
                <h3 style="color: #000000; font-family: 'Arial', sans-serif;">두지원</h3>
                <a href="https://github.com/JiwonDu" target="_blank">
                    <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="25" alt="GitHub Logo" />
                </a>               
                <p style="font-size: 16px;margin-top: 10px;">데이터 분석가, 웹 개발자</p>
                """, unsafe_allow_html=True)

if __name__ == '__main__':
    m = About_page()
    m.about_page()