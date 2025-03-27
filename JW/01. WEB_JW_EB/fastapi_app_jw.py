import os
import librosa
import numpy as np
import tensorflow as tf
import io
import logging
from fastapi import FastAPI, File, UploadFile, WebSocket
from tensorflow.keras.models import load_model

app = FastAPI()

# GPU 비활성화
tf.config.set_visible_devices([], 'GPU')

# 모델 로드
model = load_model('resnet_model_modified_v6.h5')
print("모델 로드 완료: resnet_model_modified_v6.h5")

# 고정값 설정
ENERGY_THRESHOLD = -1.8595
MEAN_ENERGY_IND = -15.5199
STD_ENERGY_IND = 8.8151
CONFIDENCE_THRESHOLD = 0.9
TEMPERATURE = 1.0

# 라벨 정의
final_labels = ['이륜차경적', '이륜차주행음', '차량경적', '차량사이렌', '차량주행음', '기타소음']
label_to_code = {label: i for i, label in enumerate(final_labels)}
index_to_label = {v: k for k, v in label_to_code.items()}
unknown_label_index = label_to_code['기타소음']

# 소음 유형별 데시벨 기준
SPL_REFERENCE = 20e-6
DB_REFERENCE = {
    "차량 경적": 100, "이륜차 경적": 100, "사이렌": 100,
    "차량 주행음": 90, "이륜차 주행음": 90, "기타 소음": 85,
}

# Energy Score 계산
def compute_energy(logits, T=TEMPERATURE):
    exp_vals = np.exp(logits / T)
    sum_exp = np.sum(exp_vals, axis=1) + 1e-9
    return -T * np.log(sum_exp)

# 오디오 분석 함수
def analyze_audio(file_bytes, predicted_label):
    try:
        y, sr = librosa.load(io.BytesIO(file_bytes), sr=None, mono=False)
        if y is None or len(y) == 0:
            logging.error("❌ librosa가 오디오 데이터를 로드하지 못함!")
            return {"error": "librosa가 오디오 데이터를 로드하지 못함"}

        is_stereo = len(y.shape) == 2 and y.shape[0] == 2
        if is_stereo:
            left_channel = y[0]
            right_channel = y[1]
            rms_total = np.sqrt(np.mean((left_channel + right_channel) ** 2)) / 2
        else:
            rms_total = np.sqrt(np.mean(y ** 2))

        if rms_total == 0:
            logging.error("❌ RMS 계산 중 값이 0이 됨!")
            return {"error": "RMS 계산 오류"}

        rms_spl = 20 * np.log10(rms_total / SPL_REFERENCE + 1e-6)
        peak_amplitude = np.max(np.abs(y))
        peak_spl = 20 * np.log10(peak_amplitude / SPL_REFERENCE + 1e-6)

        spl_used = peak_spl if predicted_label in ["차량 경적", "이륜차 경적", "사이렌"] else rms_spl
        db_ref = DB_REFERENCE.get(predicted_label, 85)
        estimated_distance = round(1 * (10 ** ((db_ref - spl_used) / 20)), 2)
        estimated_distance = max(0.1, min(estimated_distance, 1000))

        direction = "알 수 없음"
        if is_stereo:
            rms_left = np.sqrt(np.mean(left_channel ** 2))
            rms_right = np.sqrt(np.mean(right_channel ** 2))
            spl_left = 20 * np.log10(rms_left / SPL_REFERENCE + 1e-6)
            spl_right = 20 * np.log10(rms_right / SPL_REFERENCE + 1e-6)
            db_difference = spl_left - spl_right
            if abs(db_difference) < 1.5:
                direction = "중앙"
            elif 1.5 <= abs(db_difference) < 3:
                direction = "약간 왼쪽" if db_difference > 0 else "약간 오른쪽"
            else:
                direction = "왼쪽" if db_difference > 0 else "오른쪽"

        return {
            "prediction": predicted_label,
            "spl": float(round(spl_used, 2)),
            "estimated_distance": float(estimated_distance),
            "direction": direction,
        }
    except Exception as e:
        logging.error(f"❌ 예외 발생: {str(e)}")
        return {"error": str(e)}

# 모델 예측 (고정값 적용)
@app.post("/predict/")
async def predict(file: UploadFile = File(...)):
    file_bytes = await file.read()
    print(f"파일 이름: {file.filename}")

    audio_bytes = io.BytesIO(file_bytes)
    audio_librosa, sr_librosa = librosa.load(audio_bytes, sr=None)
    print("librosa로 처리한 샘플링 레이트:", sr_librosa)

    mfccs = librosa.feature.mfcc(y=audio_librosa, sr=sr_librosa, n_mfcc=50)
    features = np.mean(mfccs, axis=1).astype(float)
    print(features)

    X = features.reshape(1, 50, 1)
    logits = model.predict(X, verbose=0)
    energy_score = compute_energy(logits)[0]
    softmax_probs = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
    max_prob = np.max(softmax_probs, axis=1)[0]
    basic_pred = np.argmax(softmax_probs, axis=1)[0]
    z_score = (energy_score - MEAN_ENERGY_IND) / STD_ENERGY_IND

    if max_prob < CONFIDENCE_THRESHOLD and energy_score > ENERGY_THRESHOLD and z_score > 1.5:
        predicted_label = unknown_label_index
    else:
        predicted_label = basic_pred

    detected_noise = index_to_label[predicted_label]
    print(f"예측된 소음 유형: {detected_noise}")

    result = analyze_audio(file_bytes, detected_noise)
    result["confidence"] = float(round(max_prob, 4))
    print(result)
    return result

@app.websocket("/ws/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            audio_data = await websocket.receive_bytes()
            print("Received audio data")
            await websocket.send_text("Audio data received")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()