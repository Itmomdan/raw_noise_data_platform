import streamlit as st
import requests
import os
import time
import streamlit.components.v1 as components
from gtts import gTTS
import base64
import smtplib
from email.mime.text import MIMEText

# FastAPI 서버 주소
FASTAPI_URL = "http://localhost:8005/predict/"

# 저장 디렉토리 설정
upload_folder = "uploads"
audio_save_path = "recorded_audio"
os.makedirs(upload_folder, exist_ok=True)
os.makedirs(audio_save_path, exist_ok=True)

# 세션 상태 초기화
if 'stop_audio' not in st.session_state:
    st.session_state['stop_audio'] = False

# TTS 음성 알림 생성 함수
def generate_tts(text, filename="alert.wav"):
    tts = gTTS(text=text, lang='ko', slow=False)
    tts.save(filename)
    return filename

# 오디오 자동 재생 컴포넌트
def autoplay_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        audio_html = f"""
            <audio autoplay src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)


def send_email(to_email, subject, message):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587 #465
    sender_email = "itmomdan0328@gmail.com"  # 자신의 Gmail 주소
    sender_password = "dhvfbjqqhkxlkhzt" #os.environ.get("dhvfbjqqhkxlkhzt")  # 앱 비밀번호 사용 (구글 계정 보안 설정 필요)

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print("✅ 이메일 전송 완료!")
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 이메일 전송 실패: 인증 오류 - {e}")
    except smtplib.SMTPException as e:
        print(f"❌ 이메일 전송 실패: SMTP 오류 - {e}")
    except Exception as e:
        print(f"❌ 이메일 전송 실패: 기타 오류 - {e}")




# 경고 메시지 + 음성 알림 통합 함수
def show_alert(message, level="warning"):
    # 시각적 경고
    color = "#ffcc00" if level == "warning" else "#ff4d4d"
    text_color = "black" if level == "warning" else "white"
    icon = "⚠️" if level == "warning" else "🚨"
    
    st.markdown(
        f"""
        <style>
        @keyframes blink {{
            0% {{ background-color: {color}; }}
            50% {{ background-color: transparent; }}
            100% {{ background-color: {color}; }}
        }}
        .blink-alert {{
            animation: blink 1s linear infinite;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            color: {text_color};
            font-size: 1.5em;
            margin: 20px 0;
        }}
        </style>
        <div class="blink-alert">
            {icon} {message} {icon}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # 음성 알림
    if not st.session_state['stop_audio']:
        alert_sound = generate_tts(message)
        autoplay_audio(alert_sound)
        os.remove(alert_sound)  # 임시 파일 정리
        time.sleep(3)

# 예측 결과 처리 함수
def process_prediction(response):
    if response.status_code == 200:
        result = response.json()
        if "error" in result:
            show_alert("오디오 분석에 실패했습니다", "danger")
            return
        
        st.success("✅ 분석 결과")
        st.write(f"**유형**: {result.get('prediction', '알 수 없음')}")
        st.write(f"**소음 강도**: {result.get('spl', 0)} dB")
        st.write(f"**추정 위치**: {result.get('estimated_distance', 'N/A')}m")
        st.write(f"**추정 방향**: {result.get('direction', '알 수 없음')}")

        noise_type = result.get('prediction', '알 수 없음')
        spl = result.get('spl', 0)
        distance = result.get('estimated_distance', 'N/A')
        direction = result.get('direction', '알 수 없음')

        # 위험도 평가
        if spl >= 70:
            show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
            alert_message = f"🚨위험 수준 소음 감지!🚨 소음 유형: {noise_type}, 강도: {spl}dB, 위치: {distance}m, 방향: {direction}"
            send_email("itmomdan0328@gmail.com", "소음 경고", alert_message)  # 이메일 전송
           
        elif spl >= 50:
            show_alert("주의 요함: 지속적 노출 위험", "warning")
            alert_message = f"⚠️주의 요함!⚠️ 소음 유형: {noise_type}, 강도: {spl}dB, 위치: {distance}m, 방향: {direction}"
            send_email("itmomdan0328@gmail.com", "소음 경고", alert_message)  # 이메일 전송
        
        # 경고 후 항상 소음 유형 안내
        if not st.session_state['stop_audio']:
            info_text = f"소음 유형은 {noise_type}입니다. 현재 소음 강도는 {spl} 데시벨로 측정되었으며, 약 {distance} 미터 거리에서 발생하고 있습니다."
            info_sound = generate_tts(info_text)
            autoplay_audio(info_sound)
            os.remove(info_sound)
    else:
        show_alert("서버 연결 오류 발생", "danger")

# 메인 앱 인터페이스
def main():
    st.title("🔊 스마트 소음 감지 시스템")
    
    # 배경색 애니메이션
    animation_html = """
    <script>
        document.body.style.transition = "background-color 2s";
        document.body.style.backgroundColor = "#ffcc00";
        setTimeout(() => {
            document.body.style.backgroundColor = "white";
        }, 2000);
    </script>
    """
    st.components.v1.html(animation_html, height=0)

    # 파일 업로드 섹션
    with st.expander("📁 파일 업로드 방식", expanded=True):
        uploaded_file = st.file_uploader("WAV 파일 선택", type=["wav"])
        if uploaded_file and st.button("업로드 파일 분석"):
            with st.spinner("분석 중..."):
                # 파일 처리 및 분석 로직
                response = requests.post(FASTAPI_URL, files={"file": uploaded_file})
                process_prediction(response)
    
    # 실시간 녹음 섹션
    with st.expander("🎙 녹음 방식", expanded=True):
        audio_data = st.audio_input("음성 입력")
                
        if audio_data:

            st.success(f"📂 녹음된 오디오가 저장되었습니다: ")

            if  st.button("녹음 데이터 분석"):
                with st.spinner("분석 진행 중..."):
                    # 녹음 데이터 처리
                    response = requests.post(FASTAPI_URL, files={"file": audio_data})
                    process_prediction(response)

    # Stop Audio 버튼: 실시간 녹음 섹션 바깥으로 이동
    st.session_state['stop_audio'] = st.button("🛑 Stop Audio")

if __name__ == "__main__":
    main()