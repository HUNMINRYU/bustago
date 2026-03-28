# 🤖 ML — 혼잡도 예측 모델

> 서울시 공공데이터 기반 결합 모델을 설계·검증하고, 광주 환경에 재학습(retrain)하여 적용합니다.

---

## 📁 디렉토리 구조

```
ml/
├── data_collection/
│   ├── collect_congestion.py    # 혼잡도 실시간 수집 (서울시 버스도착정보 API)
│   ├── collect_boarding.py      # 승하차 이력 수집
│   ├── collect_weather.py       # 기상청 API
│   └── pipeline.py              # 통합 파이프라인 (main)
├── preprocessing/
│   └── build_features.py        # 전처리 + Feature 결합
├── models/
│   └── train_rf.py              # Random Forest 학습
└── README.md
```

---

## 🔄 파이프라인 흐름

```
[데이터 수집]           [전처리]              [모델 학습]
collect_congestion ─┐
collect_boarding  ──┼─→ build_features.py ──→ train_rf.py
collect_weather  ───┘
```

1. **데이터 수집** (`data_collection/`): 서울시 API, 승하차 이력, 기상청 API에서 원시 데이터 수집
2. **전처리** (`preprocessing/`): 결측치 처리, 시간대 인코딩, Feature 결합
3. **모델 학습** (`models/`): Random Forest로 혼잡도 4단계 분류 학습

---

## ⚙️ 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 데이터 수집 파이프라인 실행
python data_collection/pipeline.py

# 3. 전처리 및 Feature 결합
python preprocessing/build_features.py

# 4. 모델 학습
python models/train_rf.py
```

---

## 📊 주요 Feature

| Feature | 출처 | 설명 |
|---------|------|------|
| 차내혼잡도 | 서울시 API | 버스 내부 혼잡 수준 |
| 승차 인원 | 승하차 이력 | 정류장별 시간대별 승차 수 |
| 하차 인원 | 승하차 이력 | 정류장별 시간대별 하차 수 |
| 기온 | 기상청 API | 현재 기온 (°C) |
| 강수확률 | 기상청 API | 강수 확률 (%) |
| 요일/시간대 | 파생 변수 | 요일 인코딩, 시간대 구간 |
