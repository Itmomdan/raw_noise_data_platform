import streamlit as st
import requests
import os
import time
from gtts import gTTS
import base64
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 저장 디렉토리 설정
upload_folder = "uploads"
audio_save_path = "recorded_audio"
os.makedirs(upload_folder, exist_ok=True)
os.makedirs(audio_save_path, exist_ok=True)

# FastAPI 서버 주소
FASTAPI_URL = "http://localhost:8006/predict/"

# TTS 음성 생성 함수
def generate_tts(text, filename="alert.wav"):
    tts = gTTS(text=text, lang='ko', slow=False)
    tts.save(filename)
    return filename

# 오디오 자동 재생 함수
def autoplay_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        audio_html = f"""
            <audio autoplay src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

# 이메일 발송 함수
def send_email(to_email, subject, message):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

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
        st.success("✅ 긴급 이메일이 전송되었습니다!")
    except Exception as e:
        st.error(f"❌ 이메일 전송 실패: {e}")

# 경고 메시지 표시 함수
def show_alert(message, level="warning", play_tts=True):
    color = "#ffcc00" if level == "warning" else "#ff4d4d"
    text_color = "black" if level == "warning" else "white"
    icon = "⚠️" if level == "warning" else "🚨"
    
    st.markdown(
        f"""
        <div style='background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; color: {text_color}; font-size: 1.3em; font-weight: bold; margin: 15px 0;'>
            {icon} {message} {icon}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if play_tts and st.session_state['tts_enabled']:
        st.session_state['tts_queue'].append(message)

