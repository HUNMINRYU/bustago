"""
BUSTAGO Backend -- /api/stations, /api/weather/current, /api/arrive, /api/lines 엔드포인트
"""

import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from backend.models.db import fetchall, fetchone, execute
from backend.config import WEATHER_API_KEY, WEATHER_API_URL, GJ_BIS_API_KEY, GJ_BIS_BASE_URL
from backend.extensions import limiter

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
@limiter.limit("60 per minute")
def list_stations():
    rows = fetchall(
        "SELECT ars_no, station_name, latitude, longitude, gj_busstop_id "
        "FROM stations ORDER BY station_name"
    )
    return jsonify({
        "status": "ok",
        "data": rows,
        "timestamp": datetime.now().isoformat(),
    })


@stations_bp.route("/api/weather/current")
@limiter.limit("30 per minute")
def weather_current():
    now = datetime.now()
    hour = now.hour

    # 캐시 확인 (1시간 이내)
    cached = fetchone(
        "SELECT weather, temperature, rain, humidity, wind_speed, fetched_at "
        "FROM weather_cache WHERE location = ? AND hour = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        ("seoul", hour),
    )

    if cached:
        return jsonify({
            "status": "ok",
            "data": {
                "weather": cached["weather"],
                "temperature": cached["temperature"],
                "rain": cached["rain"],
                "humidity": cached["humidity"],
                "wind_speed": cached["wind_speed"],
                "cached": True,
            },
            "timestamp": now.isoformat(),
        })

    # 기상청 API 호출 시도
    if WEATHER_API_KEY:
        try:
            import requests
            resp = requests.get(WEATHER_API_URL, params={
                "serviceKey": WEATHER_API_KEY,
                "numOfRows": 10,
                "pageNo": 1,
                "dataType": "JSON",
                "base_date": now.strftime("%Y%m%d"),
                "base_time": now.strftime("%H00"),
                "nx": 60, "ny": 127,  # 서울 좌표
            }, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
                weather_data = _parse_kma_items(items)
                # 캐시 저장
                execute(
                    "INSERT INTO weather_cache (location, hour, weather, temperature, rain, humidity, wind_speed) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("seoul", hour, weather_data["weather"], weather_data["temperature"],
                     weather_data["rain"], weather_data["humidity"], weather_data["wind_speed"]),
                )
                return jsonify({
                    "status": "ok",
                    "data": {**weather_data, "cached": False},
                    "timestamp": now.isoformat(),
                })
        except Exception:
            pass

    # API 키 없거나 호출 실패 시 기본값
    default_weather = {
        "weather": 0,
        "temperature": 20.0,
        "rain": 0,
        "humidity": 50,
        "wind_speed": 2.0,
        "cached": False,
        "fallback": True,
    }
    return jsonify({
        "status": "ok",
        "data": default_weather,
        "timestamp": now.isoformat(),
    })


def _call_gj_bis(endpoint: str, params: dict = None) -> dict | None:
    """광주광역시 버스정보시스템 API 호출 헬퍼."""
    if not GJ_BIS_API_KEY:
        # 키 누락 — config.py에서 시작 시 경고함. 여기서는 조용히 None 반환 (502 폴백 트리거).
        return None
    try:
        import requests
        url = f"{GJ_BIS_BASE_URL}/{endpoint}?serviceKey={GJ_BIS_API_KEY}"
        res = requests.get(url, params=params or {}, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"[GJ BIS 오류] {endpoint}: {e}")
    return None


def _gj_bis_items(data: dict, list_key: str) -> list:
    """광주 BIS 응답에서 아이템 목록 추출."""
    try:
        item = data["RESPONSE"][list_key]["ITEM"]
        return item if isinstance(item, list) else [item]
    except (KeyError, TypeError):
        return []


