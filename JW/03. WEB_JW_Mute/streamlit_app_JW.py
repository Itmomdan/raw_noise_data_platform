import streamlit as st
import requests
import numpy as np
import pandas as pd
import os
import time
import tensorflow as tf
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.layers import Dense
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import seaborn as sns
import matplotlib.pyplot as plt
import logging
from gtts import gTTS
import base64
import smtplib
from email.mime.text import MIMEText

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FastAPI 서버 주소
FASTAPI_URL = "http://localhost:8006/predict/"

# 저장 디렉토리
upload_folder = "uploads"
audio_save_path = "recorded_audio"
os.makedirs(upload_folder, exist_ok=True)
os.makedirs(audio_save_path, exist_ok=True)

# CSV용 전역 변수
MODEL = None
LOGITS_MODEL = None
ENERGY_THRESHOLD = None  # 동적 계산
CONFIDENCE_THRESHOLD = 0.99
TEMPERATURE = 1.0
MEAN_ENERGY_IND = -15.3398  # 초기값
STD_ENERGY_IND = 8.2265     # 초기값

# 라벨 정의
label_dict = {'이륜차경적': 0, '이륜차주행음': 1, '차량경적': 2, '차량사이렌': 3, '차량주행음': 4, '기타소음': 5}
reverse_label_dict = {v: k for k, v in label_dict.items()}
english_labels = ['Motorcycle Horn', 'Motorcycle Running Sound', 'Vehicle Horn', 'Vehicle Siren', 'Vehicle Driving', 'Other Noise']
unknown_label_index = label_dict['기타소음']

# Eager Execution 활성화
tf.config.run_functions_eagerly(True)

# # 모델 초기화 (CSV용)
# def initialize_models(model_path='resnet_model_modified_v6.h5'):
#     global MODEL, LOGITS_MODEL
#     if MODEL is None:
#         MODEL = load_model(model_path)
#         last_layer = MODEL.layers[-1]
#         if last_layer.get_config().get("activation") == "softmax":
#             logits = Model(inputs=MODEL.input, outputs=MODEL.layers[-2].output)
#             new_dense = Dense(last_layer.units, activation=None, name='logits')(logits.output)
#             LOGITS_MODEL = Model(inputs=MODEL.input, outputs=new_dense)
#             LOGITS_MODEL.layers[-1].set_weights(last_layer.get_weights())
#         else:
#             LOGITS_MODEL = MODEL
#         logging.info("모델 로드 완료 for Streamlit")

# def compute_energy(logits, T=TEMPERATURE):
#     exp_vals = np.exp(logits / T)
#     sum_exp = np.sum(exp_vals, axis=1) + 1e-9
#     return -T * np.log(sum_exp)

# def validate_mfcc_data(df):
#     mfcc_columns = [f'mfcc_{i}' for i in range(1, 51)]
#     if not all(col in df.columns for col in mfcc_columns):
#         raise ValueError("MFCC 열이 누락됨")
#     mfcc_data = df[mfcc_columns].values
#     if mfcc_data.shape[0] == 0:
#         raise ValueError("데이터가 비어 있음")
#     if np.any(np.isnan(mfcc_data)) or np.any(np.isinf(mfcc_data)):
#         raise ValueError("MFCC 데이터에 NaN 또는 Inf 값 포함")
#     return mfcc_data.reshape(-1, 50, 1)

# def update_energy_stats(energy_scores, preds, window_size=1000, max_std_dev=20.0):
#     global MEAN_ENERGY_IND, STD_ENERGY_IND
#     if not hasattr(update_energy_stats, 'buffer'):
#         update_energy_stats.buffer = []

#     ind_scores = energy_scores[preds != unknown_label_index]
#     if len(ind_scores) > 0:
#         update_energy_stats.buffer.extend(ind_scores)
#         if len(update_energy_stats.buffer) > window_size:
#             update_energy_stats.buffer = update_energy_stats.buffer[-window_size:]
        
#         if len(update_energy_stats.buffer) >= 2:
#             new_mean = np.mean(update_energy_stats.buffer)
#             new_std = np.std(update_energy_stats.buffer)
#             if new_std <= max_std_dev and not np.isnan(new_std):
#                 MEAN_ENERGY_IND = new_mean
#                 STD_ENERGY_IND = max(new_std, 1e-6)
#                 logging.info(f"Updated MEAN_ENERGY_IND: {MEAN_ENERGY_IND:.4f}, STD_ENERGY_IND: {STD_ENERGY_IND:.4f}")

# def predict_samples(df):
#     initialize_models()
#     X = validate_mfcc_data(df)
#     y_true = df['ood_label'].map(label_dict).fillna(5).astype(int).values

