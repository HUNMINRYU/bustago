"""
BUSTAGO Backend -- /api/stations, /api/weather/current 엔드포인트
"""

import json
from datetime import datetime
from flask import Blueprint, jsonify

from backend.models.db import fetchall, fetchone, execute
from backend.config import WEATHER_API_KEY, WEATHER_API_URL
from backend.extensions import limiter

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
@limiter.limit("60 per minute")
def list_stations():
    rows = fetchall("SELECT ars_no, station_name, latitude, longitude FROM stations ORDER BY station_name")
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
