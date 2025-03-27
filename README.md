# 🔊 교통 소음 분류 기능 및 경고 알림 서비스, 담았소 

<div align="center">
  <img src="https://github.com/user-attachments/assets/8b1cae0c-f7d9-4d9d-8e86-4d2036274026" width="700"/>
</div>


<br>

> **멀티캠퍼스 데이터엔지니어**  <br/> **개발기간: 2025.01 ~ 2025.13**  <br/> **배포주소 : https://itmondan-noise-data-platform.streamlit.app/**

<br>

## 프로젝트 소개
**담았소**는 도심 속 교통 소음을 감지하고, 무심한 듯 담백하게 사용자에게 위험을 알려주는 소음 감지 서비스입니다.

- 사용자는 마이페이지에서 소음 종류별로 자신만의 알람 기준을 설정할 수 있습니다.
- 소음을 분석하여 예상 거리와 방향을 판단합니다. 
- 설정된 기준보다 높은 데시벨의 소음이 감지되면, 실시간 TTS 알림을 제공하고 보호자 이메일로 SOS 메시지가 발송됩니다. 
- 분류된 소음을 기반으로 소음 통계를 시각적으로 확인할 수 있습니다.  

위험 소음으로부터 사용자를 보호하고, 더 안전한 도시 생활을 위한 데이터 기반 서비스를 지향합니다.

<br>

## 팀원 소개 

<div align="center">

| **노은비** | **두지원** | **박은서** | **엄기영** |
| :------: |  :------: | :------: | :------: |
| [<img src="https://avatars.githubusercontent.com/selina7704" height=150 width=150> <br/> @selina7704](https://github.com/selina7704) | [<img src="https://avatars.githubusercontent.com/JiwonDu" height=150 width=150> <br/> @JiwonDu](https://github.com/JiwonDu) | [<img src="https://avatars.githubusercontent.com/EunSeo35" height=150 width=150> <br/> @EunSeo35](https://github.com/EunSeo35) | [<img src="https://avatars.githubusercontent.com/Eomcoco" height=150 width=150> <br/> @Eomcoco](https://github.com/Eomcoco) |

</div>

<br>

## 기술 스택 

### 개발 환경
![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-007ACC?style=for-the-badge&logo=Visual%20Studio%20Code&logoColor=white)
![Jupyter Notebook](https://img.shields.io/badge/Jupyter%20Notebook-F37626?style=for-the-badge&logo=Jupyter&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=Git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white)

### 백엔드 & 인프라
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)
![Amazon EC2](https://img.shields.io/badge/Amazon%20EC2-FF9900?style=for-the-badge&logo=Amazon%20AWS&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=MySQL&logoColor=white)

### AI & 데이터
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=TensorFlow&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-E25A1C?style=for-the-badge&logo=Apache%20Spark&logoColor=white)

### 프론트엔드
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)

### 협업 툴
![Slack](https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=Slack&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=Notion&logoColor=white)

<br>

## 시스템 아키텍처 

<div align="center">
  <img src="https://github.com/user-attachments/assets/74cfb413-ef99-4446-95fa-9934dbb13bec" width="800"/>
</div>

<br>

## 주요 기능 

- **교통소음 분류 기능**  
  음성 녹음 방식 또는 음성 파일 업로드 방식을 통해 소음을 분류합니다.  
  → 총 6개 클래스 분류: `차량경적`, `차량사이렌`, `차량주행음`, `이륜차경적`, `이륜차주행음`, `기타소음`

- **배경소음 제거 기능**  
  녹음된 오디오에서 주요 소리를 강조하고, 불필요한 배경 노이즈를 효과적으로 제거합니다.

- **거리 판단 기능**  
  측정된 데시벨을 바탕으로 소음원이 사용자로부터 어느 정도 떨어져 있는지 예측합니다.

- **방향 판단 기능**  
  스테레오 형식의 오디오 데이터를 활용해 소음이 발생한 방향(왼쪽/오른쪽)을 추정합니다.

- **맞춤형 알람 설정**  
  소음 유형별로 감도(`약`, `중`, `강`)를 선택하여 알람 임계치를 사용자 맞춤형으로 설정할 수 있습니다.

- **위험 소음 경고 알림**  
  설정한 데시벨 임계치를 초과하면 **실시간 TTS 알림**이 작동하며, 보호자 이메일로 **SOS 경고 메시지**가 자동 발송됩니다.