#     global ENERGY_THRESHOLD
#     if ENERGY_THRESHOLD is None:
#         logits_temp = LOGITS_MODEL.predict(X, verbose=0)
#         energy_scores_temp = compute_energy(logits_temp)
#         softmax_probs_temp = np.exp(logits_temp) / np.sum(np.exp(logits_temp), axis=1, keepdims=True)
#         threshold_candidates = np.linspace(energy_scores_temp.min(), energy_scores_temp.max(), 100)
#         best_f1 = -1
#         for thr in threshold_candidates:
#             temp_preds = np.where((np.max(softmax_probs_temp, axis=1) < CONFIDENCE_THRESHOLD) & 
#                                   (energy_scores_temp > thr), unknown_label_index, np.argmax(softmax_probs_temp, axis=1))
#             f1 = f1_score(y_true, temp_preds, labels=[unknown_label_index], average='weighted', zero_division=0)
#             if f1 > best_f1:
#                 best_f1 = f1
#                 ENERGY_THRESHOLD = thr
#         logging.info(f"최적 Energy Threshold: {ENERGY_THRESHOLD:.4f}, F1-score: {best_f1:.4f}")
#     else:
#         logging.info(f"기존 ENERGY_THRESHOLD 사용: {ENERGY_THRESHOLD}")

#     logits = LOGITS_MODEL.predict(X, verbose=0)
#     energy_scores = compute_energy(logits)
#     softmax_probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
#     max_probs = np.max(softmax_probs, axis=1)
#     basic_preds = np.argmax(softmax_probs, axis=1)
#     z_scores = (energy_scores - MEAN_ENERGY_IND) / STD_ENERGY_IND

#     final_preds = np.where((max_probs < CONFIDENCE_THRESHOLD) & 
#                            (energy_scores > ENERGY_THRESHOLD),
#                            unknown_label_index, basic_preds)

#     update_energy_stats(energy_scores, final_preds)
#     logging.info(f"Energy 범위: min={np.min(energy_scores):.4f}, max={np.max(energy_scores):.4f}, mean={np.mean(energy_scores):.4f}")
    
#     return final_preds

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

# 이메일 알림
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
    
    if not st.session_state['stop_audio']:
        alert_sound = generate_tts(message)
        autoplay_audio(alert_sound)
        os.remove(alert_sound)
        time.sleep(3)


# 예측 결과 처리 함수
def process_prediction(response):
    if response.status_code == 200:
        result = response.json()
        if "error" in result:
            show_alert("오디오 분석에 실패했습니다", "danger")
            return
        
        # 종료 시간 기록 및 시간 계산
        end_time = time.time()
        elapsed_time = end_time - st.session_state['start_time']

        st.write(f"🔊 **예측된 소음 유형:** {result.get('prediction', '알 수 없음')}")
        st.write(f"📊 **Peak SPL (dB):** {result.get('spl_peak', 'N/A')}")
        st.write(f"📊 **RMS SPL (dB):** {result.get('spl_rms', 'N/A')}")
        st.write(f"📏 **추정 거리:** {result.get('estimated_distance', 'N/A')} 미터")
        st.write(f"📡 **방향:** {result.get('direction', '알 수 없음')}")

        # 경과 시간 출력
        st.write(f"⏱️ **예측 소요 시간:** {elapsed_time:.2f} 초")

        noise_type = result.get('prediction', '알 수 없음')
        spl = result.get('spl_peak', 0)
        distance = result.get('estimated_distance', 'N/A')
        direction = result.get('direction', '알 수 없음')

        if spl >= 70:
            show_alert("위험 수준 소음 감지! 즉시 조치가 필요합니다", "danger")
            alert_message = f"🚨위험 수준 소음 감지!🚨 소음 유형: {noise_type}, 강도: {spl}dB, 위치: {distance}m, 방향: {direction}"
            # send_email("itmomdan0328@gmail.com", "소음 경고", alert_message) # 이메일 기능 필요 시 주석 해제
        elif spl >= 50:
            show_alert("주의 요함: 지속적 노출 위험", "warning")
            alert_message = f"⚠️주의 요함!⚠️ 소음 유형: {noise_type}, 강도: {spl}dB, 위치: {distance}m, 방향: {direction}"
            # send_email("itmomdan0328@gmail.com", "소음 경고", alert_message) # 이메일 기능 필요 시 주석 해제
        
        if not st.session_state['stop_audio']:
            info_text = f"소음 유형은 {noise_type}입니다. 현재 소음 강도는 {spl} 데시벨로 측정되었으며, 약 {distance} 미터 거리에서 발생하고 있습니다."
            info_sound = generate_tts(info_text)
            autoplay_audio(info_sound)
            os.remove(info_sound)
    else:
        show_alert("서버 연결 오류 발생", "danger")