# 광주대 버스정류소 — captest/bus_server.py에서 확인된 실제 busstop_id
GJ_STOPS = [
    {"name": "광주대 (3230)", "busstop_id": 1981, "ars_no": "GATE01"},
    {"name": "광주대 (3229)", "busstop_id": 80,   "ars_no": "GATE01"},
    {"name": "광주대입구 (3228)", "busstop_id": 3219, "ars_no": "GATE01"},
]


@stations_bp.route("/api/arrive/<int:busstop_id>")
@limiter.limit("30 per minute")
def arrive(busstop_id: int):
    """광주 BIS 실시간 버스 도착 정보."""
    data = _call_gj_bis("arriveInfo", {"BUSSTOP_ID": busstop_id})
    if not data:
        return jsonify({"status": "error", "message": "광주 BIS API 호출 실패", "code": 502}), 502
    items = _gj_bis_items(data, "ARRIVE_LIST")
    return jsonify({
        "status": "ok",
        "data": {"busstop_id": busstop_id, "items": items},
        "timestamp": datetime.now().isoformat(),
    })


@stations_bp.route("/api/lines")
@limiter.limit("10 per minute")
def lines():
    """광주 BIS 전체 노선 목록."""
    data = _call_gj_bis("lineInfo")
    if not data:
        return jsonify({"status": "error", "message": "광주 BIS API 호출 실패", "code": 502}), 502
    resp = data.get("RESPONSE", {})
    list_key = next((k for k in resp if k != "RESULT"), None)
    items = _gj_bis_items(data, list_key) if list_key else []
    return jsonify({
        "status": "ok",
        "data": {"items": items, "count": len(items)},
        "timestamp": datetime.now().isoformat(),
    })


@stations_bp.route("/api/gj-stops")
@limiter.limit("60 per minute")
def gj_stops():
    """광주대 버스정류소 목록 (busstop_id 포함)."""
    return jsonify({
        "status": "ok",
        "data": GJ_STOPS,
        "timestamp": datetime.now().isoformat(),
    })


def _get_current_weather() -> dict | None:
    """현재 날씨 데이터 조회 (recommend.py 등에서 재사용)."""
    try:
        now = datetime.now()
        cached = fetchone(
            "SELECT weather, temperature FROM weather_cache WHERE location = ? AND hour = ? "
            "ORDER BY fetched_at DESC LIMIT 1",
            ("seoul", now.hour),
        )
        if cached:
            return {"weather": cached["weather"], "temperature": cached["temperature"]}
    except Exception:
        pass
    return None


def _parse_kma_items(items):
    """기상청 API 초단기실황 아이템 파싱."""
    data = {"weather": 0, "temperature": 20.0, "rain": 0, "humidity": 50, "wind_speed": 2.0}
    sky_val = 1  # 기본값 맑음
    
    for item in items:
        cat = item.get("category")
        val = item.get("obsrValue", "0")
        if cat == "T1H":
            data["temperature"] = float(val)
        elif cat == "RN1":
            rain_val = float(val)
            data["rain"] = 1 if rain_val > 0 else 0
        elif cat == "REH":
            data["humidity"] = int(float(val))
        elif cat == "WSD":
            data["wind_speed"] = float(val)
        elif cat == "SKY":
             sky_val = int(float(val))
             # PTY 값이 아직 안 들어왔거나 0일 경우 sky 우선 적용
             if data["weather"] == 0 and sky_val in (3, 4):
                 data["weather"] = 1
        elif cat == "PTY":
            pty = int(float(val))
            # 0=없음, 1=비, 2=비/눈, 3=눈, 5=빗방울, 6=빗방울눈날림, 7=눈날림
            if pty == 0:
                # 비/눈이 없으면 sky_val에 따라 0(맑음) 또는 1(흐림) 설정
                data["weather"] = 1 if sky_val in (3, 4) else 0
            elif pty in (1, 2, 5, 6):
                data["weather"] = 2
                data["rain"] = 1
            elif pty in (3, 7):
                data["weather"] = 3
                data["rain"] = 1
    return data
