"""
BUSTAGO Backend -- /api/predict 엔드포인트
LRU Cache로 동일 피처 조합의 중복 예측 요청 시 ML 모델 호출 없이 즉시 반환.
"""

import re
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, abort

from backend.models.db import fetchone, execute
from backend.config import MODEL_PATH
from backend.extensions import limiter

predict_bp = Blueprint("predict", __name__)

# --- Prediction Cache (TTL 300초 = 5분) ---
_predict_cache = {}
_CACHE_TTL = 300


def _cache_key(features: dict) -> tuple:
    # 2026-05-16: weekday는 ML feature에서 제거되었지만 API 호환성 위해 cache key에 유지
    # (DB 컬럼에는 그대로 저장됨).
    return (features["hour"], features.get("weekday", -1), features["weather"],
            features.get("temperature", 20.0), features["route_count"])


def _cached_predict(features: dict) -> dict:
    """캐시된 예측 반환. 미스 시 ML 모델 호출 후 캐시 저장."""
    key = _cache_key(features)
    now = time.monotonic()

    entry = _predict_cache.get(key)
    if entry and (now - entry["ts"]) < _CACHE_TTL:
        return entry["result"]

    result = _do_predict(features)
    _predict_cache[key] = {"result": result, "ts": now}

    if len(_predict_cache) > 500:
        oldest_key = min(_predict_cache, key=lambda k: _predict_cache[k]["ts"])
        del _predict_cache[oldest_key]

    return result

# 더미 예측 (모델 파일 없을 때)
DUMMY_PREDICTION = {
    "level": 1,
    "label": "보통",
    "probabilities": [0.2, 0.5, 0.2, 0.1],
}

# 혼잡도별 추천 메시지
RECOMMENDATIONS = {
    0: "여유로운 시간대입니다. 편하게 이용하세요.",
    1: "보통 수준의 혼잡도입니다.",
    2: "혼잡이 예상됩니다. 다음 시간대를 추천합니다.",
    3: "매우 혼잡합니다. 가능하면 다른 시간대를 이용하세요.",
}


def _do_predict(features: dict) -> dict:
    """ML 모델로 예측. 모델 없으면 더미 반환."""
    try:
        from ml.models.predict import predict_congestion
        return predict_congestion(features, model_path=MODEL_PATH)
    except (FileNotFoundError, ImportError):
        return dict(DUMMY_PREDICTION)


@predict_bp.route("/api/predict")
@limiter.limit("30 per minute")
def predict():
    # 파라미터 파싱
    station_id = request.args.get("station_id")
    hour = request.args.get("hour")
    weekday = request.args.get("weekday")

    if not station_id:
        abort(400, description="station_id is required")
    if not re.fullmatch(r"[A-Za-z0-9]{3,10}", station_id):
        abort(400, description="station_id must be 3-10 alphanumeric characters")
    if hour is None:
        abort(400, description="hour is required")
    if not hour.isdigit():
        abort(400, description="hour must contain only numeric characters")

    try:
        hour = int(hour)
    except ValueError:
        abort(400, description="hour must be an integer (0-23)")

    if hour < 0 or hour > 23:
        abort(400, description="hour must be between 0 and 23")

    if weekday is not None:
        if not weekday.isdigit():
            abort(400, description="weekday must contain only numeric characters")
        try:
            weekday = int(weekday)
        except ValueError:
            abort(400, description="weekday must be an integer (0-6)")
        if weekday < 0 or weekday > 6:
            abort(400, description="weekday must be between 0 and 6")
    else:
        weekday = datetime.now().weekday()

    # 정류장 조회
    station = fetchone(
        "SELECT ars_no, station_name FROM stations WHERE ars_no = ?",
        (station_id,),
    )
    station_name = station["station_name"] if station else station_id

    # crowd_counts 테이블에서 해당 정류장의 최근 카운팅 값 조회
    crowd = fetchone(
        "SELECT count_board, count_in FROM crowd_counts WHERE station_id = ? ORDER BY created_at DESC LIMIT 1",
        (station_id,),
    )
    prev_boarding = crowd["count_board"] if crowd else 0
    prev_alighting = crowd["count_in"] if crowd else 0

    # weather_cache 테이블에서 최근 날씨 조회
    weather_row = fetchone(
        "SELECT weather, temperature FROM weather_cache ORDER BY fetched_at DESC LIMIT 1",
        (),
    )
    weather_val = weather_row["weather"] if weather_row else 0
    temperature_val = weather_row["temperature"] if weather_row else 20.0

    # 피처 구성: ML 6개 (2026-05-16 weekday 제거, 진단 P0).
    # weekday는 API/DB 호환성 위해 받아두지만 ML 호출에는 미포함.
    features = {
        "hour": hour,
        "weather": weather_val,
        "temperature": temperature_val,
        "prev_boarding": prev_boarding,
        "prev_alighting": prev_alighting,
        "route_count": 5,
        "weekday": weekday,  # ML 모델은 무시. 캐시 키와 DB 컬럼 호환용.
    }

    prediction = _cached_predict(features)

    # 다음 시간대 예측
    next_hour = (hour + 1) % 24
    next_features = dict(features, hour=next_hour)
    next_pred = _cached_predict(next_features)

    # 예측 결과 DB 저장
    try:
        execute(
            "INSERT INTO predictions (station_ars_no, hour, weekday, predicted_level, predicted_label, probabilities) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (station_id, hour, weekday, prediction["level"], prediction["label"],
             str(prediction["probabilities"])),
        )
    except Exception:
        pass  # DB 저장 실패해도 응답은 반환

    return jsonify({
        "status": "ok",
        "data": {
            "station_id": station_id,
            "station_name": station_name,
            "hour": hour,
            "weekday": weekday,
            "prediction": prediction,
            "recommendation": RECOMMENDATIONS.get(prediction["level"], ""),
            "next_hour_prediction": {
                "level": next_pred["level"],
                "label": next_pred["label"],
            },
        },
        "timestamp": datetime.now().isoformat(),
    })
