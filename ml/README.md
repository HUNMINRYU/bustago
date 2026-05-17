# 🤖 ML — 혼잡도 예측 모델

> 서울시 공공데이터 기반 혼잡도 4단계 분류 파이프라인.
>
> - **운영 모델 (단일)**: RandomForest (`rf_model.pkl` 2.3MB, 학습 완료) ← Backend가 사용
> - **폴백**: `backend/seeds/rule_based.py` (광주대 통학 패턴 hour×weekday 기반, 의존성 0)
> - **호출 체인**: backend → ML predict → 실패 시 rule_based → 실패 시 DUMMY (3단 폴백)
>
> 2026-05-17 단순화 B: LightGBM 학습 인프라는 `archive/ml_lightgbm/`로 이관 (모델 파일 미생성·미운영이었던 듀얼 트랙 정리).

---

## 📁 디렉토리 구조

```
ml/
├── data_collection/
│   ├── collect_congestion.py       # 혼잡도 실시간 수집 (서울시 버스도착정보 API)
│   ├── collect_boarding.py         # 승하차 이력 수집
│   ├── collect_weather.py          # 기상청 API
│   ├── test_collect_congestion.py  # Mock 단위 테스트 (pytest 3건)
│   └── pipeline.py                 # 통합 파이프라인 (main)
├── preprocessing/
│   └── build_features.py           # 전처리 + Feature 결합
├── models/
│   ├── train_rf.py                 # RandomForest 학습 — 운영 모델 생성
│   ├── rf_model.pkl                # RandomForest 학습 모델 (2.3MB, n=100) ← 운영 중
│   └── predict.py                  # 예측 인터페이스 (RF 단일 로드)
└── README.md
```

> 폴백 모듈: `backend/seeds/rule_based.py` (sklearn 미설치 환경에서도 동작)
> Archive: `archive/ml_lightgbm/` (LightGBM 학습 인프라 복원 가이드 포함)

---

## 🔄 파이프라인 흐름

```
[데이터 수집]           [전처리]              [모델 학습]      [추론]
collect_congestion ─┐
collect_boarding  ──┼─→ build_features.py ──→ train_rf.py ──→ predict.py
collect_weather  ───┘                                        ↑ ML 실패 시
                                          backend.seeds.rule_based ──┘
```

1. **데이터 수집** (`data_collection/`): 서울시 API, 승하차 이력, 기상청 API에서 원시 데이터 수집
2. **전처리** (`preprocessing/`): 결측치 처리, 시간대 인코딩, Feature 결합
3. **모델 학습** (`models/`): RandomForest로 4단계 분류 학습 (운영)
4. **추론** (`models/predict.py`): Backend에서 호출하는 예측 인터페이스
5. **폴백** (`backend.seeds.rule_based`): ML 실패 시 광주대 통학 패턴 rule-based 추정

---

## ⚙️ 실행 방법

```bash
# 1. 의존성 설치
pip install -r ../backend/requirements.txt   # RandomForest 운영용

# 2. 데이터 수집 파이프라인 실행
python data_collection/pipeline.py

# 3. 전처리 및 Feature 결합
python preprocessing/build_features.py

# 4. RandomForest 학습 (필요 시 재학습)
python models/train_rf.py

# 5. 예측 테스트
python models/predict.py
```

---

## 📊 모델 사양

### RandomForest (현재 운영 모델, 2026-05-16 재학습)

| 항목 | 값 |
|------|-----|
| 알고리즘 | RandomForestClassifier (scikit-learn) |
| 하이퍼파라미터 | `n_estimators=100, max_depth=10, min_samples_leaf=5, max_features=sqrt` |
| 모델 파일 | `rf_model.pkl` (2.3 MB) ← **운영 중** |
| 학습 데이터 | 서울시 공공데이터 14,616건 (Feature 6개, weekday 제거 후) |
| 라벨 | 0(여유) / 1(보통) / 2(혼잡) / 3(매우혼잡) |
| 실측 성능 (2026-05-16) | Accuracy 0.9993 / F1 macro 0.9993 / CV 5-fold 0.9991 (±0.0007) |
| 변경 이력 | 2026-03-31 초기(n=10, 7 feat, 0.2MB, Acc 0.9000) → 2026-05-16 weekday 제거(n=10, 6 feat, Acc 0.9973) → 2026-05-16 n=100 (현재) |

