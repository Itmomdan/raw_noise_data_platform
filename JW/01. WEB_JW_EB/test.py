import pyaudio

p = pyaudio.PyAudio()

# 모든 장치 정보 출력
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    print(f"ID: {i}, Name: {device_info['name']}, Input Channels: {device_info['maxInputChannels']}")

p.terminate()
