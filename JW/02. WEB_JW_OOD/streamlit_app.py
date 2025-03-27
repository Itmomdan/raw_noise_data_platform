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

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FastAPI 서버 주소
FASTAPI_URL = "http://localhost:8006/predict/"

# 저장 디렉토리
upload_folder = "uploads"
audio_save_path = "recorded_audio"
os.makedirs(upload_folder, exist_ok=True)
os.makedirs(audio_save_path, exist_ok=True)

# CSV용 전역 변수 (주피터 코드 반영)
MODEL = None
LOGITS_MODEL = None
ENERGY_THRESHOLD = None  # 동적 계산
CONFIDENCE_THRESHOLD = 0.99  # 주피터 값
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

# 모델 초기화 (CSV용)
def initialize_models(model_path='resnet_model_modified_v6.h5'):
    global MODEL, LOGITS_MODEL
    if MODEL is None:
        MODEL = load_model(model_path)
        last_layer = MODEL.layers[-1]
        if last_layer.get_config().get("activation") == "softmax":
            logits = Model(inputs=MODEL.input, outputs=MODEL.layers[-2].output)
            new_dense = Dense(last_layer.units, activation=None, name='logits')(logits.output)
            LOGITS_MODEL = Model(inputs=MODEL.input, outputs=new_dense)
            LOGITS_MODEL.layers[-1].set_weights(last_layer.get_weights())
        else:
            LOGITS_MODEL = MODEL
        logging.info("모델 로드 완료 for Streamlit")

def compute_energy(logits, T=TEMPERATURE):
    exp_vals = np.exp(logits / T)
    sum_exp = np.sum(exp_vals, axis=1) + 1e-9
    return -T * np.log(sum_exp)

def validate_mfcc_data(df):
    mfcc_columns = [f'mfcc_{i}' for i in range(1, 51)]
    if not all(col in df.columns for col in mfcc_columns):
        raise ValueError("MFCC 열이 누락됨")
    mfcc_data = df[mfcc_columns].values
    if mfcc_data.shape[0] == 0:
        raise ValueError("데이터가 비어 있음")
    if np.any(np.isnan(mfcc_data)) or np.any(np.isinf(mfcc_data)):
        raise ValueError("MFCC 데이터에 NaN 또는 Inf 값 포함")
    return mfcc_data.reshape(-1, 50, 1)

def update_energy_stats(energy_scores, preds, window_size=1000, max_std_dev=20.0):
    global MEAN_ENERGY_IND, STD_ENERGY_IND
    if not hasattr(update_energy_stats, 'buffer'):
        update_energy_stats.buffer = []

    ind_scores = energy_scores[preds != unknown_label_index]
    if len(ind_scores) > 0:
        update_energy_stats.buffer.extend(ind_scores)
        if len(update_energy_stats.buffer) > window_size:
            update_energy_stats.buffer = update_energy_stats.buffer[-window_size:]
        
        if len(update_energy_stats.buffer) >= 2:
            new_mean = np.mean(update_energy_stats.buffer)
            new_std = np.std(update_energy_stats.buffer)
            if new_std <= max_std_dev and not np.isnan(new_std):
                MEAN_ENERGY_IND = new_mean
                STD_ENERGY_IND = max(new_std, 1e-6)
                logging.info(f"Updated MEAN_ENERGY_IND: {MEAN_ENERGY_IND:.4f}, STD_ENERGY_IND: {STD_ENERGY_IND:.4f}")

