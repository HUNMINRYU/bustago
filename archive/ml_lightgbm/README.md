# Archived: LightGBM 학습 인프라

> Archive 일자: 2026-05-17
> Archive 사유: Principal Engineer 진단 (2026-05-17) — MVP 단순화 묶음 B
> 원본 위치: `ml/models/train_lgbm.py`, `ml/models/train_lgbm_fallback.py`

## 배경

본 학습 인프라는 2026-05-07에 *RF 운영 + LGBM 후보* 듀얼 트랙으로 작성됐다.
그러나:

1. `lgbm_model.pkl`은 **생성된 적이 없음** (광주 데이터 확보 후 학습 예정으로 보류)
2. `ml/models/predict.py`의 LGBM-first 폴백 로직은 실제로는 항상 RF만 로드
3. 운영 모델 두 종류 유지는 책임 소재가 흐려짐 (Principal Engineer 진단 §3)
4. 5/16 weekday 제거로 6 feature 갱신 시 LGBM 코드도 동기 갱신했으나 실제 활용 0

→ **운영 모델은 RF 단일로 확정**, LGBM 인프라는 본 디렉토리로 archive.

## 복원 방법

광주 현장 데이터 확보 후 LightGBM 비교가 필요해질 시:

```bash
git mv archive/ml_lightgbm/train_lgbm.py ml/models/
git mv archive/ml_lightgbm/train_lgbm_fallback.py ml/models/
# ml/models/predict.py의 LGBM 분기 복원
# pip install lightgbm
# python ml/models/train_lgbm.py --compare
```

## 함께 단순화한 항목

- `ml/models/predict.py` LGBM-first 로직 제거 → RF 단일 로드
- `ml/README.md` "RF + LGBM 후보" 표현 제거 → "RF 운영 + rule_based fallback"
- 발표 슬라이드 6 갱신 (LGBM 6 feature → RF 6 feature)
