---
name: bustago-ml
description: "BUSTAGO ML 파이프라인 구현 스킬. 혼잡도 데이터 수집(collect_congestion.py), Random Forest 학습(train_rf.py), 모델 직렬화(joblib), 예측 인터페이스(predict.py), 수집기 통합(pipeline.py). ML 모델 학습, 데이터 수집 파이프라인, Feature Engineering, 예측 함수 구현 시 반드시 이 스킬을 사용."
---

# BUSTAGO ML Pipeline

## 프로젝트 컨텍스트
- 기존 완성 코드: collect_boarding.py, collect_weather.py, build_features.py
- Feature 컬럼: hour, weekday, weather, temperature, rain, prev_boarding, prev_alighting, route_count, boarding, alighting
- Label: 0(여유), 1(보통), 2(혼잡), 3(매우혼잡) -- quartile 기반
- API 키: .env (SEOUL_OPENDATA_API_KEY, DATA_GO_KR_API_KEY)
- 데이터 경로: data/seoul_boarding/, data/weather/, data/features/

## Task 1: collect_congestion.py

서울시 버스도착정보 API에서 차내혼잡도를 수집한다.

**API 정보** (test_api_v2.py 참조):
- URL: http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll
- 파라미터: serviceKey, busRouteId, resultType=json
- 응답 필드: rerdie_Div1 (혼잡구분), reride_Num1 (혼잡코드), full1 (만차여부)
- 인증: DATA_GO_KR_API_KEY

**구현 패턴** (collect_boarding.py 따름):
- dotenv로 .env 로드, 경로는 os.path 기반
- requests.get + timeout, time.sleep(0.5)
- 결과를 pandas DataFrame으로 변환
- data/congestion/ 하위에 CSV 저장

**출력 컬럼**: bus_route_id, station_name, station_id, congestion_level, congestion_code, is_full, collected_at

## Task 2: pipeline.py

3개 수집기를 통합 실행한다.

```python
def run_pipeline(use_cached=True):
    """
    use_cached=True: 기존 CSV가 있으면 재수집하지 않음
    1. 승하차 데이터 수집 (또는 기존 CSV 로드)
    2. 기상 데이터 수집
    3. 혼잡도 데이터 수집
    4. build_features.py 호출하여 Feature DataFrame 생성
    5. 결과 저장: data/features/train_features.csv
    """
```

## Task 3: train_rf.py

Random Forest 모델을 학습하고 평가한다.

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# 1. data/features/train_features.csv 로드
# 2. X = feature_cols 10개, y = label
# 3. train_test_split(test_size=0.2, random_state=42, stratify=y)
# 4. RandomForestClassifier(n_estimators=100, random_state=42)
# 5. cross_val_score(cv=5) 출력
# 6. fit → predict → classification_report + confusion_matrix 출력
# 7. joblib.dump(model, "ml/models/rf_model.pkl")
# 8. Feature importance 출력
```

## Task 4: predict.py

학습된 모델로 혼잡도를 예측하는 인터페이스를 제공한다.

```python
LABEL_MAP = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}
FEATURE_COLS = ["hour", "weekday", "weather", "temperature", "rain",
                "prev_boarding", "prev_alighting", "route_count",
                "boarding", "alighting"]

def predict_congestion(features: dict) -> dict:
    """
    입력: {"hour": 8, "weekday": 1, "weather": 0, "temperature": 22.0,
           "rain": 0, "prev_boarding": 45, "prev_alighting": 30,
           "route_count": 12, "boarding": 0, "alighting": 0}
    출력: {"level": 2, "label": "혼잡",
           "probabilities": [0.1, 0.2, 0.5, 0.2]}
    """
```

## Task 5: 모델 계약서

_workspace/01_ml_model_contract.json:
```json
{
  "model_path": "ml/models/rf_model.pkl",
  "input_features": ["hour","weekday","weather","temperature","rain",
                      "prev_boarding","prev_alighting","route_count",
                      "boarding","alighting"],
  "input_types": {
    "hour": "int", "weekday": "int", "weather": "int",
    "temperature": "float", "rain": "int",
    "prev_boarding": "int", "prev_alighting": "int",
    "route_count": "int", "boarding": "int", "alighting": "int"
  },
  "output": {
    "level": "int (0-3)",
    "label": "str (여유|보통|혼잡|매우혼잡)",
    "probabilities": "list[float] length 4"
  },
  "predict_function": "ml.models.predict.predict_congestion",
  "label_map": {"0": "여유", "1": "보통", "2": "혼잡", "3": "매우혼잡"}
}
```
