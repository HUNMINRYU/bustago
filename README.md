# 🚌 BUSTAGO - 버스 정류장 혼잡도 예측 시스템

[![CI](https://github.com/HUNMINRYU/bustago/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/HUNMINRYU/bustago/actions/workflows/ci.yml)

> "30분 후, 정류장이 여유로워집니다"  
> 서울시 공공데이터로 설계한 결합 모델을 광주 환경(대학 셔틀 + 시내버스)에 적용하여,  
> 승차장 혼잡도를 예측하고 학생의 탑승 의사결정을 지원합니다.

---

## 📌 프로젝트 소개

**BUSTAGO**는 서울시 버스도착정보 API(차내혼잡도 포함)와 승하차 이력 데이터를 활용하여  
**"정류장 대기 혼잡도 + 버스 내부 혼잡도 → 탑승 가능성 예측"** 결합 모델을 설계·검증한 후,  
이 모델 구조를 광주대학교 인성관 정류장에 직접 적용하여 운영하는 시스템입니다.

### 시스템 구조
| 레이어 | 내용 |
|--------|------|
| **데이터** | 서울시 공공데이터(차내혼잡도·승하차 이력·기상) 기반 학습 |
| **혼잡도 모델** | **운영 = RandomForest** (`rf_model.pkl` 2.3MB, n=100, 6 feature, 2026-05-16 재학습) · **폴백 = rule_based** (`backend/seeds/rule_based.py`, 광주대 통학 패턴, 의존성 0). LightGBM 듀얼 트랙은 2026-05-17 단순화로 `archive/ml_lightgbm/`에 이관. |
| **AI 카운팅** | 광주대 인성관 정류장 — Jetson Orin Nano(YOLOv11+DeepSORT)로 실시간 대기 인원 수집 |
| **혼잡도 예측** | 서울 학습 모델 → 광주 정류장 직접 적용 (혼잡도 4단계 기준은 국토부 표준으로 동일) |
| **사용자 인터페이스** | 학생 PWA(혼잡도 + 노선 추천) + 운영자 Admin 대시보드(실시간 카운팅) |

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
![LightGBM](https://img.shields.io/badge/LightGBM-02569B?style=flat)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikitlearn&logoColor=white)
![YOLOv11](https://img.shields.io/badge/YOLOv11-00FFFF?style=flat&logo=ultralytics&logoColor=black)
![DeepSORT](https://img.shields.io/badge/DeepSORT-FF6F61?style=flat)

### Backend
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat&logo=mysql&logoColor=white)

### Frontend
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat&logo=chartdotjs&logoColor=white)
![Leaflet.js](https://img.shields.io/badge/Leaflet.js-199900?style=flat&logo=leaflet&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-5A0FC8?style=flat&logo=pwa&logoColor=white)

### Hardware
![Jetson](https://img.shields.io/badge/Jetson%20Orin%20Nano-76B900?style=flat&logo=nvidia&logoColor=white)
![RaspberryPi](https://img.shields.io/badge/Raspberry%20Pi%204-C51A4A?style=flat&logo=raspberrypi&logoColor=white)

### Design
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=flat&logo=figma&logoColor=white)

---

## 📁 폴더 구조
```
bustago/
├── backend/                # Flask REST API (9개 엔드포인트), SQLite/MySQL DB
├── frontend/               # 학생 PWA + 운영자 PC 대시보드
│   ├── student/            #   학생용 모바일 PWA (혼잡도 + 노선 추천)
│   ├── admin/              #   운영자 PC 대시보드 (Chart.js, Leaflet.js, 실시간 카운팅 패널)
│   └── shared/             #   공용 API 래퍼
├── ml/                     # 혼잡도 예측 파이프라인 (RandomForest 운영)
│   ├── data_collection/    #   서울시 API 데이터 수집 (혼잡도·승하차·기상)
│   ├── preprocessing/      #   전처리 + Feature 결합
│   └── models/             #   학습 + 예측 (rf_model.pkl 운영, lgbm_model.pkl 광주 데이터 확보 후 생성 예정)
├── hardware/               # Jetson AI 카운팅 (counter.py) + Watchdog 스크립트 (watchdog_jetson/pi.sh)
├── docs/                   # 프로젝트 산출물
│   ├── 01_계획분석/        #   계획서, 요구사항, 업무흐름도, 기술조사
│   ├── 02_설계/            #   아키텍처, DB설계, 화면설계, 하드웨어 개념도, 물리 설치 설계도
│   ├── 03_구축/            #   하드웨어 연동 설계, 팀원 작업배분, 시연 계획서, HW 설치 가이드 Part1/2
│   ├── 04_테스트/          #   ML 단위 테스트, Backend pytest, AI 카운팅 정확도 리포트 템플릿
│   ├── 05_배포/            #   하드웨어 구매검토 보고서 v5 (최신)
│   ├── 06_조사데이터/      #   설문결과, EDA 분석, API 비교, 유사프로젝트 사례분석
│   ├── 발표자료/           #   PPT, 대본, 포스터, 슬라이드 구조
│   └── _회의준비/          #   구두 설명 가이드 3종 + 데모 실행 가이드
├── CONTRIBUTING.md         # AI 산출물 검토 프로세스 + Git 규칙
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
| 현장 카운팅 | Jetson Orin Nano — YOLOv11+DeepSORT Line Crossing | Ground Truth (2-3단계) | 🔄 HW 설치 후 진행 |

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

### 2a. Docker Compose로 한 번에 (권장, 2026-05-16~)
```bash
# .env 준비 (없으면 .env.example 복사 후 필요한 키 채우기)
cp .env.example .env  # 한 번만

# MySQL + backend + frontend 동시 기동
docker compose up -d

# 상태 확인
docker compose ps                 # mysql healthy, backend healthy 표시
docker compose logs -f backend    # 로그 추적
curl http://localhost:5000/api/health

# 종료
docker compose down               # 컨테이너 제거 (볼륨 보존)
docker compose down -v            # 데이터까지 초기화 (개발 환경)
```

> docker compose는 `mysql:8.0`을 자동 띄우고 `backend/schema.sql`로 초기화한다.
> Backend는 MySQL 연결 실패 시 SQLite로 자동 폴백(backend/models/db.py) — Docker 없이도 동작.

### 2b. 로컬에서 직접 (Docker 없이)
```bash
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 프론트엔드
```bash
# 프론트엔드 정적 서버 시작 (포트 8080, API 프록시 포함)
# 자세한 실행법: docs/_회의준비/데모_실행_가이드.md 참조

# WSL2 환경에서 브라우저 열기
cmd.exe /c start http://localhost:8080/student/index.html   # 학생 PWA
cmd.exe /c start http://localhost:8080/admin/index.html     # 운영자 대시보드

# 일반 Linux/Mac
open http://localhost:8080/student/index.html               # Mac
xdg-open http://localhost:8080/student/index.html           # Linux
```

### 4. ML 모델
```bash
cd ml
pip install -r ../backend/requirements.txt  # 공용 의존성 (RF 운영용)
python models/predict.py                     # 혼잡도 예측 테스트 (현재 rf_model.pkl 사용)

# RandomForest 재학습 (필요 시)
python models/train_rf.py

# LightGBM은 archive/ml_lightgbm/에 보존 (2026-05-17 단순화 묶음 B로 이관). 광주 자체
# 데이터 확보 후 비교 학습이 필요해질 때 복원 — 가이드: archive/ml_lightgbm/README.md
```
> 현재 운영 모델은 `rf_model.pkl` (학습 완료, 225KB). `lgbm_model.pkl`이 존재하면 `predict.py`가 자동으로 LGBM을 우선 사용합니다.

### 5. AI 카운팅 (Jetson / PC 웹캠)
```bash
cd hardware
pip install -r requirements.txt
# PC 웹캠 테스트 (디버그 모드)
python counter.py --camera 0 --model yolo11n.pt --debug
# Jetson 배포
python counter.py --camera 0 --model yolo11n.engine --server http://SERVER_IP/api/crowd-count
```

---

## 📅 개발 기간

**2026.03 ~ 2026.06** (RISE 캡스톤디자인)

| 마일스톤 | 일정 |
|----------|------|
| 1차 발표/시연 | 5.21 |
| 교내 경진대회 | 5.28 |
| 최종 결과보고서 | 6.4 |
