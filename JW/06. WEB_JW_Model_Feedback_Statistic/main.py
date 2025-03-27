import subprocess
import os
import time

# FastAPI 서버 실행
def run_fastapi():
    subprocess.Popen(["uvicorn", "fastapi_app_JW:app", "--reload", "--port", "8006"])

# Streamlit 서버 실행
def run_streamlit():
    subprocess.Popen(["streamlit", "run", "home.py", "--server.port", "8506"])

if __name__ == "__main__":
    # FastAPI 서버 실행
    run_fastapi()
    
    # 잠시 기다린 후 Streamlit 실행
    time.sleep(2)  # FastAPI 서버가 준비되기 전에 Streamlit이 실행되면 문제가 될 수 있어서 잠시 기다림
    run_streamlit()

    print("FastAPI와 Streamlit이 모두 실행 중입니다.")
