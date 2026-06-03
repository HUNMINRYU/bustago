"""
BUSTAGO Backend -- /api/stations, /api/arrive, /api/lines, /api/bus_location, /api/gj-stops 엔드포인트
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request

from backend.models.db import fetchall
from backend.config import GJ_BIS_API_KEY, GJ_BIS_BASE_URL
from backend.extensions import limiter

log = logging.getLogger(__name__)

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
@limiter.limit("60 per minute")
def list_stations():
    rows = fetchall(
        "SELECT ars_no, station_name, latitude, longitude, gj_busstop_id "
        "FROM stations WHERE ars_no IN ('INS01', 'GJ3229', 'GJ3230', 'DEMO01') "
        "ORDER BY CASE ars_no "
        "WHEN 'INS01' THEN 0 WHEN 'GJ3229' THEN 1 WHEN 'GJ3230' THEN 2 "
        "WHEN 'DEMO01' THEN 3 ELSE 9 END, "
        "station_name"
    )
    return jsonify({
        "status": "ok",
        "data": rows,
        "timestamp": datetime.now().isoformat(),
    })


# 2026-05-17 단순화 C: /api/weather/current 엔드포인트 제거.
# RF feature에서 weather/temperature 빠졌고 frontend에서도 호출 0건이라 정리.
# WEATHER_API_KEY config는 외부 의존 옵션으로 config.py에 보존 (.env 갱신 영향 최소화).


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
        # print → log.warning으로 교체 (silent 아니지만 logger 일관성).
        log.warning("GJ BIS API 호출 실패 endpoint=%s: %s", endpoint, e)
    return None


def _gj_bis_items(data: dict, list_key: str) -> list:
    """광주 BIS 응답에서 아이템 목록 추출."""
    try:
        item = data["RESPONSE"][list_key]["ITEM"]
        return item if isinstance(item, list) else [item]
    except (KeyError, TypeError):
        return []


# 광주대 버스정류소 — 단일 진실원 (2026-05-17 클린 아키텍처 정합화)
from backend.seeds.gj_constants import GJ_BUSSTOPS as GJ_STOPS


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


@stations_bp.route("/api/bus_location/<int:line_id>")
@limiter.limit("30 per minute")
def bus_location(line_id: int):
    """광주 BIS 실시간 버스 위치 (노선별 GPS 좌표).

    2026-05-17: captest/bus_server.py에서 본 시스템으로 이관.
    응답: items에 각 차량의 좌표·차량번호·진행 방향 등이 들어있음
          (필드명은 광주 BIS 명세를 그대로 따름).
    """
    data = _call_gj_bis("busLocationInfo", {"LINE_ID": line_id})
    if not data:
        return jsonify({"status": "error", "message": "광주 BIS API 호출 실패", "code": 502}), 502
    resp = data.get("RESPONSE", {})
    list_key = next((k for k in resp if k != "RESULT"), None)
    items = _gj_bis_items(data, list_key) if list_key else []
    return jsonify({
        "status": "ok",
        "data": {"line_id": line_id, "items": items, "count": len(items)},
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


# 2026-05-17 단순화 C: _get_current_weather / _parse_kma_items 제거.
# weather_cache 테이블·KMA API 파서·재사용 헬퍼 모두 정리. RF feature 4개 (hour, prev_*, route_count) 운영.
