# 🤖 ML — 혼잡도 예측 모델

> 서울시 공공데이터로 학습한 LightGBM 모델을 광주대학교 정류장 환경에 직접 적용합니다.
> (RandomForest는 lgbm_model.pkl 없을 경우 자동 fallback으로 사용)

---

## 📁 디렉토리 구조

```
ml/
├── data_collection/
│   ├── collect_congestion.py       # 혼잡도 실시간 수집 (서울시 버스도착정보 API)
│   ├── collect_boarding.py         # 승하차 이력 수집
│   ├── collect_weather.py          # 기상청 API
│   ├── test_collect_congestion.py  # Mock 단위 테스트
│   └── pipeline.py                 # 통합 파이프라인 (main)
├── preprocessing/
│   └── build_features.py           # 전처리 + Feature 결합
├── models/
│   ├── train_lgbm.py               # LightGBM 학습 (주 모델) — --compare 옵션으로 RF 비교 가능
│   ├── train_rf.py                 # Random Forest 학습 (fallback용)
│   ├── predict.py                  # 예측 인터페이스 (lgbm_model.pkl 우선, rf fallback)
│   ├── lgbm_model.pkl              # LightGBM 학습 모델 (1.7MB) ← 주 모델
│   └── train_lgbm_fallback.py      # ML 패키지 미설치 환경 대응 스크립트
└── README.md
```

---

## 🔄 파이프라인 흐름

```
[데이터 수집]           [전처리]              [모델 학습]          [추론]
collect_congestion ─┐
collect_boarding  ──┼─→ build_features.py ──→ train_lgbm.py ──→ predict.py
collect_weather  ───┘                     └─→ train_rf.py (fallback)
```

1. **데이터 수집** (`data_collection/`): 서울시 API, 승하차 이력, 기상청 API에서 원시 데이터 수집
2. **전처리** (`preprocessing/`): 결측치 처리, 시간대 인코딩, Feature 결합
3. **모델 학습** (`models/`): LightGBM으로 혼잡도 4단계 분류 학습
4. **추론** (`models/predict.py`): Backend에서 호출하는 예측 인터페이스

---

## ⚙️ 실행 방법

```bash
# 1. 의존성 설치
pip install -r ../backend/requirements.txt
pip install lightgbm   # LightGBM 별도 설치

# 2. 데이터 수집 파이프라인 실행
python data_collection/pipeline.py

# 3. 전처리 및 Feature 결합
python preprocessing/build_features.py

# 4. LightGBM 모델 학습 (주 모델)
python models/train_lgbm.py

# RF vs LightGBM 성능 비교 출력
python models/train_lgbm.py --compare

# 5. 예측 테스트
python models/predict.py
```

---

## 📊 모델 사양

### LightGBM (주 모델, 2026-05-07 확정)

| 항목 | 값 |
|------|-----|
| 알고리즘 | LGBMClassifier |
| 하이퍼파라미터 | `n_estimators=300, max_depth=6, learning_rate=0.05, num_leaves=31` |
| **Accuracy** | **0.9400** |
| **F1 (macro)** | **0.9319** |
| **CV (5-fold)** | **0.9340 ± 0.0215** |
| 모델 크기 | 1.7 MB |
| 학습 시간 | ~0.15초 |

### RF vs LightGBM 벤치마크 (합성 데이터 500행, 2026-05-07 실측)

| 모델 | Accuracy | F1 (macro) | 학습시간 |
|------|:--------:|:----------:|:--------:|
| RandomForest (fallback) | 0.9000 | 0.8850 | 0.01s |
| **LightGBM (주 모델)** | **0.9400** | **0.9319** | 0.15s |

### 활성 Feature (7개)

| Feature | 출처 | 설명 |
|---------|------|------|
| hour | 파생 변수 | 시간대 (0-23) |
| weekday | 파생 변수 | 요일 (0=월, 6=일) |
| weather | 기상청 API | 날씨 코드 (0=맑음, 1=흐림, 2=비, 3=눈) |
| temperature | 기상청 API | 현재 기온 (°C) |
| prev_boarding | 승하차 이력 | 이전 시간대 승차 수 |
| prev_alighting | 승하차 이력 | 이전 시간대 하차 수 |
| route_count | 서울시 API | 경유 노선 수 |

### 혼잡도 레이블

| level | label | 기준 |
|-------|-------|------|
| 0 | 여유 | ≤ 25th percentile |
| 1 | 보통 | 25-50th |
| 2 | 혼잡 | 50-75th |
| 3 | 매우혼잡 | > 75th |
