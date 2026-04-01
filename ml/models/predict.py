"""
BUSTAGO - 혼잡도 예측 인터페이스
학습된 Random Forest 모델을 로드하여 혼잡도를 예측한다.

Backend에서 호출하는 함수:
    predict_congestion(features: dict) -> dict

Usage:
    from ml.models.predict import predict_congestion

    result = predict_congestion({
        "hour": 8,
        "weekday": 1,
        "weather": 0,
        "temperature": 20.0,
        "prev_boarding": 50,
        "prev_alighting": 30,
        "route_count": 12,
    })
    # result: {"level": 2, "label": "혼잡", "probabilities": [0.1, 0.2, 0.5, 0.2]}
"""

import os
import numpy as np
import joblib

# Feature 컬럼 순서 (train_rf.py 기준 - rain/boarding/alighting 제거)
FEATURE_COLS = [
    "hour", "weekday",
    "weather", "temperature",
    "prev_boarding", "prev_alighting",
    "route_count",
]

LABEL_NAMES = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}

# 모델 경로 (이 파일 기준)
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "rf_model.pkl")

# 모델 캐시 (한 번만 로드)
_model_cache = None


def load_model(model_path: str = None):
    """학습된 모델을 로드한다. 캐시하여 재사용."""
    global _model_cache

    if model_path is None:
        model_path = DEFAULT_MODEL_PATH

    if _model_cache is not None:
        return _model_cache

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"모델 파일 없음: {model_path}\n"
            f"먼저 train_rf.py를 실행하여 모델을 학습하세요."
        )

    _model_cache = joblib.load(model_path)
    return _model_cache


def predict_congestion(features: dict, model_path: str = None) -> dict:
    """
    혼잡도를 예측한다.

    Args:
        features: dict - Feature 값 딕셔너리
            필수 키: hour, weekday, weather, temperature,
                     prev_boarding, prev_alighting, route_count
        model_path: str - 모델 파일 경로 (기본: rf_model.pkl)

    Returns:
        dict:
            level (int): 혼잡도 등급 (0~3)
            label (str): 혼잡도 라벨 (여유/보통/혼잡/매우혼잡)
            probabilities (list[float]): 각 등급 확률 [여유, 보통, 혼잡, 매우혼잡]
    """
    model = load_model(model_path)

    # Feature 배열 생성 (컬럼 순서 보장)
    feature_values = []
    for col in FEATURE_COLS:
        val = features.get(col, 0)
        feature_values.append(float(val))

    X = np.array([feature_values])

    # 예측
    level = int(model.predict(X)[0])
    probabilities = model.predict_proba(X)[0].tolist()

    # 확률 배열이 4개 미만인 경우 (학습 데이터에 없는 클래스) 0으로 패딩
    while len(probabilities) < 4:
        probabilities.append(0.0)

    # 소수점 4자리 반올림
    probabilities = [round(p, 4) for p in probabilities]

    return {
        "level": level,
        "label": LABEL_NAMES.get(level, "알수없음"),
        "probabilities": probabilities,
    }


def predict_batch(features_list: list, model_path: str = None) -> list:
    """
    여러 건의 혼잡도를 한 번에 예측한다.

    Args:
        features_list: list[dict] - Feature 딕셔너리 리스트
        model_path: str - 모델 파일 경로

    Returns:
        list[dict]: 예측 결과 리스트
    """
    model = load_model(model_path)

    X = []
    for features in features_list:
        row = [float(features.get(col, 0)) for col in FEATURE_COLS]
        X.append(row)

    X = np.array(X)
    levels = model.predict(X).astype(int)
    probas = model.predict_proba(X)

    results = []
    for i in range(len(levels)):
        probs = probas[i].tolist()
        while len(probs) < 4:
            probs.append(0.0)

        results.append({
            "level": int(levels[i]),
            "label": LABEL_NAMES.get(int(levels[i]), "알수없음"),
            "probabilities": [round(p, 4) for p in probs],
        })

    return results


if __name__ == "__main__":
    # 테스트 예측
    test_input = {
        "hour": 8,
        "weekday": 1,
        "weather": 0,
        "temperature": 20.0,
        "prev_boarding": 50,
        "prev_alighting": 30,
        "route_count": 12,
    }

    print("=== BUSTAGO 혼잡도 예측 테스트 ===\n")
    print(f"입력: {test_input}\n")

    try:
        result = predict_congestion(test_input)
        print(f"예측 결과:")
        print(f"  등급: {result['level']} ({result['label']})")
        print(f"  확률: {result['probabilities']}")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