> 주의: 합성/quantile 라벨링 결과로 Accuracy가 비현실적으로 높음 (진단 §6).
> 광주대 자체 데이터로 검증 필요 — Phase 3 이후 트랙.

### 학습 결과 진화 (운영 모델 RandomForest)

| 시점 | 설정 | Features | Accuracy | F1 macro | CV 5-fold | 모델 크기 |
|---|---|---|---|---|---|---|
| 2026-05-07 (합성 500행) | n=10, depth=10 | 7 (with weekday placeholder) | 0.9000 | 0.8850 | — | 0.2 MB |
| 2026-05-16 (실 14,616건, weekday 제거) | n=10, depth=10 | 6 | 0.9973 | 0.9973 | 0.9979 ±0.0013 | 0.2 MB |
| 2026-05-16 (n=100 채택) | n=100, depth=10 | 6 | 0.9993 | 0.9993 | 0.9991 ±0.0007 | 2.3 MB |
| **2026-05-17 (현재 운영, weather 제거)** | **n=100, depth=10** | **4** | **0.9983** | **0.9983** | **0.9960 ±0.0029** | **2.9 MB** |

> 2026-05-17 단순화 C 결과: weather/temperature 제거 후 hour feature importance 0.81로 집중 (이전 0.49). CV std는 0.0007 → 0.0029로 약간 증가했으나 절대 안정성 유지.

### Rule-based Fallback (`backend/seeds/rule_based.py`, 2026-05-17 추가)

| 항목 | 값 |
|------|-----|
| 알고리즘 | 광주대 통학 패턴 hour×weekday 룰 |
| 의존성 | 없음 (sklearn 미설치 환경에서도 동작) |
| 정확도 | 미측정 (직관 기반) — 광주 자체 데이터로 후일 검증 |
| 용도 | ML 호출 실패 시 폴백, MVP 단순화 대안 |

> ⚠️ 위 RF 수치는 합성/quantile 라벨링 결과로 비현실적으로 높음. 광주 현장 실측 검증 필요 (Phase 3 이후).
> 본 한계는 `docs/04_테스트/모델_신뢰성_한계_진술서.md`에 상세 명시.

### Archived (2026-05-17 단순화 B)

| 항목 | Archive 위치 | 사유 |
|---|---|---|
| `train_lgbm.py` + `train_lgbm_fallback.py` | `archive/ml_lightgbm/` | LightGBM 학습 인프라 — 모델 파일 미생성, 듀얼 트랙 정리. 광주 데이터 확보 후 부활 검토. |

### 활성 Feature (4개, 2026-05-17 갱신)

| Feature | 출처 | 설명 | Feature Importance |
|---------|------|------|--------------------|
| hour | 파생 변수 | 시간대 (0-23) | **0.81** |
| route_count | 서울시 API | 경유 노선 수 | 0.10 |
| prev_boarding | 승하차 이력 | 이전 시간대 승차 수 | 0.05 |
| prev_alighting | 승하차 이력 | 이전 시간대 하차 수 | 0.04 |

### Deprecated Features

| Feature | 제거일 | 사유 |
|---|---|---|
| weekday | 2026-05-16 | 서울 공공데이터(use_month 월 단위 집계)에 요일 정보 없음 (진단 P0). backend API에서는 호환성 위해 파라미터로 받지만 ML 호출에 미포함. rule_based 폴백에는 사용됨. |
| weather | 2026-05-17 | RF Feature Importance 0.07이었으나 외부 의존성(기상청 API)·운영 부담 대비 가치 낮다고 판단 (단순화 C). `/api/weather/current` + `weather_cache` 테이블 + `_parse_kma_items` 통째 정리. |
| temperature | 2026-05-17 | weather와 함께 제거. Importance 0.26으로 hour 다음 차였으나 MVP 단순화 우선. |

### 혼잡도 레이블

| level | label | 기준 |
|-------|-------|------|
| 0 | 여유 | ≤ 25th percentile |
| 1 | 보통 | 25-50th |
| 2 | 혼잡 | 50-75th |
| 3 | 매우혼잡 | > 75th |
