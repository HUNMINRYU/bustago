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
│   ├── test_collect_congestion.py # Mock 단위 테스트
│   └── pipeline.py              # 통합 파이프라인 (main)
├── preprocessing/
│   └── build_features.py        # 전처리 + Feature 결합
├── models/
│   ├── train_rf.py              # Random Forest 학습 (Autoresearch 최적화 완료)
│   ├── predict.py               # 예측 인터페이스
│   └── rf_model.pkl             # 학습된 모델 (0.2MB)
└── README.md
```

---

## 🔄 파이프라인 흐름

```
[데이터 수집]           [전처리]              [모델 학습]        [추론]
collect_congestion ─┐
collect_boarding  ──┼─→ build_features.py ──→ train_rf.py ──→ predict.py
collect_weather  ───┘
```

1. **데이터 수집** (`data_collection/`): 서울시 API, 승하차 이력, 기상청 API에서 원시 데이터 수집
2. **전처리** (`preprocessing/`): 결측치 처리, 시간대 인코딩, Feature 결합
3. **모델 학습** (`models/`): Random Forest로 혼잡도 4단계 분류 학습
4. **추론** (`models/predict.py`): Backend에서 호출하는 예측 인터페이스

---

## ⚙️ 실행 방법

```bash
# 1. 의존성 설치 (backend/requirements.txt 공용)
pip install -r ../backend/requirements.txt

# 2. 데이터 수집 파이프라인 실행
python data_collection/pipeline.py

# 3. 전처리 및 Feature 결합
python preprocessing/build_features.py

# 4. 모델 학습
python models/train_rf.py

# 5. 예측 테스트
python models/predict.py
```

---

## 📊 모델 사양 (Autoresearch 최적화 후)

**알고리즘**: RandomForestClassifier
**하이퍼파라미터**: `n_estimators=10, max_depth=10, min_samples_leaf=5, max_features=sqrt`
**성능**: CV Mean Accuracy 0.9962 (+/- 0.0026)
**모델 크기**: 0.2 MB (Baseline 5.1MB 대비 96% 감소)
**학습 시간**: ~1.2초

### 활성 Feature (7개)

| Feature | 중요도 | 출처 | 설명 |
|---------|--------|------|------|
| hour | 0.39 | 파생 변수 | 시간대 (0-23) |
| temperature | 0.21 | 기상청 API | 현재 기온 (°C) |
| weekday | 0.14 | 파생 변수 | 요일 (0=월, 6=일) |
| route_count | 0.12 | 서울시 API | 경유 노선 수 |
| weather | 0.07 | 기상청 API | 날씨 코드 (0=맑음, 1=흐림, 2=비, 3=눈) |
| prev_boarding | 0.03 | 승하차 이력 | 이전 시간대 승차 수 |
| prev_alighting | 0.03 | 승하차 이력 | 이전 시간대 하차 수 |

### 제거된 Feature (Autoresearch 검증)

| Feature | 제거 사유 |
|---------|----------|
| rain | 중요도 0.001 미만 — 노이즈 |
| boarding | Leakage 위험 — 제거 시 CV 오히려 상승 |
| alighting | Leakage 위험 — 제거 시 CV 오히려 상승 |

### 혼잡도 레이블
| level | label | 기준 |
|-------|-------|------|
| 0 | 여유 | ≤ 25th percentile |
| 1 | 보통 | 25-50th |
| 2 | 혼잡 | 50-75th |
| 3 | 매우혼잡 | > 75th |