def predict_samples(df):
    initialize_models()
    X = validate_mfcc_data(df)
    y_true = df['ood_label'].map(label_dict).fillna(5).astype(int).values

    global ENERGY_THRESHOLD
    if ENERGY_THRESHOLD is None:
        logits_temp = LOGITS_MODEL.predict(X, verbose=0)
        energy_scores_temp = compute_energy(logits_temp)
        softmax_probs_temp = np.exp(logits_temp) / np.sum(np.exp(logits_temp), axis=1, keepdims=True)
        threshold_candidates = np.linspace(energy_scores_temp.min(), energy_scores_temp.max(), 100)
        best_f1 = -1
        for thr in threshold_candidates:
            temp_preds = np.where((np.max(softmax_probs_temp, axis=1) < CONFIDENCE_THRESHOLD) & 
                                  (energy_scores_temp > thr), unknown_label_index, np.argmax(softmax_probs_temp, axis=1))
            f1 = f1_score(y_true, temp_preds, labels=[unknown_label_index], average='weighted', zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                ENERGY_THRESHOLD = thr
        logging.info(f"최적 Energy Threshold: {ENERGY_THRESHOLD:.4f}, F1-score: {best_f1:.4f}")
    else:
        logging.info(f"기존 ENERGY_THRESHOLD 사용: {ENERGY_THRESHOLD}")

    logits = LOGITS_MODEL.predict(X, verbose=0)
    energy_scores = compute_energy(logits)
    softmax_probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
    max_probs = np.max(softmax_probs, axis=1)
    basic_preds = np.argmax(softmax_probs, axis=1)
    z_scores = (energy_scores - MEAN_ENERGY_IND) / STD_ENERGY_IND

    final_preds = np.where((max_probs < CONFIDENCE_THRESHOLD) & 
                           (energy_scores > ENERGY_THRESHOLD),
                           unknown_label_index, basic_preds)

    update_energy_stats(energy_scores, final_preds)
    logging.info(f"Energy 범위: min={np.min(energy_scores):.4f}, max={np.max(energy_scores):.4f}, mean={np.mean(energy_scores):.4f}")
    
    return final_preds

def main():
    st.title("소음 분류기")

    # 실시간 녹음
    audio_value = st.audio_input("음성을 녹음하세요!")
    if audio_value:
        st.audio(audio_value, format='audio/wav')
        file_path = os.path.join(audio_save_path, "recorded_audio.wav")
        with open(file_path, "wb") as f:
            f.write(audio_value.getvalue())
        st.success(f"녹음된 오디오가 저장되었습니다: {file_path}")

        if st.button("녹음 예측하기"):
            start_time = time.time()
            files = {"file": ("recorded_audio.wav", audio_value.getvalue(), "audio/wav")}
            response = requests.post(FASTAPI_URL, files=files)
            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                prediction = response.json()
                if "error" in prediction:
                    st.error("오디오 분석 중 오류 발생! 🚨")
                else:
                    st.success("분석 완료 ✅")
                    st.write(f"**예측된 소음 유형:** {prediction.get('prediction', '알 수 없음')}")
                    st.write(f"**소음 크기 (dB):** {prediction.get('spl', 'N/A')} dB")
                    st.write(f"**추정 거리:** {prediction.get('estimated_distance', 'N/A')} 미터")
                    st.write(f"**방향:** {prediction.get('direction', '알 수 없음')}")
                    st.write(f"**신뢰도:** {prediction.get('confidence', 'N/A')}")
                    st.write(f"⏱️ 예측 소요 시간: {elapsed_time:.2f}초")
            else:
                st.error("서버와의 통신 오류 발생! ❌")

    # WAV 파일 업로드
    uploaded_file = st.file_uploader("음성 파일을 업로드하세요", type=["wav"])
    if uploaded_file is not None:
        st.audio(uploaded_file, format='audio/wav')
        st.write(f"파일 이름: {uploaded_file.name}")

        upload_path = os.path.join(upload_folder, uploaded_file.name)
        with open(upload_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        st.success(f"📂 업로드된 파일이 저장되었습니다: {upload_path}")

        if st.button('업로드 예측하기'):
            start_time = time.time()
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "audio/wav")}
            response = requests.post(FASTAPI_URL, files=files)
            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                prediction = response.json()
                if "error" in prediction:
                    st.error("오디오 분석 중 오류 발생! 🚨")
                else:
                    st.success("분석 완료 ✅")
                    st.write(f"**예측된 소음 유형:** {prediction.get('prediction', '알 수 없음')}")
                    st.write(f"**소음 크기 (dB):** {prediction.get('spl', 'N/A')} dB")
                    st.write(f"**추정 거리:** {prediction.get('estimated_distance', 'N/A')} 미터")
                    st.write(f"**방향:** {prediction.get('direction', '알 수 없음')}")
                    st.write(f"**신뢰도:** {prediction.get('confidence', 'N/A')}")
                    st.write(f"⏱️ 예측 소요 시간: {elapsed_time:.2f}초")
            else:
                st.error("서버와의 통신 오류 발생! ❌")

    # CSV 업로드 및 평가
    st.title("소음 분류 성능 평가")
    uploaded_csv = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv)
            st.write("📌 **업로드된 데이터 미리보기**:")
            st.dataframe(df.head())

            if st.button("예측 실행"):
                predicted_labels = predict_samples(df)
                df['predicted_label'] = [reverse_label_dict[label] for label in predicted_labels]

                st.write("🎯 **예측 결과**:")
                st.write(df.head())

                y_true = df['ood_label'].map(label_dict).fillna(5).astype(int).values
                y_pred = predicted_labels

                report = classification_report(y_true, y_pred, target_names=english_labels, output_dict=True)
                cm = confusion_matrix(y_true, y_pred, labels=list(label_dict.values()))
                overall_accuracy = accuracy_score(y_true, y_pred)

                st.subheader("클래스별 예측 결과")
                metrics_df = pd.DataFrame({
                    'Class': english_labels,
                    'Precision': [report[label]['precision'] for label in english_labels],
                    'Recall': [report[label]['recall'] for label in english_labels],
                    'F1-Score': [report[label]['f1-score'] for label in english_labels],
                    'Support': [report[label]['support'] for label in english_labels]
                })
                st.table(metrics_df.round(4))
                st.write(f"Overall Accuracy: {overall_accuracy:.4f}")

                st.subheader("Confusion Matrix")
                plt.figure(figsize=(8, 6))
                sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                            xticklabels=english_labels, yticklabels=english_labels)
                plt.xlabel("Predicted")
                plt.ylabel("Actual")
                plt.title("Confusion Matrix")
                st.pyplot(plt)

                st.write(f"최종 값: ENERGY_THRESHOLD={ENERGY_THRESHOLD:.4f}, MEAN_ENERGY_IND={MEAN_ENERGY_IND:.4f}, STD_ENERGY_IND={STD_ENERGY_IND:.4f}")

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 예측 결과 다운로드", csv, "predictions.csv", "text/csv")
        except Exception as e:
            st.error(f"🚨 CSV 읽기 오류: {str(e)}")

if __name__ == "__main__":
    main()