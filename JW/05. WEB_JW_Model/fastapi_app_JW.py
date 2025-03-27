import os
import librosa
import numpy as np
import tensorflow as tf
import io
from fastapi import FastAPI, File, UploadFile, WebSocket
from tensorflow.keras.models import load_model
from scipy.signal import stft, istft

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

# 고주파 소음 목록 (Peak SPL 사용)
HIGH_FREQ_SOUNDS = ["사이렌", "차량 경적", "이륜차 경적"]

# 거리 계산 함수 (소음 유형별 Peak SPL vs RMS SPL 적용)
def estimate_distance(spl_peak, spl_rms, predicted_label):
    """ 소음 유형별 거리 계산 (Peak vs RMS 적용) """
    db_ref = DB_REFERENCE.get(predicted_label, 85)

    # Peak SPL을 사용할지, RMS SPL을 사용할지 결정
    if predicted_label in HIGH_FREQ_SOUNDS:
        spl_used = spl_peak
    else:
        spl_used = spl_rms

    estimated_distance = 1 * (10 ** ((db_ref - spl_used) / 20))
    return "50미터 이상" if estimated_distance > 50 else round(estimated_distance, 1)

# 방향 판별 함수
def estimate_direction(y, predicted_label):
    """ 소음 유형에 따라 고주파/저주파 차이를 반영한 방향 판별 """
    if len(y.shape) == 1:
        return "알 수 없음"

    left_channel, right_channel = y[0], y[1]
    rms_left = np.sqrt(np.mean(left_channel ** 2))
    rms_right = np.sqrt(np.mean(right_channel ** 2))

    spl_left = 20 * np.log10(rms_left / SPL_REFERENCE + 1e-6)
    spl_right = 20 * np.log10(rms_right / SPL_REFERENCE + 1e-6)

    db_diff = spl_left - spl_right
    threshold = 2 if predicted_label in HIGH_FREQ_SOUNDS else 1  

    if abs(db_diff) < threshold:
        return "중앙"
    elif db_diff > threshold:
        return "왼쪽"
    return "오른쪽"

# 오디오 분석 (데시벨, 거리, 방향 포함)
def analyze_audio(file_bytes, predicted_label):
    """ 오디오 분석 (데시벨, 거리, 방향 포함) """
    y, sr = librosa.load(io.BytesIO(file_bytes), sr=None, mono=False)
    if y is None or len(y) == 0:
        return {"error": "오디오 데이터를 로드하지 못함"}

    is_stereo = len(y.shape) == 2 and y.shape[0] == 2

    # RMS & Peak SPL 계산
    rms_total = np.sqrt(np.mean(y ** 2))
    rms_spl = 20 * np.log10(rms_total / SPL_REFERENCE + 1e-6)
    peak_amplitude = np.max(np.abs(y))
    peak_spl = 20 * np.log10(peak_amplitude / SPL_REFERENCE + 1e-6)

    # 거리 예측 (소음 유형별 SPL 선택)
    estimated_distance = estimate_distance(peak_spl, rms_spl, predicted_label)

    # 방향 판별
    direction = estimate_direction(y, predicted_label) if is_stereo else "알 수 없음"

    return {
        "prediction": predicted_label,
        "spl_peak": round(peak_spl, 2),
        "spl_rms": round(rms_spl, 2),
        "estimated_distance": estimated_distance,
        "direction": direction
    }

# 스펙트럴 감산 함수 (Wiener 필터링 대체)
def spectral_subtraction(y, sr, noise_estimation_frames=0.6):
    # STFT 계산
    f, t, Zxx = stft(y, fs=sr)
    mag = np.abs(Zxx)
    phase = np.angle(Zxx)
    
    # 초기 프레임에서 소음 스펙트럼 추정
    noise_mag = np.mean(mag[:, :noise_estimation_frames], axis=1)
    
    # 스펙트럴 감산
    clean_mag = np.maximum(mag - noise_mag[:, np.newaxis], 0)
    
    # 역 STFT로 신호 복원
    y_clean = istft(clean_mag * np.exp(1j * phase), fs=sr)[1]
    return y_clean

# 배경 소음 제거 함수 (스펙트럴 감산 사용)
def remove_background_noise(audio_bytes, background_bytes, sr=44100):
    y, _ = librosa.load(io.BytesIO(audio_bytes), sr=sr, mono=False)
    y_bg, _ = librosa.load(io.BytesIO(background_bytes), sr=sr, mono=False)

    # 오디오 클리핑
    y = np.clip(y, -1.0, 1.0)
    y_bg = np.clip(y_bg, -1.0, 1.0)

    # 스펙트럴 감산 적용
    y_clean = spectral_subtraction(y, sr, noise_estimation_frames=5)
    y_clean = np.nan_to_num(y_clean, nan=0.0, posinf=0.0, neginf=0.0)

    # MFCC 계산
    mfccs_clean = librosa.feature.mfcc(y=y_clean, sr=sr, n_mfcc=50)
    features = np.mean(mfccs_clean, axis=1).astype(float)
    return features

# 무음 구간 감지 및 배경 소음 제거 (스펙트럴 감산 사용)
def detect_silence_and_remove_noise(file_bytes, sr=44100):
    # 오디오 로드 (스테레오로 로드하더라도)
    y, _ = librosa.load(io.BytesIO(file_bytes), sr=sr, mono=False)
    
    # MFCC 계산 전 모노로 변환
    y_mono = librosa.to_mono(y) if y.ndim > 1 else y

    # 무음 구간 감지 (모노 신호 사용)
    intervals = librosa.effects.split(y_mono, top_db=20)
    if len(intervals) == 0:
        mfccs = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=50)
        return np.mean(mfccs, axis=1).astype(float)

    # 무음 구간 추출 (intervals 외 영역)
    silence_samples = []
    for i in range(len(intervals) + 1):
        start = intervals[i-1][1] if i > 0 else 0
        end = intervals[i][0] if i < len(intervals) else len(y_mono)
        silence_samples.extend(y_mono[start:end])
    y_silence = np.array(silence_samples) if silence_samples else y_mono

    # 스펙트럴 감산 적용 (모노 신호 사용)
    y_clean = spectral_subtraction(y_mono, sr, noise_estimation_frames=5)
    y_clean = np.nan_to_num(y_clean, nan=0.0, posinf=0.0, neginf=0.0)

    # MFCC 계산 후 평균을 내어 특징 벡터 생성
    mfccs_clean = librosa.feature.mfcc(y=y_clean, sr=sr, n_mfcc=50)
    features = np.mean(mfccs_clean, axis=1).astype(float)
    return features


# 모델 예측 (고정값 적용)
@app.post("/predict/")
async def predict(file: UploadFile = File(...), background: UploadFile = File(None)):
    file_bytes = await file.read()
    print(f"파일 이름: {file.filename}")

   # 배경 소음 제거 로직
    if background:
        background_bytes = await background.read()
        features = remove_background_noise(file_bytes, background_bytes)
    else:
        # WAV 파일에서 무음 구간으로 배경 소음 제거
        features = detect_silence_and_remove_noise(file_bytes)

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
    result = analyze_audio(file_bytes, detected_noise)
    result["confidence"] = float(round(max_prob, 4))
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