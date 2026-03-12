# 🚌 bustago - 스마트 버스정류장 혼잡도 안내 시스템

> 버스 정류장의 실시간 혼잡도를 AI로 분석하고, 승객에게 최적의 탑승 정보를 제공합니다.

---

## 📌 프로젝트 소개

**bustago**는 Raspberry Pi와 Pi Camera를 활용해 버스정류장의 혼잡도를 실시간으로 감지하고,  
YOLOv8 기반 인원 카운팅과 LSTM 예측 모델을 통해 혼잡도를 4단계로 분류하여  
정류장 현장 디스플레이 및 웹 대시보드에 안내하는 IoT + AI 통합 시스템입니다.

### 혼잡도 4단계
| 단계 | 기준 |
|------|------|
| 🟢 여유 | 대기 인원 적음 |
| 🟡 보통 | 평균 수준 |
| 🟠 혼잡 | 대기 인원 많음 |
| 🔴 매우혼잡 | 즉시 혼잡 대응 필요 |

---

## 🛠 기술 스택

### AI / ML
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=flat)
![LSTM](https://img.shields.io/badge/LSTM-FF6F00?style=flat)

### Backend
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)

### Frontend
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![Leaflet.js](https://img.shields.io/badge/Leaflet.js-199900?style=flat&logo=leaflet&logoColor=white)

### Hardware
![RaspberryPi](https://img.shields.io/badge/Raspberry%20Pi-C51A4A?style=flat&logo=raspberrypi&logoColor=white)

---

## 📁 폴더 구조
```
bustago/
├── hardware/       # Raspberry Pi 제어, Pi Camera, 디스플레이 출력
├── backend/        # Flask 서버, MySQL DB, 공공 버스 API 연동
├── frontend/       # 웹 대시보드, 실시간 시각화, 지도 연동
├── ml/             # YOLOv8 인원 카운팅, LSTM 혼잡도 예측 모델
└── docs/           # 프로젝트 문서, 회의록, 기획서
```

---

## 👥 팀원 소개

| 이름 | 역할 | GitHub |
|------|------|--------|
| 류훈민 | 팀장 / 프로젝트 총괄 | [@HUNMINRYU](https://github.com/HUNMINRYU) |
| 간볼딧글 | 부팀장 / 문서화 | [@ganbolditgl](https://github.com/ganbolditgl) |
| 박건우 | 백엔드 / DB | [@Geonwoopark38](https://github.com/Geonwoopark38) |
| 이건영 | 프론트엔드 | [@Leekunyoung-eng](https://github.com/Leekunyoung-eng) |

---

## ⚙️ 설치 및 실행 방법

### 1. 레포지토리 클론
```bash
git clone https://github.com/HUNMINRYU/bustago.git
cd bustago
```

### 2. 백엔드 실행
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 프론트엔드 실행
```bash
cd frontend
# index.html을 브라우저에서 열거나 라이브 서버 사용
```

### 4. ML 모델 실행
```bash
cd ml
pip install -r requirements.txt
python detect.py
```

---

## 📅 개발 기간

2025.03 ~ 2025.06 (RISE 캡스톤디자인)