# 소음 강도 게이지 함수
def display_noise_gauge(label, value, max_value=120):
    if value <= 50:
        color = "#3498db"
    elif value <= 70:
        color = "#ffcc00"
    else:
        color = "#ff4d4d"
    
    st.write(f"{label}: {value} dB")
    st.markdown(
        f"""
        <div style="display: flex; align-items: center;">
            <span style="width: 30px; text-align: right; margin-right: 10px;">0</span>
            <div style="flex-grow: 1;">
                <progress value="{value}" max="{max_value}" style="width: 100%; height: 20px;">
                    <style>progress::-webkit-progress-value {{ background-color: {color}; }}</style>
                </progress>
            </div>
            <span style="width: 30px; text-align: left; margin-left: 10px;">{max_value}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 예측 결과 표시 함수
def display_prediction_result(result, elapsed_time):
    st.markdown("### 📋 분석 결과", unsafe_allow_html=True)
    st.write(f"🔊 **예측된 소음 유형:** {result.get('prediction', '알 수 없음')}")
    spl_peak = result.get('spl_peak', 0)
    display_noise_gauge("📊 최대 소음 강도", spl_peak)
    spl_rms = result.get('spl_rms', 0)
    display_noise_gauge("📊 평균 소음 강도", spl_rms)
    st.write(f"📏 **추정 거리:** {result.get('estimated_distance', 'N/A')} 미터")
    st.write(f"📡 **방향:** {result.get('direction', '알 수 없음')}")
    st.write(f"⏱️ **분석 소요 시간:** {elapsed_time:.2f} 초")
    return spl_peak

# TTS 순차 재생 함수
def play_tts_queue():
    if 'tts_queue' in st.session_state and st.session_state['tts_queue']:
        for text in st.session_state['tts_queue']:
            tts_file = generate_tts(text)
            autoplay_audio(tts_file)
            os.remove(tts_file)
            time.sleep(5)  # TTS 간 2초 간격
        st.session_state['tts_queue'] = []

# 타이머 표시 함수
def display_timer(start_time, duration=300):
    timer_container = st.empty()
    bar_container = st.empty()
    
    end_time = start_time + duration
    while time.time() < end_time:
        elapsed = time.time() - start_time
        remaining_time = max(duration - elapsed, 0)
        remaining_percentage = (remaining_time / duration) * 100
        
        with timer_container:
            st.write(f"남은 시간: {int(remaining_time // 60)}분 {int(remaining_time % 60)}초")
        with bar_container:
            st.progress(remaining_percentage / 100)
        
        time.sleep(5)
    
    if remaining_time <= 0 and not st.session_state['email_sent'] and st.session_state['sos_email_enabled']:
        send_email(
            "itmomdan0328@gmail.com",
            "🚨 긴급 소음 경고",
            "위험 수준 소음이 감지되었으나 5분 이상 응답이 없습니다. 안전을 확인해주세요!"
        )
        st.session_state['email_sent'] = True
        st.session_state['danger_alert_time'] = None
        timer_container.empty()
        bar_container.empty()

# 예측 결과 처리 함수
def process_prediction(response, mode):
    if response.status_code == 200:
        result = response.json()
        if "error" in result:
            show_alert("오디오 분석에 실패했습니다", "danger")
            return None, None
        
        end_time = time.time()
        elapsed_time = end_time - st.session_state['start_time']
        
        st.session_state[f'{mode}_result'] = result
        st.session_state[f'{mode}_elapsed_time'] = elapsed_time
        
        return result, elapsed_time
    return None, None

# 커스텀 스타일
st.markdown("""
    <style>
    div.stButton > button {
        background-color: #2c3e50;
        color: white;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        border: none;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    div.stButton > button:hover {
        background-color: #ffcc00;
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

class NoiseModel_page:
    def noisemodel_page(self):
        # 상태 초기화
        if 'tts_enabled' not in st.session_state:
            st.session_state['tts_enabled'] = True
        if 'sos_email_enabled' not in st.session_state:
            st.session_state['sos_email_enabled'] = True
        if 'start_time' not in st.session_state:
            st.session_state['start_time'] = None
        if 'background_audio' not in st.session_state:
            st.session_state['background_audio'] = None
        if 'danger_alert_time' not in st.session_state:
            st.session_state['danger_alert_time'] = None
        if 'email_sent' not in st.session_state:
            st.session_state['email_sent'] = False
        if 'tts_queue' not in st.session_state:
            st.session_state['tts_queue'] = []


        tab1, tab2 = st.tabs(['소음 분류기', '알람 기준 설정'])

        with tab1:                        # 설명서 적용
            st.markdown("### 소음 분류기 사용 방법", unsafe_allow_html=True)
            st.write("이곳에서 소음을 녹음하거나 파일을 업로드해 분석할 수 있습니다.")
            st.write("분석 결과로 소음 유형과 강도를 확인할 수 있어요!")
            st.write("""🚗 도로에서 나는 소음을 확인하고 싶나요? \n
                 🔔 경적, 사이렌, 주행음, 기타 소음을 구분해 분석해 줍니다!""")
            with st.expander("📖 소음 분류기 사용 매뉴얼 자세히 보기"):
                st.subheader("1️⃣ 소음 분류기란?")
                st.write("소음 분류기는 소리를 녹음하거나 파일을 업로드해 분석하는 서비스입니다.")
                st.write("🚗 도로 소음 / 🚨 경적·사이렌 / 🏭 기타 소음 등 다양한 소리를 인식하고, 결과를 제공합니다.")
                st.write("📢 분석된 소음이 사용자 설정 기준을 초과하면 경고 메시지와 긴급 알림을 보낼 수 있습니다.")

                st.subheader("2️⃣ 사용 방법 (단계별 가이드)")
                st.write("**🎙 1. 소음 녹음 방식**")
                st.write("""직접 소리를 녹음해 분석하는 방법입니다. 👉 녹음 버튼을 누르고, 원하는 소리를 녹음한 뒤 정지하세요.""")
                st.write("&nbsp;&nbsp;① &nbsp;***배경 소음 녹음 (5초 이상 권장)***")
                st.write("- 기본적인 주변 소음을 녹음하면 분석 정확도를 높일 수 있습니다.")
                st.write("&nbsp;&nbsp;②&nbsp;***목표 소음 녹음***")
                st.write("- 분석하고 싶은 소리를 녹음하세요. 50cm~1m 거리에서 녹음하는 것이 가장 정확합니다.")
                st.warning("""📌 녹음할 때 유의할 점\n\n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ✔ 녹음 환경: 너무 시끄러운 곳에서는 원하는 소음이 묻힐 수 있어요.\n\n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ✔ 마이크 품질: 이어폰 마이크보다는 스마트폰 내장 마이크를 사용하는 것이 더 좋아요.""")

                st.subheader("3️⃣ 분석 결과 확인하기")
                st.code("""
예시)
🔊 예측된 소음 유형: 차량 주행음
📊 최대 소음 강도 (dB): 77.5
📊 평균 소음 강도 (dB): 57.73
📏 추정 거리: 23.1 미터
📡 방향: 중앙
⏱️ 분석 소요 시간: 0.20 초
            """)
                st.write("📌 참고: '방향'은 소리가 어디서 들리는지를 알려줍니다. \n\n- 하지만 한쪽 소리만 들리는 파일(모노 타입)로는 방향을 알 수 없어요. \n\n -  양쪽 소리가 모두 담긴 파일(스테레오 타입)을 사용하면 소리가 왼쪽, 오른쪽, 또는 중앙에서 나는지 예측할 수 있습니다!")

                st.subheader("4️⃣ 경고 및 알림 기능")
                st.write("📫 사용자가 설정한 기준에 따라 경고 메시지를 제공합니다.")
                st.code("""
🚨 위험 수준 소음 감지! 즉시 조치가 필요합니다 🚨
⚠️ 주의 요함! 소음이 높습니다 ⚠️
                        """)
                st.write("📌 TTS (음성 안내 기능) 지원: \n\n - 경고 메시지는 음성으로 자동 안내됩니다. \n\n - '소음 분류기 사용 방법' 아래의 'TTS 알림' 토글로 켜거나 끌 수 있으며, 설정은 다음 분석에도 유지됩니다!")
                st.write("📌 긴급 메시지 기능: \n\n - 위험 수준 소음이 감지되면 '안전 확인' 버튼이 나타납니다. \n\n - 5분 이상 응답이 없으면 등록된 이메일로 긴급 알림이 자동 발송됩니다.")

                st.subheader("💡 자주하는 질문 (FAQ)")
                st.write("**Q1. 분석 결과가 이상해요!**")
                st.write("👉 녹음된 소리가 너무 짧거나 음질이 낮으면 분석이 부정확할 수 있어요. 배경 소음 없이 녹음해 주세요!")
                st.write("**Q2. MP3 파일도 업로드할 수 있나요?**")
                st.write("👉 현재는 WAV 파일만 지원하고 있어요. MP3 파일을 변환한 뒤 업로드해 주세요.")
                st.write("**Q3. 실시간으로 소음을 분석할 수도 있나요?**")
                st.write("👉 현재는 녹음된 소리만 분석 가능하지만, 향후 실시간 분석 기능을 추가할 예정이에요!")
                st.write("**Q4: 소음 분류기가 작동하지 않을 때는 어떻게 하나요?**")
                st.write("👉 인터넷 연결을 확인하고, WAV 파일이 16kHz인지 확인하세요. 문제가 지속되면 관리자에게 문의해주세요.")
                st.write("**Q5: 배경 소음은 꼭 녹음해야 하나요?**")
                st.write("👉 필수는 아니지만, 배경 소음을 제공하면 분석 정확도가 높아집니다.")
                st.write("**Q6: SOS 메일이 오지 않아요. 어떻게 해야 하나요?**")
                st.write("👉 SOS 메일 발송이 켜져 있는지 확인하고, 이메일 설정이 올바른지 점검하세요.")

            col1, col2 = st.columns(2)
            with col1:
                st.session_state['tts_enabled'] = st.toggle(
                    "🔊 TTS 알림", 
                    value=st.session_state['tts_enabled'], 
                    help="경고 메시지 및 분석 결과를 음성으로 들을 수 있는 기능입니다. \n\n 클릭하여 음성 알림을 켜거나 끕니다."
                )
            with col2:
                st.session_state['sos_email_enabled'] = st.toggle(
                    "📧 SOS 메시지 발송", 
                    value=st.session_state['sos_email_enabled'], 
                    help="경고 메시지 제공 후 사용자가 5분간 반응이 없을 경우 SOS 메시지가 발송되는 기능입니다. \n\n 클릭하여 SOS 메시지 기능능을 켜거나 끕니다."
                )
            st.divider()

            with st.expander("🎙 녹음 방식", expanded=True):
                st.subheader("1️⃣ 배경 소음 녹음")
                background_audio = st.audio_input("🎤 배경 소음 녹음 시작 (5초 이상 권장)", key="background_audio_tab1")
                if background_audio:
                    background_path = os.path.join(audio_save_path, "background_audio.wav")
                    with open(background_path, "wb") as f:
                        f.write(background_audio.getvalue())
                    st.session_state['background_audio'] = background_audio
                    st.success(f"📂 배경 소음 저장: {background_path}")

                st.subheader("2️⃣ 실제 소음 녹음")
                audio_data = st.audio_input("🎤 목표 소음 녹음 시작", key="target_audio_tab1")
                if audio_data:
                    file_path = os.path.join(audio_save_path, "recorded_audio.wav")
                    with open(file_path, "wb") as f:
                        f.write(audio_data.getvalue())
                    st.success(f"📂 오디오 저장: {file_path}")

                    if st.button("🎙 음성 예측하기", key="predict_recording_tab1", use_container_width=True):
                        st.session_state['start_time'] = time.time()
                        st.session_state['danger_alert_time'] = None
                        st.session_state['email_sent'] = False
                        st.session_state['tts_queue'] = []
                        status_placeholder = st.empty()
                        with status_placeholder:
                            st.spinner("🔊 분석 중...")
                        files = {"file": ("recorded_audio.wav", audio_data.getvalue(), "audio/wav")}
                        if st.session_state['background_audio']:
                            files["background"] = ("background_audio.wav", st.session_state['background_audio'].getvalue(), "audio/wav")
                        response = requests.post(FASTAPI_URL, files=files)
                        result, elapsed_time = process_prediction(response, mode="recording")
                        status_placeholder.write("✅ 분석 완료!")
                        
                        if result:
                            spl_peak = display_prediction_result(result, elapsed_time)
                            
                            if spl_peak >= 70:
                                show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            elif spl_peak >= 50:
                                show_alert("주의 요함: 지속적 노출 위험", "warning")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            
                            play_tts_queue()

                            if spl_peak >= 70 and st.session_state['sos_email_enabled']:
                                if not st.session_state['danger_alert_time']:
                                    st.session_state['danger_alert_time'] = time.time()
                                
                                if st.button("✅ 안전 확인", key="safety_check_recording", use_container_width=True):
                                    st.session_state['danger_alert_time'] = None
                                    st.session_state['email_sent'] = False
                                    st.success("✅ 안전 확인됨")
                                else:
                                    st.warning("5분 동안 안전 확인 버튼을 누르지 않으면 SOS 메일이 발송됩니다.")
                                    display_timer(st.session_state['danger_alert_time'])

            with st.expander("📁 파일 업로드 방식", expanded=True):
                uploaded_file = st.file_uploader("📂 음성 파일 업로드", type=["wav"], key="uploader_tab1")
                if uploaded_file:
                    st.audio(uploaded_file, format='audio/wav')
                    upload_path = os.path.join(upload_folder, uploaded_file.name)
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    st.success(f"📂 파일 저장: {upload_path}")
                    
                    if st.button("🎙 음성 예측하기", key="predict_upload_tab1", use_container_width=True):
                        st.session_state['start_time'] = time.time()
                        st.session_state['danger_alert_time'] = None
                        st.session_state['email_sent'] = False
                        st.session_state['tts_queue'] = []
                        status_placeholder = st.empty()
                        with status_placeholder:
                            st.spinner("🔊 분석 중...")
                        response = requests.post(FASTAPI_URL, files={"file": uploaded_file})
                        result, elapsed_time = process_prediction(response, mode="upload")
                        status_placeholder.write("✅ 분석 완료!")
                        
                        if result:
                            spl_peak = display_prediction_result(result, elapsed_time)
                            
                            if spl_peak >= 70:
                                show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            elif spl_peak >= 50:
                                show_alert("주의 요함: 지속적 노출 위험", "warning")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            
                            play_tts_queue()

                            if spl_peak >= 70 and st.session_state['sos_email_enabled']:
                                if not st.session_state['danger_alert_time']:
                                    st.session_state['danger_alert_time'] = time.time()
                                
                                if st.button("✅ 안전 확인", key="safety_check_upload", use_container_width=True):
                                    st.session_state['danger_alert_time'] = None
                                    st.session_state['email_sent'] = False
                                    st.success("✅ 안전 확인됨")
                                else:
                                    st.warning("5분 동안 안전 확인 버튼을 누르지 않으면 SOS 메일이 발송됩니다.")
                                    display_timer(st.session_state['danger_alert_time'])

        with tab2:
            st.subheader("알람 기준 설정")
            st.write("현재는 기본 설정(위험: 70dB, 주의: 50dB)으로 작동 중입니다.")

if __name__ == '__main__':
    m = NoiseModel_page()
    m.noisemodel_page()