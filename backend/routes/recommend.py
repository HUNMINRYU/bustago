"""
BUSTAGO Backend -- /api/route-recommend endpoint
"""

import json
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from backend.extensions import limiter

recommend_bp = Blueprint("recommend", __name__)

# 광주 BIS API 키 없을 때 폴백 고정 노선 데이터
STATIC_ROUTES = {
    "GATE01": [
        {"route_no": "419", "route_name": "419번 (광주역행)",
         "end_stations": ["광주역", "충장로", "금남로"], "route_count": 8},
        {"route_no": "518", "route_name": "518번 (금남로행)",
         "end_stations": ["금남로", "충장로", "광주대입구"], "route_count": 7},
    ],
    "INS01": [
        {"route_no": "SHUTTLE1", "route_name": "셔틀 1호차",
         "end_stations": ["정문"], "route_count": 2},
        {"route_no": "SHUTTLE2", "route_name": "셔틀 2호차",
         "end_stations": ["정문"], "route_count": 2},
        {"route_no": "SHUTTLE5", "route_name": "셔틀 5호차",
         "end_stations": ["정문"], "route_count": 2},
        {"route_no": "SHUTTLE6", "route_name": "셔틀 6호차",
         "end_stations": ["정문"], "route_count": 2},
    ],
}


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

    # 노선 목록: 고정 데이터 우선, 없으면 DB
    routes = STATIC_ROUTES.get(station_id.upper())
    if not routes:
        from backend.models.db import fetchall
        rows = fetchall(
            "SELECT route_no, route_name, end_stations, route_count FROM routes WHERE start_station_id = ?",
            (station_id,)
        )
        routes = [
            {"route_no": r[0], "route_name": r[1],
             "end_stations": json.loads(r[2]), "route_count": r[3]}
            for r in (rows or [])
        ]

    if not routes:
        return jsonify({
            "status": "ok",
            "data": {"station_id": station_id, "hour": hour, "weekday": weekday, "routes": []},
            "timestamp": datetime.now().isoformat()
        })

    # 목적지 필터 (선택)
    if dest:
        routes = [r for r in routes if any(dest in s for s in r["end_stations"])]

    # 기상 정보 (실패 시 기본값)
    weather_feat = {"weather": 0, "temperature": 20.0}
    try:
        from backend.models.db import fetchone
        row = fetchone(
            "SELECT weather, temperature FROM weather_cache ORDER BY id DESC LIMIT 1", ()
        )
        if row:
            weather_feat = {"weather": row[0] or 0, "temperature": float(row[1] or 20.0)}
    except Exception:
        pass

    # 각 노선 혼잡도 예측 (ML 모델 사용, 실패 시 시간 기반 fallback)
    result_routes = []
    for route in routes:
        features = {
            "hour": hour,
            "weekday": weekday,
            "weather": weather_feat["weather"],
            "temperature": weather_feat["temperature"],
            "prev_boarding": 0,
            "prev_alighting": 0,
            "route_count": route["route_count"],
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