def main():
    st.title("소음 분류기")
    

    # 실시간 녹음 섹션
    with st.expander("🎙 녹음 방식", expanded=True):
        st.subheader("1. 배경 소음 녹음")
        background_audio = st.audio_input("배경 소음을 녹음하세요 (5초 권장)")
        background_path = os.path.join(audio_save_path, "background_audio.wav")
    
        if background_audio:
            st.session_state['background_audio'] = background_audio  # 세션 상태에 저장
            with open(background_path, "wb") as f:
                f.write(background_audio.getvalue())
            st.success(f"📂 배경 소음이 저장되었습니다: {background_path}")
        else:
            st.session_state['background_audio'] = None  # 초기화

        st.subheader("2. 실제 소음 녹음")
        audio_data = st.audio_input("목표 소음을 녹음하세요")

        if audio_data:
            file_path = os.path.join(audio_save_path, "recorded_audio.wav")
            with open(file_path, "wb") as f:
                f.write(audio_data.getvalue())
            st.success(f"📂 녹음된 오디오가 저장되었습니다: {file_path}")

            if st.button("녹음 데이터 분석"):
                st.session_state['start_time'] = time.time()  # 시작 시간 기록 (세션 상태에 저장)
                with st.spinner("분석 진행 중..."):
                    files = {"file": ("recorded_audio.wav", audio_data.getvalue(), "audio/wav")}
                    # 배경 소음 파일 전송 부분
                    if st.session_state['background_audio']:
                        files["background"] = (
                            "background_audio.wav",
                            st.session_state['background_audio'].getvalue(),
                            "audio/wav",
                        )
                    response = requests.post(FASTAPI_URL, files=files)
                    process_prediction(response)  # process_prediction에서 시간 측정


    # 파일 업로드 섹션
    with st.expander("📁 파일 업로드 방식", expanded=True):
    # 기존 배경 소음 초기화
        st.session_state['background_audio'] = None

        uploaded_file = st.file_uploader("음성 파일을 업로드하세요", type=["wav"])
    
        if uploaded_file is not None:
            st.audio(uploaded_file, format='audio/wav')
            st.write(f"파일 이름: {uploaded_file.name}")

            upload_path = os.path.join(upload_folder, uploaded_file.name)
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            st.success(f"📂 업로드된 파일이 저장되었습니다: {upload_path}")
            
            if st.button("음성 예측하기"):
                st.session_state['start_time'] = time.time()  # 시작 시간 기록 (세션 상태에 저장)
                with st.spinner("분석 중..."):
                    response = requests.post(FASTAPI_URL, files={"file": uploaded_file})
                    process_prediction(response)  # process_prediction에서 시간 측정
                
    
    # Stop Audio 버튼
    st.session_state['stop_audio'] = st.button("🛑 Stop Audio")

    # # CSV 파일 업로드 및 평가
    # st.title("소음 분류 성능 평가")
    # uploaded_csv = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])
    # if uploaded_csv is not None:
    #     try:
    #         df = pd.read_csv(uploaded_csv)
    #         st.write("📌 **업로드된 데이터 미리보기**:")
    #         st.dataframe(df.head())

    #         if st.button("예측 실행"):
    #             predicted_labels = predict_samples(df)
    #             df['predicted_label'] = [reverse_label_dict[label] for label in predicted_labels]

    #             st.write("🎯 **예측 결과**:")
    #             st.write(df.head())

    #             y_true = df['ood_label'].map(label_dict).fillna(5).astype(int).values
    #             y_pred = predicted_labels

    #             report = classification_report(y_true, y_pred, target_names=english_labels, output_dict=True)
    #             cm = confusion_matrix(y_true, y_pred, labels=list(label_dict.values()))
    #             overall_accuracy = accuracy_score(y_true, y_pred)

    #             st.subheader("클래스별 예측 결과")
    #             metrics_df = pd.DataFrame({
    #                 'Class': english_labels,
    #                 'Precision': [report[label]['precision'] for label in english_labels],
    #                 'Recall': [report[label]['recall'] for label in english_labels],
    #                 'F1-Score': [report[label]['f1-score'] for label in english_labels],
    #                 'Support': [report[label]['support'] for label in english_labels]
    #             })
    #             st.table(metrics_df.round(4))
    #             st.write(f"Overall Accuracy: {overall_accuracy:.4f}")

    #             st.subheader("Confusion Matrix")
    #             plt.figure(figsize=(8, 6))
    #             sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
    #                         xticklabels=english_labels, yticklabels=english_labels)
    #             plt.xlabel("Predicted")
    #             plt.ylabel("Actual")
    #             plt.title("Confusion Matrix")
    #             st.pyplot(plt)

    #             st.write(f"최종 값: ENERGY_THRESHOLD={ENERGY_THRESHOLD:.4f}, MEAN_ENERGY_IND={MEAN_ENERGY_IND:.4f}, STD_ENERGY_IND={STD_ENERGY_IND:.4f}")

    #             csv = df.to_csv(index=False).encode('utf-8')
    #             st.download_button("📥 예측 결과 다운로드", csv, "predictions.csv", "text/csv")
    #     except Exception as e:
    #         st.error(f"🚨 CSV 읽기 오류: {str(e)}")

if __name__ == "__main__":
    main()