import streamlit as st
import Home, Dashboard, Mypage

def run():
    st.title("🔊 Noise Classifier")
    st.write("🔍 **소음 분석 AI**에 오신 것을 환영합니다!\n이곳에서 다양한 소음을 분석하고, 그 유형을 예측해볼 수 있어요.")


    # # 사이드바에 버튼 생성
    # col1, col2, col3 = st.sidebar.columns(3)
    # with col1:
    #     if st.button("🏠 Home"):
    #         Home.run()
    # with col2:
    #     if st.button("📊 Dashboard"):
    #         Dashboard.run()
    # with col3:
    #     if st.button("👤 My Page"):
    #         Mypage.run()
    if st.sidebar.button("🏠 Home"):
        Home.run()

    st.sidebar.empty()

    if st.sidebar.button("📊 Dashboard"):
        Dashboard.run()

    st.sidebar.empty()

    if st.sidebar.button("👤 My Page"):
        Mypage.run()

    # 사용 설명서
    st.header("📖 소음 분류기 사용 설명서")

    st.markdown(
        """
        **Noise Classifier는 다음과 같은 기능을 제공합니다!**  
        
        **🎤 실시간 녹음**: 마이크를 통해 실시간으로 소음을 녹음하고 분석해요!  
        **📂 파일 업로드**: WAV 형식의 음성 파일을 업로드해서 분석할 수 있어요.  
        **🔍 소음 유형 예측**: 입력된 오디오에서 소음 유형을 AI가 예측합니다.  
        **⚠️ 위험도 평가**: 소음 크기(dB)를 측정하고, 위험 수준을 알려줘요!  
        
        ---  
        
        **🛠️ 사용 방법**  

        **사이드바**에서 **Noise Classifier**를 선택하세요.  
        **🎙️ 실시간 녹음** 또는 **📁 파일 업로드** 방식을 선택하세요.  
        **실시간 녹음**을 선택하면 마이크로 소음을 녹음한 뒤 **[녹음 데이터 분석]** 버튼을 눌러주세요.  
        **파일 업로드**를 선택하면 WAV 파일을 추가하고 **[음성 예측하기]** 버튼을 클릭하세요.  
        🔹 📊 분석 결과가 화면에 표시됩니다!  

        ---  

        **⚠️ 주의사항**  
        
        🚨 **정확한 분석을 위해 다음을 유의하세요!**  
        ✅ 잡음이 적은 환경에서 녹음하면 결과가 더 정확해요!  
        ✅ 고품질의 WAV 음성 파일을 사용하면 분석 정확도가 올라갑니다.  
        ✅ FastAPI 서버가 정상적으로 실행 중인지 꼭 확인하세요!  

        이제 직접 사용해보세요! 🔥  
        """
    )
if __name__ == "__main__":
    run()