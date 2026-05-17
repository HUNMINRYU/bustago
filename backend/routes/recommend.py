"""
BUSTAGO Backend -- /api/route-recommend endpoint
"""

import json
import logging
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.extensions import limiter

log = logging.getLogger(__name__)

recommend_bp = Blueprint("recommend", __name__)

# 광주대 노선 데이터 단일 진실원
# (2026-05-17 클린 아키텍처: STATIC_ROUTES 분산 제거 → backend.seeds.routes_gj)
from backend.seeds.routes_gj import routes_for_station


def _load_routes_for(station_id: str) -> list[dict]:
    """DB 우선, 빈 결과 시 코드 시드 폴백 (단일 진실원 = seeds/routes_gj.py).

    DB 시드가 정상 적용된 환경은 DB 결과 반환 (운영 환경).
    schema.sql 미적용 / 신규 환경 / CI 등에서는 코드 폴백 (시연 안정성).
    """
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


@recommend_bp.route("/api/route-recommend")
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

    # 노선 목록: DB 우선 → 코드 시드 폴백 (단일 진실원 정합화, 2026-05-17)
    routes = _load_routes_for(station_id)

    if not routes:
        return jsonify({
            "status": "ok",
            "data": {"station_id": station_id, "hour": hour, "weekday": weekday, "routes": []},
            "timestamp": datetime.now().isoformat()
        })

    # 목적지 필터 (선택)
    if dest:
        routes = [r for r in routes if any(dest in s for s in r["end_stations"])]

    # 각 노선 혼잡도 예측 (ML 모델, 실패 시 rule_based 폴백)
    # 2026-05-17 단순화 C: weather_cache 조회 제거 (RF feature에서 weather 빠짐)
    result_routes = []
    for route in routes:
        features = {
            "hour": hour,
            "prev_boarding": 0,
            "prev_alighting": 0,
            "route_count": route["route_count"],
            "weekday": weekday,  # rule_based 폴백 입력 + 응답 echo용
        }
        try:
            from ml.models.predict import predict_congestion
            pred = predict_congestion(features)
        except Exception:
            # 피크타임 기반 fallback
            level = 2 if hour in (8, 9, 17, 18) else 1
            pred = {"level": level, "label": ["여유", "보통", "혼잡", "매우혼잡"][level],
                    "probabilities": [0.1, 0.3, 0.4, 0.2] if level == 2 else [0.2, 0.5, 0.2, 0.1]}

        result_routes.append({
            "route_no": route["route_no"],
            "route_name": route["route_name"],
            "end_stations": route["end_stations"],
            "congestion": pred,
            "recommended": False,
        })

    # 혼잡도 낮은 순 정렬, 최저 노선에 recommended=True
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
