# 🤖 ML — 혼잡도 예측 모델

> 서울시 공공데이터 기반 혼잡도 4단계 분류 파이프라인.
>
> - **현재 운영**: RandomForest (`rf_model.pkl` 225KB, 학습 완료) ← Backend가 사용
> - **보조 (학습 인프라 완료)**: LightGBM (`train_lgbm.py` 작성됨, 모델 파일은 광주 현장 데이터 확보 후 생성 예정)
> - **자동 선택**: `predict.py` 호출 시 `lgbm_model.pkl`이 존재하면 LGBM, 없으면 `rf_model.pkl` fallback

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
│   ├── train_rf.py                 # RandomForest 학습 — **현재 운영 모델** 생성
│   ├── rf_model.pkl                # RandomForest 학습 모델 (225KB) ← **운영 중**
│   ├── train_lgbm.py               # LightGBM 학습 — `--compare` 옵션으로 RF 비교 가능 (광주 데이터 확보 후 실행 예정)
│   ├── predict.py                  # 예측 인터페이스 (lgbm_model.pkl 존재 시 우선, 없으면 rf fallback)
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
3. **모델 학습** (`models/`): RandomForest로 4단계 분류 학습 (현 운영), LightGBM은 광주 데이터 확보 후 전환 예정
4. **추론** (`models/predict.py`): Backend에서 호출하는 예측 인터페이스

---

## ⚙️ 실행 방법

```bash
# 1. 의존성 설치
pip install -r ../backend/requirements.txt   # 공용 (RandomForest 운영용)

# 2. 데이터 수집 파이프라인 실행
python data_collection/pipeline.py

# 3. 전처리 및 Feature 결합
python preprocessing/build_features.py

# 4-A. 현재 운영: RandomForest 재학습 (필요 시)
python models/train_rf.py

# 4-B. 보조: LightGBM 학습 (광주 데이터 확보 후 권장)
pip install lightgbm                          # 별도 설치 필요
python models/train_lgbm.py                   # 학습 → lgbm_model.pkl 생성
python models/train_lgbm.py --compare         # RF vs LGBM 성능 비교 출력

# 5. 예측 테스트 (자동 선택: lgbm 우선, 없으면 rf fallback)
python models/predict.py
```

---

## 📊 모델 사양

### RandomForest (현재 운영 모델, 2026-03-31 학습)

| 항목 | 값 |
|------|-----|
| 알고리즘 | RandomForestClassifier (scikit-learn) |
| 모델 파일 | `rf_model.pkl` (225 KB) ← **운영 중** |
| 학습 데이터 | 서울시 공공데이터 합성 (Feature 7개) |
| 라벨 | 0(여유) / 1(보통) / 2(혼잡) / 3(매우혼잡) |

### LightGBM (학습 인프라 작성 완료, 모델 파일 미생성 — 광주 데이터 확보 후 학습 예정)

| 항목 | 값 (`train_lgbm.py` 기준) |
|------|-----|
| 알고리즘 | LGBMClassifier |
| 하이퍼파라미터 | `n_estimators=300, max_depth=6, learning_rate=0.05, num_leaves=31` |
| 합성 데이터 벤치마크 (2026-05-07) | Accuracy 0.9400 / F1 (macro) 0.9319 / CV 5-fold 0.9340 ± 0.0215 |
| 모델 파일 | `lgbm_model.pkl` (학습 실행 후 1.7 MB 예상) ← 현재 **미생성** |

### 합성 데이터 벤치마크 (500행, 2026-05-07 실측 — 회의 근거용)

| 모델 | Accuracy | F1 (macro) | 학습시간 | 운영 상태 |
|------|:--------:|:----------:|:--------:|:---------|
| **RandomForest** | 0.9000 | 0.8850 | 0.01s | ✅ 운영 중 (`rf_model.pkl`) |
| LightGBM | **0.9400** | **0.9319** | 0.15s | ⏳ 학습 인프라만 작성, 광주 데이터 확보 후 전환 예정 |

> ⚠️ 위 벤치마크는 합성 데이터 500행 기준이며, 광주 현장 실측 데이터에서의 성능은 별도 검증 필요.

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
