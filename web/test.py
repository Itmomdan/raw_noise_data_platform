import streamlit as st
from streamlit_webrtc import webrtc_streamer

st.title("🎙️ WebRTC 오디오 테스트")

webrtc_streamer(
    key="simple-audio",
    media_stream_constraints={"video": False, "audio": True},
    rtc_configuration={
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {
                "urls": "turn:openrelay.metered.ca:80",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
        ]
    }
)
