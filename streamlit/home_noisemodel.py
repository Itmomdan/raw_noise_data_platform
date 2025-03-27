import streamlit as st
import requests
import os
import time
from gtts import gTTS
import base64
import smtplib
from email.mime.text import MIMEText
import pandas as pd
from datetime import datetime
import mysql.connector
from streamlit_javascript import st_javascript
import config
from config import DB_CONFIG

# 이메일 발송에 사용할 sender 정보
sender_email = config.SENDER_EMAIL
sender_password = config.SENDER_PASSWORD

# 파일 저장 경로 설정
upload_folder = "uploads"
audio_save_path = "recorded_audio"
os.makedirs(upload_folder, exist_ok=True)
os.makedirs(audio_save_path, exist_ok=True)

# FastAPI 엔드포인트 URL
FASTAPI_URL = "http://15.168.145.74:8008/predict/"


# TTS 생성 함수
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

# 사용자 정보 가져오기
def get_user_info(user_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, name, guardian_email FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# 주소를 위도/경도로 변환
def geocode_address(address):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
    headers = {"User-Agent": "DamassoNoiseApp/1.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
            else:
                st.error(f"❌ 주소 검색 실패: '{address}'에 대한 결과가 없습니다.")
                return None, None
        else:
            st.error(f"❌ Nominatim API 오류: 상태 코드 {response.status_code}")
            return None, None
    except Exception as e:
        st.error(f"❌ 주소 변환 중 오류: {str(e)}")
        return None, None

# 소음 분류 결과를 DB에 저장
def save_to_classification_results(user_id, result, latitude, longitude, audio_path, elapsed_time, timestamp):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    query = """
        INSERT INTO classification_results 
        (user_id, noise_type, spl_peak, spl_rms, estimated_distance, direction, alarm_trigger, latitude, longitude, alarm_triggered, audio_path, elapsed_time, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    distance = result.get('estimated_distance', 'N/A')
    if isinstance(distance, (int, float)):
        estimated_distance = float(distance)
    elif isinstance(distance, str) and distance != 'N/A':
        try:
            estimated_distance = float(''.join(filter(str.isdigit, distance)))
        except ValueError:
            estimated_distance = None
    else:
        estimated_distance = None

    # 사용자 설정값 가져오기
    predicted_noise_type = result.get('prediction', '알 수 없음')
    alarm_settings = get_alarm_settings(user_id, predicted_noise_type)

    # `alarm_db` 설정값이 없으면 기본값(70dB) 사용
    if alarm_settings:
        alarm_db, sensitivity_level = alarm_settings
    else:
        alarm_db = 70  # 기본값
        st.warning(f"🚨 `{predicted_noise_type}`에 대한 사용자 설정값이 없음. 기본값 {alarm_db}dB 사용")

    alarm_trigger = datetime.now() if result.get('spl_peak', 0) >= alarm_db else None
    alarm_triggered = 1 if result.get('spl_peak', 0) >= alarm_db else 0
    values = (
        user_id,
        result.get('prediction', '알 수 없음'),
        result.get('spl_peak', 0),
        result.get('spl_rms', 0),
        estimated_distance,
        result.get('direction', '알 수 없음'),
        alarm_trigger,
        latitude,
        longitude,
        alarm_triggered,
        audio_path,
        elapsed_time,
        timestamp
    )
    try:
        cursor.execute(query, values)
        conn.commit()
        #st.success("✅ DB에 저장 완료")
    except mysql.connector.Error as e:
        st.error(f"❌ DB 저장 오류: {str(e)}")
    finally:
        conn.close()

# 이메일 발송 함수
def send_email(to_email, subject, message):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = config.SENDER_EMAIL
    sender_password = config.SENDER_PASSWORD

    if not sender_email or not sender_password:
        st.error("❌ SENDER_EMAIL 또는 SENDER_PASSWORD가 설정되지 않았습니다!")
        return False

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        st.success("✅ 긴급 이메일이 전송되었습니다!")
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ 인증 오류: Gmail 앱 비밀번호가 잘못되었거나 계정 설정을 확인해주세요!")
        return False
    except smtplib.SMTPException as e:
        st.error(f"❌ SMTP 오류: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ 기타 오류: {str(e)}")
        return False

# SOS 이메일 발송
def send_sos_email(user_id, result, address=None, latitude=None, longitude=None):
    user_info = get_user_info(user_id)
    if not user_info or not user_info.get('guardian_email'):
        st.error("❌ 보호자 이메일이 등록되지 않았습니다.")
        return False

    noise_type = result.get('prediction', '알 수 없음')
    spl_peak = result.get('spl_peak', 0)
    spl_rms = result.get('spl_rms', 0)
    distance = result.get('estimated_distance', 'N/A')
    direction = result.get('direction', '알 수 없음')
    timestamp = result.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
    location = f"{address} (위도: {latitude}, 경도: {longitude})" if address else "위치 정보 없음"

    subject = "📢 긴급 SOS 알림"
    message = f"""
보호자님, 안녕하세요.

[{user_info['name']}]님이 위험 상황에 처해 있어 긴급 연락을 드립니다.

📍 위치: {location}
🔊 감지된 소음 유형: {noise_type}
📊 최대 소음 강도: {spl_peak} dB
📊 평균 소음 강도: {spl_rms} dB
📏 추정 거리: {distance} 미터
📡 방향: {direction}
⏰ 발생 시각: {timestamp}

⚠️ 즉시 확인이 필요합니다.

필요 시 즉시 연락 부탁드립니다.

감사합니다.
[Damasso Noise Platform]
"""
    return send_email(user_info['guardian_email'], subject, message)

# 알림 메시지 표시
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

# 소음 게이지 표시
def display_noise_gauge(label, value, max_value=120):
    if value <= 50:
        color = "#009874"
    elif value <= 70:
        color = "#009874"
    else:
        color = "#009874"
    
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

# 예측 결과 표시
def display_prediction_result(result, elapsed_time, address=None, latitude=None, longitude=None):
    st.markdown("### 📋 분석 결과", unsafe_allow_html=True)
    st.write(f"🔊 **예측된 소음 유형:** {result.get('prediction', '알 수 없음')}")
    spl_peak = result.get('spl_peak', 0)
    display_noise_gauge("📊 최대 소음 강도", spl_peak)
    spl_rms = result.get('spl_rms', 0)
    display_noise_gauge("📊 평균 소음 강도", spl_rms)
    st.write(f"📏 **추정 거리:** {result.get('estimated_distance', 'N/A')} 미터")
    st.write(f"📡 **방향:** {result.get('direction', '알 수 없음')}")
    st.write(f"⏱️ **분석 소요 시간:** {elapsed_time:.2f} 초")
    if address:
        st.write(f"📍 **위치:** {address} (위도: {latitude}, 경도: {longitude})")
        df = pd.DataFrame({"lat": [latitude], "lon": [longitude]})
        st.map(df)
    return spl_peak

# TTS 큐 재생
def play_tts_queue():
    if 'tts_queue' in st.session_state and st.session_state['tts_queue']:
        for text in st.session_state['tts_queue']:
            tts_file = generate_tts(text)
            autoplay_audio(tts_file)
            os.remove(tts_file)
            time.sleep(5)
        st.session_state['tts_queue'] = []

# SOS 타이머 표시
def display_timer(start_time, user_id, result, address, latitude, longitude, duration=60):
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
        
        time.sleep(1)
    
    if remaining_time <= 1 and not st.session_state['email_sent'] and st.session_state['sos_email_enabled']:
        send_sos_email(user_id, result, address, latitude, longitude)
        st.session_state['email_sent'] = True
        st.session_state['danger_alert_time'] = None
        timer_container.empty()
        bar_container.empty()

# 예측 처리
def process_prediction(response, mode, user_id, audio_data=None, address=None, latitude=None, longitude=None, timestamp=None):
    if response.status_code == 200:
        result = response.json()
        if "error" in result:
            show_alert("오디오 분석에 실패했습니다", "danger")
            return None, None, None
        
        end_time = time.time()
        elapsed_time = end_time - st.session_state['start_time']
        
        st.session_state[f'{mode}_result'] = result
        st.session_state[f'{mode}_elapsed_time'] = elapsed_time
        
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S') if timestamp else datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_path = os.path.join(audio_save_path, f"{user_id}_{timestamp_str}.wav") if mode == "recording" else os.path.join(upload_folder, f"{user_id}_{timestamp_str}.wav")
        if audio_data:
            with open(audio_path, "wb") as f:
                f.write(audio_data.getvalue() if mode == "recording" else audio_data.read())
        
        result['timestamp'] = timestamp
        result['address'] = address
        save_to_classification_results(user_id, result, latitude, longitude, audio_path, elapsed_time, timestamp)
        
        # 저장된 오디오 경로를 세션에 저장하여 피드백 페이지 등에서 재생할 수 있도록 함
        st.session_state['audio_path'] = audio_path
        
        return result, elapsed_time, audio_path
    else:
        st.error(f"❌ FastAPI 요청 실패: 상태 코드 {response.status_code}")
        return None, None, None



# 버튼 스타일링
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

# 알람 설정 가져오기
def get_alarm_settings(user_id, noise_type):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    query = """
        SELECT alarm_db, sensitivity_level
        FROM alarm_settings
        WHERE user_id = %s AND noise_type = %s
    """
    
    cursor.execute(query, (user_id, noise_type))
    result = cursor.fetchone()
    
    
    conn.close()
    return result


# 알람 설정 저장
def save_alarm_settings(user_id, noise_type, alarm_db, sensitivity_level):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM alarm_settings WHERE user_id = %s AND noise_type = %s", (user_id, noise_type))
    existing_record = cursor.fetchone()

    if existing_record:
        query = """
            UPDATE alarm_settings
            SET alarm_db = %s, sensitivity_level = %s
            WHERE user_id = %s AND noise_type = %s
        """
        values = (alarm_db, sensitivity_level, user_id, noise_type)
        cursor.execute(query, values)
    else:
        query = """
            INSERT INTO alarm_settings (user_id, noise_type, alarm_db, sensitivity_level)
            VALUES (%s, %s, %s, %s)
        """
        values = (user_id, noise_type, alarm_db, sensitivity_level)
        cursor.execute(query, values)
    conn.commit()
    conn.close()

# 알림 트리거 체크
def check_alarm_trigger(spl_peak, user_id, noise_type):
    alarm_settings = get_alarm_settings(user_id, noise_type)
    st.write("알람 설정 값:", alarm_settings)
    
    if alarm_settings is None:
        st.error("알람 설정이 없습니다. 알람 설정을 확인해주세요.")
        return  # 알람 설정이 없으면 더 이상 진행하지 않음

    if alarm_settings:
        alarm_db, sensitivity_level = alarm_settings
        warning_threshold = alarm_db * 0.8
        if spl_peak >= alarm_db:
            if spl_peak >= alarm_db:
                alert_message = f"🚨 위험 수준 소음 감지! 최대 소음 강도는 {spl_peak} dB입니다."
                show_alert(alert_message, "danger")
            elif spl_peak >= warning_threshold:
                alert_message = f"⚠️ 주의 요함! 소음 강도가 {spl_peak} dB입니다."
                show_alert(alert_message, "warning")
    else:
            st.error("알람 설정을 가져오는 데 실패했습니다. 사용자 ID 또는 소음 유형이 잘못되었을 수 있습니다.")
            
            
# DB에서 사용자 소음 기록 가져오기
def get_classification_results(user_id, start_date=None, end_date=None, noise_type=None, page=1, per_page=10):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT result_id, noise_type, spl_peak, spl_rms, estimated_distance, direction, elapsed_time, timestamp, audio_path, latitude, longitude
        FROM classification_results
        WHERE user_id = %s
    """
    params = [user_id]
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query += " AND timestamp >= %s"
        params.append(start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query += " AND timestamp <= %s"
        params.append(end_datetime)
    
    if noise_type and noise_type != "모두":
        query += " AND noise_type = %s"
        params.append(noise_type)
    
    query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    for result in results:
        if result['latitude'] is not None:
            result['latitude'] = float(result['latitude'])
        if result['longitude'] is not None:
            result['longitude'] = float(result['longitude'])
    
    count_query = "SELECT COUNT(*) as total FROM classification_results WHERE user_id = %s"
    count_params = [user_id]
    if start_date:
        count_query += " AND timestamp >= %s"
        count_params.append(start_datetime)
    if end_date:
        count_query += " AND timestamp <= %s"
        count_params.append(end_datetime)
    if noise_type and noise_type != "모두":
        count_query += " AND noise_type = %s"
        count_params.append(noise_type)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()['total']
    
    conn.close()
    return results, total

# 피드백 저장
def save_feedback(result_id, user_id, noise_type, spl_peak, feedback, wrong_noise, audio_path, timestamp):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    query = """
        INSERT INTO feedback (result_id, user_id, noise_type, spl_peak, feedback, wrong_noise, audio_path, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (result_id, user_id, noise_type, spl_peak, feedback, wrong_noise, audio_path, timestamp)
    try:
        cursor.execute(query, values)
        conn.commit()
        st.success("피드백이 저장되었습니다")
    except mysql.connector.Error as e:
        st.error(f"❌ 피드백 저장 오류: {str(e)}")
    finally:
        conn.close()




class NoiseModel_page:
    def noisemodel_page(self):
        user_id = st.session_state['user_info']['id']
        user_info = get_user_info(user_id)

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
        if 'gps_coords' not in st.session_state:
            st.session_state['gps_coords'] = None

        tab1, tab2, tab3 = st.tabs(['소음 분류기', '소음 측정 기록', '알람 기준 설정'])

        with tab1:
            st.markdown("### 소음 분류기 사용 방법", unsafe_allow_html=True)
            st.write("이곳에서 소음을 녹음하거나 파일을 업로드해 분석할 수 있습니다.")
            st.write("분석 결과로 소음 유형, 강도과 방향을 확인할 수 있어요!")
            st.write("""🚗 도로에서 나는 소음을 확인하고 싶나요? \n
                 🔔 경적, 사이렌, 주행음, 기타 소음을 구분해 분석해 줍니다!""")
            with st.expander("📖 소음 분류기 사용 매뉴얼 자세히 보기"):
                st.subheader("1️⃣ 소음 분류기란?")
                st.write("소음 분류기는 소리를 녹음하거나 파일을 업로드해 분석하는 서비스입니다.")
                st.write("🚗 도로 소음 / 🚨 경적·사이렌 / 🏭 기타 소음 등 다양한 소리를 인식하고, 결과를 제공합니다.")
                st.write("📢 분석된 소음이 사용자 설정 기준을 초과하면 경고 메시지와 긴급 알림을 보낼 수 있습니다.")
                st.write("**지원하는 소음 유형**: 차량경적, 이륜차경적, 차량사이렌, 차량주행음, 이륜차주행음, 기타소음")

                st.subheader("2️⃣ 사용 방법 (단계별 가이드)")
                st.write("**🎙 1. 소음 녹음 방식**")
                st.write("""직접 소리를 녹음해 분석하는 방법입니다. 👉 녹음 버튼을 누르고, 원하는 소리를 녹음한 뒤 정지하세요.""")
                st.write("  ①  ***배경 소음 녹음 (5초 이상 권장)***")
                st.write("- 기본적인 주변 소음을 녹음하면 분석 정확도를 높일 수 있습니다.")
                st.write("- 예: 도로의 기본 소음, 바람 소리 등")
                st.write("  ② ***목표 소음 녹음***")
                st.write("- 분석하고 싶은 소리를 녹음하세요. 50cm~1m 거리에서 녹음하는 것이 가장 정확합니다.")
                st.write("- 예: 차량경적, 차량사이렌 등 특정 소음")
                st.info("""📌 녹음할 때 유의할 점\n\n        ✔ 녹음 환경: 너무 시끄러운 곳에서는 원하는 소음이 묻힐 수 있어요.\n\n    ✔ 마이크 품질: 이어폰 마이크보다는 스마트폰 내장 마이크를 사용하는 것이 더 좋아요.\n\n    ✔ 녹음 길이: 최소 3초 이상 녹음해야 분석이 잘 돼요!""")

                st.write("**📁 2. 파일 업로드 방식**")
                st.write("- WAV 형식의 오디오 파일을 업로드해 분석할 수 있습니다.")
                st.write("- 소음 발생 시간과 위치를 직접 입력해 기록을 남길 수 있어요.")
                st.info("📌 업로드 팁: 16kHz 샘플레이트의 WAV 파일을 사용하면 최적의 결과를 얻을 수 있어요!")

                st.subheader("3️⃣ 분석 결과 확인하기")
                st.write("분석 후 아래와 같은 정보를 제공합니다:")
                st.code("""
예시)
🔊 예측된 소음 유형: 차량경적
📊 최대 소음 강도 (dB): 85.3
📊 평균 소음 강도 (dB): 62.1
📏 추정 거리: 15.7 미터
📡 방향: 왼쪽
⏱️ 분석 소요 시간: 0.25 초
📍 위치: 서울특별시 강남구 역삼동 (위도: 37.501, 경도: 127.037)
            """)
                st.info("📌 참고: '방향'은 소리가 어디서 들리는지를 알려줍니다. \n\n- 한쪽 소리만 들리는 파일(모노 타입)로는 방향을 알 수 없어요. \n\n - 양쪽 소리가 모두 담긴 파일(스테레오 타입)을 사용하면 소리가 왼쪽, 오른쪽, 또는 중앙에서 나는지 예측할 수 있습니다!")

                st.subheader("4️⃣ 경고 및 알림 기능")
                st.write("📫 사용자가 설정한 기준에 따라 경고 메시지를 제공합니다:")
                st.code("""
🚨 위험 수준 소음 감지! 최대 소음 강도는 85.3 dB입니다 🚨
⚠️ 주의 요함! 소음 강도가 62.1 dB입니다 ⚠️
                        """)
                st.info("📌 TTS (음성 안내 기능): \n\n - 경고 메시지와 분석 결과를 음성으로 들을 수 있어요. \n\n - 'TTS 알림' 토글로 켜고 끌 수 있으며, 설정은 유지됩니다!")
                st.info("📌 SOS 메시지: \n\n - 최대 소음 강도가 70dB 이상일 때 '안전 확인' 버튼이 나타납니다. \n\n - 1분간 응답이 없으면 보호자 이메일로 SOS 메시지가 발송돼요!")

                st.subheader("💡 자주하는 질문 (FAQ)")
                st.write("**Q1. 분석 결과가 이상해요!**")
                st.warning("녹음된 소리가 너무 짧거나 음질이 낮으면 분석이 부정확할 수 있어요. 최소 3초 이상, 배경 소음 없이 녹음해 주세요!")
                st.write("**Q2. MP3 파일도 업로드할 수 있나요?**")
                st.warning("현재는 WAV 파일만 지원해요. MP3를 WAV로 변환 후 업로드해 주세요.")
                st.write("**Q3. 실시간으로 소음을 분석할 수도 있나요?**")
                st.warning("현재는 녹음 또는 업로드된 소리만 분석 가능해요. 실시간 분석은 추후 업데이트 예정입니다!")
                st.write("**Q4. 소음 분류기가 작동하지 않아요!**")
                st.warning("인터넷 연결을 확인하고, WAV 파일이 16kHz인지 체크하세요. 문제가 지속되면 관리자에게 문의해 주세요.")
                st.write("**Q5. 배경 소음은 꼭 녹음해야 하나요?**")
                st.warning("필수는 아니지만, 배경 소음을 제공하면 분석 정확도가 올라가요.")
                st.write("**Q6. SOS 메일이 오지 않아요!**")
                st.warning("SOS 메시지 발송 옵션이 켜져 있는지, 보호자 이메일이 등록되어 있는지 확인해 주세요.")

            col1, col2 = st.columns(2)
            with col1:
                st.session_state['tts_enabled'] = st.toggle(
                    "🔊 TTS 알림", 
                    value=st.session_state['tts_enabled'], 
                    help="경고 메시지 및 분석 결과를 음성으로 들을 수 있는 기능입니다."
                )
            with col2:
                st.session_state['sos_email_enabled'] = st.toggle(
                    "📧 SOS 메시지 발송", 
                    value=st.session_state['sos_email_enabled'], 
                    help="경고 후 1분간 반응이 없으면 SOS 메시지가 발송됩니다."
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
                    #st.success(f"📂 오디오 저장: {file_path}")
                    recording_timestamp = datetime.now()
                    st.write(f"⏰ 녹음 완료 시간: {recording_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

                    location = st_javascript("navigator.geolocation.getCurrentPosition((pos) => pos.coords.latitude + ',' + pos.coords.longitude)")
                    latitude, longitude, address = None, None, None
                    if location and isinstance(location, str):
                        lat, lon = location.split(",")
                        latitude, longitude = float(lat), float(lon)
                        st.session_state['gps_coords'] = (latitude, longitude)
                        st.success(f"📍 GPS 위치: 위도 {latitude}, 경도 {longitude}")
                    else:
                        st.warning("❌ GPS 위치를 가져올 수 없습니다. 주소를 입력해주세요.")
                        address = st.text_input("📍 주소를 입력하세요 (예: 서울특별시 강남구 역삼동) *필수*", "", help="소음이 발생한 위치를 입력 후 엔터키를 눌러주세요.", key="recording_address")
                        if address:
                            latitude, longitude = geocode_address(address)
                            if latitude and longitude:
                                st.success(f"📍 주소 위치: {address} (위도: {latitude}, 경도: {longitude})")

                    predict_button = st.button("🎙 음성 예측하기", key="predict_recording_tab1", use_container_width=True, disabled=not (latitude and longitude and address))
                    if predict_button and latitude and longitude and address:
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
                        result, elapsed_time, audio_path = process_prediction(
                            response, mode="recording", user_id=user_id, audio_data=audio_data,
                            address=address, latitude=latitude, longitude=longitude, timestamp=recording_timestamp
                        )
                        status_placeholder.write("✅ 분석 완료!")
                        
                        # if result:
                        #     spl_peak = display_prediction_result(result, elapsed_time, address, latitude, longitude)
                        #     check_alarm_trigger(spl_peak, user_id, result.get('prediction', '알 수 없음'))
                            
                        #     if spl_peak >= 70:
                        #         show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
                        #         if st.session_state['tts_enabled']:
                        #             tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                        #             st.session_state['tts_queue'].append(tts_text)
                        #     elif spl_peak >= 50:
                        #         show_alert("주의 요함: 지속적 노출 위험", "warning")
                        #         if st.session_state['tts_enabled']:
                        #             tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                        #             st.session_state['tts_queue'].append(tts_text)

                        if result:
                            spl_peak = display_prediction_result(result, elapsed_time, address, latitude, longitude)
                            
                            alarm_settings = get_alarm_settings(user_id, result.get('prediction', '알 수 없음'))
                            
                            if alarm_settings:
                                alarm_db = alarm_settings[0]  
                            warning_threshold = alarm_db * 0.8

                            if spl_peak >= alarm_db:
                                show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            elif spl_peak >= warning_threshold: 
                                show_alert("주의 요함: 지속적 노출 위험", "warning")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)

                            play_tts_queue()

                            if spl_peak >= alarm_db and st.session_state['sos_email_enabled']:
                                if not st.session_state['danger_alert_time']:
                                    st.session_state['danger_alert_time'] = time.time()
                                
                                if st.button("✅ 안전 확인", key="safety_check_recording", use_container_width=True):
                                    st.session_state['danger_alert_time'] = None
                                    st.session_state['email_sent'] = False
                                    st.success("✅ 안전 확인됨")
                                else:
                                    st.warning("1분 동안 안전 확인 버튼을 누르지 않으면 SOS 메일이 발송됩니다.")
                                    display_timer(st.session_state['danger_alert_time'], user_id, result, address, latitude, longitude)

            with st.expander("📁 파일 업로드 방식", expanded=True):
                uploaded_file = st.file_uploader("", type=["wav"], key="uploader_tab1")
                if uploaded_file:
                    st.audio(uploaded_file, format='audio/wav')
                    upload_path = os.path.join(upload_folder, uploaded_file.name)
                    with open(upload_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    #st.success(f"📂 파일 저장: {upload_path}")

                    st.subheader("📅 시간 및 위치 입력")
                    custom_timestamp = st.text_input(
                        "⏰ 소음 발생 시간 (예: 2025-03-23 14:30:00)", 
                        value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        help="소음이 발생한 시간을 입력하세요."
                    )
                    address = st.text_input(
                        "📍 주소를 입력하세요 (예: 서울특별시 강남구 역삼동) *필수*", 
                        "",
                        help="소음이 발생한 위치를 입력 후 엔터키를 눌러주세요."
                    )
                    latitude, longitude = None, None
                    if address:
                        latitude, longitude = geocode_address(address)
                        if latitude and longitude:
                            st.success(f"📍 주소 위치: {address} (위도: {latitude}, 경도: {longitude})")
                            df = pd.DataFrame({"lat": [latitude], "lon": [longitude]})
                            st.map(df)

                    predict_button = st.button("🎙 음성 예측하기", key="predict_upload_tab1", use_container_width=True, disabled=not (address and latitude))
                    if predict_button and latitude and longitude and address:
                        st.session_state['start_time'] = time.time()
                        st.session_state['danger_alert_time'] = None
                        st.session_state['email_sent'] = False
                        st.session_state['tts_queue'] = []
                        
                        try:
                            upload_timestamp = datetime.strptime(custom_timestamp, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            st.error("❌ 시간 형식이 잘못되었습니다. 'YYYY-MM-DD HH:MM:SS' 형식을 사용하세요.")
                            upload_timestamp = datetime.now()

                        status_placeholder = st.empty()
                        with status_placeholder:
                            st.spinner("🔊 분석 중...")
                        response = requests.post(FASTAPI_URL, files={"file": uploaded_file})
                        result, elapsed_time, audio_path = process_prediction(
                            response, mode="upload", user_id=user_id, audio_data=uploaded_file,
                            address=address, latitude=latitude, longitude=longitude, timestamp=upload_timestamp
                        )
                        status_placeholder.write("✅ 분석 완료!")
                        
                        if result:
                            spl_peak = display_prediction_result(result, elapsed_time, address, latitude, longitude)
                            
                            alarm_settings = get_alarm_settings(user_id, result.get('prediction', '알 수 없음'))
                            
                            if alarm_settings:
                                alarm_db = alarm_settings[0] 
                            
                            warning_threshold = alarm_db * 0.8

                            if spl_peak >= alarm_db:
                                show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                            elif spl_peak >= warning_threshold:
                                show_alert("주의 요함: 지속적 노출 위험", "warning")
                                if st.session_state['tts_enabled']:
                                    tts_text = f"예측된 소음 유형은 {result.get('prediction', '알 수 없음')}입니다. 최대 소음 강도는 {spl_peak} 데시벨, 평균 소음 강도는 {result.get('spl_rms', 0)} 데시벨입니다."
                                    st.session_state['tts_queue'].append(tts_text)
                         
                            play_tts_queue()

                            if spl_peak >= alarm_db and st.session_state['sos_email_enabled']:
                                if not st.session_state['danger_alert_time']:
                                    st.session_state['danger_alert_time'] = time.time()
                                
                                if st.button("✅ 안전 확인", key="safety_check_upload", use_container_width=True):
                                    st.session_state['danger_alert_time'] = None
                                    st.session_state['email_sent'] = False
                                    st.success("✅ 안전 확인됨")
                                else:
                                    st.warning("1분 동안 안전 확인 버튼을 누르지 않으면 SOS 메일이 발송됩니다.")
                                    display_timer(st.session_state['danger_alert_time'], user_id, result, address, latitude, longitude)

        with tab2:
            st.subheader("소음 측정 기록")
            st.write("여기에서 사용자의 최근 소음 분류 기록을 확인하고 피드백을 남길 수 있습니다.")

            st.markdown("#### 🔍 필터링 옵션")
            col1, col2, col3 = st.columns(3)
            with col1:
                start_date = st.date_input("시작 날짜", value=None, key="start_date")
            with col2:
                end_date = st.date_input("종료 날짜", value=None, key="end_date")
            with col3:
                noise_types = ["모두", "차량경적", "이륜차경적", "차량사이렌", "차량주행음", "이륜차주행음", "기타소음"]
                selected_noise_type = st.selectbox("소음 유형", noise_types, index=0, key="noise_type_filter")

            per_page = 10
            if 'current_page' not in st.session_state:
                st.session_state['current_page'] = 1

            results, total = get_classification_results(
                user_id=user_id,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
                noise_type=selected_noise_type,
                page=st.session_state['current_page'],
                per_page=per_page
            )

            if not results:
                st.write("필터링 조건에 맞는 측정 기록이 없습니다.")
            else:
                st.write(f"총 기록 수: {total}")
                for i, result in enumerate(results):
                    with st.expander(f"기록 #{(st.session_state['current_page'] - 1) * per_page + i + 1} - {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}", expanded=False):
                        st.write(f"**소음 유형**: {result['noise_type']}")
                        st.write(f"**최대 소음 강도**: {result['spl_peak']} dB")
                        st.write(f"**평균 소음 강도**: {result['spl_rms']} dB")
                        st.write(f"**추정 거리**: {result['estimated_distance'] if result['estimated_distance'] is not None else 'N/A'} 미터")
                        st.write(f"**방향**: {result['direction']}")
                        st.write(f"**분석 시간**: {result['elapsed_time']:.2f} 초")
                        # if result['latitude'] and result['longitude']:
                        #     address = f"위도: {result['latitude']}, 경도: {result['longitude']}"
                        #     st.write(f"**위치**: {address}")
                        #     df = pd.DataFrame({"lat": [result['latitude']], "lon": [result['longitude']]})
                        #     st.map(df)

                        # if result['audio_path'] and os.path.exists(result['audio_path']):
                        #     st.audio(result['audio_path'], format='audio/wav')
                        # else:
                        #     st.warning("⚠️ 오디오 파일을 찾을 수 없습니다.")

                        feedback_key = f"feedback_{i}_{result['timestamp']}"
                        feedback = st.selectbox(
                            "이 분류가 정확했나요?",
                            ["네", "아니요", "모르겠어요"],
                            key=feedback_key,
                            help="소음 유형이 실제와 맞는지 알려주세요!"
                        )
                        wrong_noise = None
                        if feedback == "아니요":
                            wrong_noise = st.text_input(
                                "어떤 소음이었나요?",
                                key=f"feedback_text_{i}_{result['timestamp']}",
                                help="정확하지 않다면 실제 소음 유형을 입력해주세요."
                            )
                        if st.button("피드백 제출", key=f"submit_{i}_{result['timestamp']}"):
                            save_feedback(
                                result_id=result['result_id'],
                                user_id=user_id,
                                noise_type=result['noise_type'],
                                spl_peak=result['spl_peak'],
                                feedback=feedback,
                                wrong_noise=wrong_noise,
                                audio_path=result['audio_path'],
                                timestamp=result['timestamp']
                            )

                total_pages = (total + per_page - 1) // per_page
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("이전 페이지", disabled=(st.session_state['current_page'] == 1)):
                            st.session_state['current_page'] -= 1
                    with col2:
                        st.write(f"페이지 {st.session_state['current_page']} / {total_pages}")
                    with col3:
                        if st.button("다음 페이지", disabled=(st.session_state['current_page'] == total_pages)):
                            st.session_state['current_page'] += 1

        with tab3:
            st.subheader("알람 기준 설정")
            
            DEFAULT_ALARM_DB = {
                "차량경적": 100,
                "이륜차경적": 100,
                "차량사이렌": 110,
                "차량주행음": 90,
                "이륜차주행음": 90,
                "기타소음": 85
            }
            SENSITIVITY_MULTIPLIER = {
                "약(🔵)": {"db": -10},
                "중(🟡)": {"db": 0},
                "강(🔴)": {"db": 10}
            }

            #selected_sensitivity = st.radio("📢 감도 선택", ["약(🔵)", help="작은 소리에도 알람을 제공해요", "중(🟡)", help="일반적인 안전 기준이에요", "강(🔴)", help="큰 소리에만 알람을 제공해요"], index=1)        
            selected_sensitivity = st.radio("📢 감도 선택", ["약(🔵)", "중(🟡)", "강(🔴)"], index=1)
            st.caption("🔵 작은 소리에도 알람을 제공해요, 🟡 일반적인 안전 기준이에요, 🔴 큰 소리에만 알람을 제공해요")

            # 알람 데시벨 조정
            adjusted_alarm_settings = {
                noise_type: {
                    "데시벨": DEFAULT_ALARM_DB[noise_type] + SENSITIVITY_MULTIPLIER[selected_sensitivity]["db"]
                }
                for noise_type in DEFAULT_ALARM_DB
            }

            st.subheader("📌 소음 유형별 알람 기준 조정")
            st.write("감도를 선택하면 데시벨 값이 자동 설정됩니다. 필요하면 개별적으로 조정하세요.")
            user_alarm_settings = {}
            for noise_type, values in adjusted_alarm_settings.items():
                user_db = st.slider(f"🔊 {noise_type} (dB)", 50, 120, values["데시벨"], key=f"{noise_type}_db")
                user_alarm_settings[noise_type] = {"데시벨": user_db}

            if st.button("📌 설정 저장"):
                for noise_type, settings in user_alarm_settings.items():
                    save_alarm_settings(
                        user_id=user_id,
                        noise_type=noise_type,
                        alarm_db=settings["데시벨"],
                        sensitivity_level=selected_sensitivity
                    )
                st.success("✅ 알람 설정이 저장되었습니다.")
                st.write(f"📢 **선택한 감도:** {selected_sensitivity}")
                st.subheader("📌 최종 설정값")
                st.table(pd.DataFrame(user_alarm_settings).T)

if __name__ == '__main__':
    m = NoiseModel_page()
    m.noisemodel_page()