"""BUSTAGO Backend -- 혼잡도 도메인 통합 (/api/predict + /api/route-recommend)

2026-05-17 단순화 D: predict.py + recommend.py를 한 도메인으로 병합.
- 두 라우트가 같은 ML 호출 로직 + 캐시 + 폴백 체인 공유
- 광주대 노선 데이터는 seeds.routes_gj 단일 진실원에서 로드
- predict_bp + recommend_bp → congestion_bp 1개

폴백 체인:
  1. ML predict_congestion (sklearn rf_model.pkl)
  2. rule_based (광주대 통학 패턴, sklearn 의존 0)
  3. DUMMY_PREDICTION (항상 '보통')
"""

import json
import logging
import re
import time
from datetime import datetime

from flask import Blueprint, request, jsonify, abort

from backend.models.db import fetchone, execute
from backend.config import MODEL_PATH
from backend.extensions import limiter
from backend.seeds.routes_gj import routes_for_station

log = logging.getLogger(__name__)

congestion_bp = Blueprint("congestion", __name__)

# ---------- 캐시 ----------
_predict_cache: dict = {}
_CACHE_TTL = 300


def _cache_key(features: dict) -> tuple:
    return (features["hour"], features.get("weekday", -1), features["route_count"])


def _cached_predict(features: dict) -> dict:
    """캐시된 예측 반환. 미스 시 ML 모델 호출 후 캐시 저장 (LRU 500개 한도)."""
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


# ---------- 폴백 ----------
DUMMY_PREDICTION = {
    "level": 1,
    "label": "보통",
    "probabilities": [0.2, 0.5, 0.2, 0.1],
}

RECOMMENDATIONS = {
    0: "여유로운 시간대입니다. 편하게 이용하세요.",
    1: "보통 수준의 혼잡도입니다.",
    2: "혼잡이 예상됩니다. 다음 시간대를 추천합니다.",
    3: "매우 혼잡합니다. 가능하면 다른 시간대를 이용하세요.",
}


def _do_predict(features: dict) -> dict:
    """ML 모델 우선, 실패 시 rule_based → DUMMY (3단 폴백)."""
    try:
        from ml.models.predict import predict_congestion
        return predict_congestion(features, model_path=MODEL_PATH)
    except (FileNotFoundError, ImportError) as e:
        log.warning("ML predict 실패 → rule_based 폴백: %s", e)
        try:
            from backend.seeds.rule_based import rule_based_predict
            return rule_based_predict(
                hour=int(features.get("hour", 12)),
                weekday=int(features.get("weekday", 0)),
            )
        except Exception as e2:
            log.warning("rule_based도 실패 → DUMMY 폴백: %s", e2)
            return dict(DUMMY_PREDICTION)


# ---------- 노선 로드 (단일 진실원) ----------
def _load_routes_for(station_id: str) -> list[dict]:
    """DB 우선 → 코드 시드 폴백 (단일 진실원 = seeds/routes_gj.py)."""
    from backend.models.db import fetchall
    try:
        rows = fetchall(
            "SELECT route_no, route_name, end_stations, route_count "
            "FROM routes WHERE start_station_id = ?",
            (station_id,)
        )
    except Exception as e:
        log.warning("routes DB 조회 실패, 코드 시드 폴백: %s", e)
        rows = None

    if rows:
        return [
            {"route_no": r["route_no"], "route_name": r["route_name"],
             "end_stations": json.loads(r["end_stations"]),
             "route_count": r["route_count"]}
            for r in rows
        ]
    return routes_for_station(station_id)


# =============================================================================
# /api/predict — 정류장 1개 혼잡도 예측
# =============================================================================
@congestion_bp.route("/api/predict")
@limiter.limit("30 per minute")
def predict():
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

    station = fetchone(
        "SELECT ars_no, station_name FROM stations WHERE ars_no = ?",
        (station_id,),
    )
    station_name = station["station_name"] if station else station_id

    crowd = fetchone(
        "SELECT count_board, count_in FROM crowd_counts WHERE station_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (station_id,),
    )
    prev_boarding = crowd["count_board"] if crowd else 0
    prev_alighting = crowd["count_in"] if crowd else 0

    features = {
        "hour": hour,
        "prev_boarding": prev_boarding,
        "prev_alighting": prev_alighting,
        "route_count": 5,
        "weekday": weekday,
    }

    prediction = _cached_predict(features)

    next_hour = (hour + 1) % 24
    next_features = dict(features, hour=next_hour)
    next_pred = _cached_predict(next_features)

    try:
        execute(
            "INSERT INTO predictions (station_ars_no, hour, weekday, predicted_level, "
            "predicted_label, probabilities) VALUES (?, ?, ?, ?, ?, ?)",
            (station_id, hour, weekday, prediction["level"], prediction["label"],
             str(prediction["probabilities"])),
        )
    except Exception as e:
        log.warning(
            "predictions INSERT 실패 station_id=%s hour=%s: %s",
            station_id, hour, e,
        )

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


# =============================================================================
# /api/route-recommend — 정류장의 노선별 혼잡도 + 추천 1개
# =============================================================================
@congestion_bp.route("/api/route-recommend")
@limiter.limit("20 per minute")
def route_recommend():
    station_id = request.args.get("station_id", "")
    hour_str = request.args.get("hour", "")
    weekday_str = request.args.get("weekday", str(datetime.now().weekday()))
    dest = request.args.get("dest", "")

    if not re.match(r'^[A-Za-z0-9]{2,10}$', station_id):
        return jsonify({"status": "error", "message": "station_id required", "code": 400}), 400
    if not hour_str.isdigit() or not (0 <= int(hour_str) <= 23):
        return jsonify({"status": "error", "message": "hour 0-23 required", "code": 400}), 400
    if not weekday_str.isdigit() or not (0 <= int(weekday_str) <= 6):
        return jsonify({"status": "error", "message": "weekday 0-6", "code": 400}), 400

    hour = int(hour_str)
    weekday = int(weekday_str)

    routes = _load_routes_for(station_id)

    if not routes:
        return jsonify({
            "status": "ok",
            "data": {"station_id": station_id, "hour": hour, "weekday": weekday, "routes": []},
            "timestamp": datetime.now().isoformat()
        })

    if dest:
        routes = [r for r in routes if any(dest in s for s in r["end_stations"])]

    # 각 노선 혼잡도 예측 (predict와 같은 폴백 체인 + 캐시 공유)
    result_routes = []
    for route in routes:
        features = {
            "hour": hour,
            "prev_boarding": 0,
            "prev_alighting": 0,
            "route_count": route["route_count"],
            "weekday": weekday,
        }
        pred = _cached_predict(features)

        result_routes.append({
            "route_no": route["route_no"],
            "route_name": route["route_name"],
            "end_stations": route["end_stations"],
            "congestion": pred,
            "recommended": False,
        })

    # 혼잡도 낮은 순 정렬, 최저 1개에 recommended=True
    result_routes.sort(key=lambda r: r["congestion"]["level"])
    if result_routes:
        result_routes[0]["recommended"] = True

    return jsonify({
        "status": "ok",
        "data": {
            "station_id": station_id,
            "hour": hour,
            "weekday": weekday,
            "routes": result_routes,
        },
        "timestamp": datetime.now().isoformat(),
    })
