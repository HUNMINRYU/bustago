# 🚌 BUSTAGO - 버스 정류장 혼잡도 예측 시스템

> "30분 후, 정류장이 여유로워집니다"  
> 서울시 공공데이터로 설계한 결합 모델을 광주 환경(대학 셔틀 + 시내버스)에 적용하여,  
> 승차장 혼잡도를 예측하고 학생의 탑승 의사결정을 지원합니다.

---

## 📌 프로젝트 소개

**BUSTAGO**는 서울시 버스도착정보 API(차내혼잡도 포함)와 승하차 이력 데이터를 활용하여  
**"정류장 대기 혼잡도 + 버스 내부 혼잡도 → 탑승 가능성 예측"** 결합 모델을 설계·검증한 후,  
이 모델 구조를 광주대학교 셔틀버스 승차장과 시내버스 정류장에 재학습(retrain)하여 적용하는 시스템입니다.

### 3단계 파이프라인
| 단계 | 내용 |
|------|------|
| **1단계** | 서울시 공공데이터(차내혼잡도, 승하차 이력)로 결합 모델 구조 설계·검증 |
| **2단계** | 광주대 인성관 앞 셔틀 승차장에 모델 적용 (테스트베드 ①) |
| **3단계** | 광주대 정문 시내버스 정류장으로 확장 (테스트베드 ②) |

### 혼잡도 4단계
| 단계 | 기준 |
|------|------|
| 🟢 여유 | 대기 인원 적음, 탑승 가능성 높음 |
| 🟡 보통 | 평균 수준 |
| 🟠 혼잡 | 대기 인원 많음, 만차 가능성 있음 |
| 🔴 매우혼잡 | 만차 예상, 대안 교통 추천 |

### 사용자
| 사용자 | 화면 | 핵심 기능 |
|--------|------|----------|
| 학생 | 모바일 PWA | 셔틀 만차 예측, 행동 추천 ("지금 vs 나중") |
| 운영자 | PC 웹 대시보드 | 노선별 만차 통계, 증차 의사결정 지원 |

---

## 🛠 기술 스택

### AI / ML
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![RandomForest](https://img.shields.io/badge/Random%20Forest-228B22?style=flat)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikitlearn&logoColor=white)

### Backend
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)

### Frontend
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![Leaflet.js](https://img.shields.io/badge/Leaflet.js-199900?style=flat&logo=leaflet&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-5A0FC8?style=flat&logo=pwa&logoColor=white)

### Hardware
![RaspberryPi](https://img.shields.io/badge/Raspberry%20Pi%204-C51A4A?style=flat&logo=raspberrypi&logoColor=white)

### Design
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat&logo=figma&logoColor=white)

---

## 📁 폴더 구조
```
bustago/
├── backend/                # Flask REST API, MySQL/SQLite DB, 공공 API 연동
├── frontend/               # 학생 PWA + 운영자 PC 대시보드
│   ├── student/            #   학생용 모바일 PWA
│   ├── admin/              #   운영자 PC 대시보드 (Chart.js, Leaflet.js)
│   └── shared/             #   공용 API 래퍼
├── ml/                     # Random Forest 혼잡도 예측 파이프라인
│   ├── data_collection/    #   데이터 수집 (혼잡도, 승하차, 기상)
│   ├── preprocessing/      #   전처리 + Feature 결합
│   └── models/             #   학습 + 예측 (rf_model.pkl: 0.2MB)
├── hardware/               # Raspberry Pi 제어 (미구현 — 향후 연동 예정)
├── docs/                   # 프로젝트 산출물
│   ├── 00_하네스설계/      #   AI 에이전트 팀 하네스 아키텍처
│   ├── 01_계획분석/        #   계획서, 요구사항, 업무흐름도, 기술조사
│   ├── 02_설계/            #   아키텍처, DB설계, 화면설계
│   ├── 03_구축/            #   하네스 실행 결과, GStack 역할 구조
│   ├── 04_테스트/          #   (예정)
│   ├── 05_배포/            #   (예정)
│   ├── 06_조사데이터/      #   설문결과, EDA 분석
│   └── 발표자료/           #   PPT, 대본, 포스터
├── research_log.txt        # ML Autoresearch 12회 반복 실험 로그
└── README.md
```

---

## 📊 데이터 소스

| 데이터 | 출처 | 용도 | 상태 |
|--------|------|------|------|
| 버스도착정보 (차내혼잡도) | 서울시 공공데이터포털 API | 결합 모델 설계·검증 (1단계) | ✅ 수집 완료 |
| 승하차 이력 | 서울 열린데이터광장 | 정류장 혼잡 패턴 분석 (1단계) | ✅ 수집 완료 |
| 기상 데이터 | 기상청 API | 날씨 변수 반영 | ✅ 수집 완료 |
| 학생 설문 | 구글폼 (N≥50) | 필요성 검증 + 이용 패턴 | ✅ 완료 |
| 시내버스 승하차 인원 | 광주시 공공데이터포털 | 시내버스 모델 학습 (2-3단계) | 예정 |
| 셔틀 운행 기록 | 컴온버스 / 학생지원팀 | 셔틀 만차 패턴 학습 (2단계) | 예정 |
| 현장 카운팅 | 직접 수집 (2곳 × 2주) | Ground Truth (2-3단계) | 예정 |

---

## 👥 팀 같이타요

| 이름 | 역할 | 담당 | GitHub |
|------|------|------|--------|
| 류훈민 | 팀장 | AI 모델 설계, 공공데이터 분석, GitHub 관리 | [@HUNMINRYU](https://github.com/HUNMINRYU) |
| 박건우 | 부팀장 | 현장 카운팅, 설문조사, 문서화, Padlet 관리 | [@ganbolditgl](https://github.com/ganbolditgl) |
| 이트겔 | 백엔드 | Flask API, MySQL DB, 서울시/광주시/기상청 API 연동 | [@Geonwoopark38](https://github.com/Geonwoopark38) |
| 이건영 | 프론트엔드 | 학생 PWA, 운영자 대시보드, Figma 화면설계 | [@Leekunyoung-eng](https://github.com/Leekunyoung-eng) |

**참여기업**: 대상정보기술 (이정회 팀장 — 기술 자문)

---

## ⚙️ 설치 및 실행

### 1. 레포지토리 클론
```bash
git clone https://github.com/HUNMINRYU/bustago.git
cd bustago
```

### 2. 백엔드
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 프론트엔드
```bash
# 학생 PWA: frontend/student/index.html 을 브라우저에서 열거나 라이브 서버 사용
# 운영자 대시보드: frontend/admin/index.html
```

### 4. ML 모델
```bash
cd ml
pip install -r ../backend/requirements.txt  # 공용 의존성
python models/train_rf.py   # Random Forest 학습 (CV 0.9962, 0.2MB)
python models/predict.py    # 혼잡도 예측 테스트
```

---

## 📅 개발 기간

**2026.03 ~ 2026.06** (RISE 캡스톤디자인)

| 마일스톤 | 일정 |
|----------|------|
| 1차 발표/시연 | 5.21 |
| 교내 경진대회 | 5.28 |
| 최종 결과보고서 | 6.4 |