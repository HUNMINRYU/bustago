import pytest
import sys
import os

import responses

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app
from backend.config import GJ_BIS_BASE_URL

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """헬스 체크 엔드포인트 확인"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"

def test_predict_endpoint_missing_args(client):
    """필수 파라미터 누락 시 400 에러 확인"""
    resp = client.get("/api/predict")
    assert resp.status_code == 400
    assert "station_id is required" in resp.json["message"]

def test_predict_endpoint_success(client):
    """정상 파라미터 호출 시 더미 예측 반환 확인"""
    resp = client.get("/api/predict?station_id=100100118&hour=10")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"
    assert "prediction" in resp.json["data"]
    assert resp.json["data"]["station_id"] == "100100118"


# --- Crowd Count Tests ---

def test_crowd_count_post_success(client):
    """POST /api/crowd-count 정상 데이터 전송 시 200 확인"""
    resp = client.post("/api/crowd-count", json={
        "station_id": "INS01",
        "count_in": 5,
        "count_board": 3,
        "current_waiting": 2,
    })
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"


def test_crowd_count_post_missing_station(client):
    """POST /api/crowd-count station_id 누락 시 400 확인"""
    resp = client.post("/api/crowd-count", json={
        "count_in": 5,
        "count_board": 3,
        "current_waiting": 2,
    })
    assert resp.status_code == 400
    assert "station_id" in resp.json["message"]


def test_crowd_count_get_success(client):
    """POST 후 GET /api/crowd-count 최신 데이터 조회 확인"""
    client.post("/api/crowd-count", json={
        "station_id": "GETtest1",
        "count_in": 10,
        "count_board": 4,
        "current_waiting": 6,
    })
    resp = client.get("/api/crowd-count?station_id=GETtest1")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"
    assert resp.json["data"]["count_in"] == 10
    assert resp.json["data"]["current_waiting"] == 6


def test_crowd_count_get_no_data(client):
    """GET /api/crowd-count 데이터 없는 정류장 조회 시 404 확인"""
    resp = client.get("/api/crowd-count?station_id=UNKNOWN1")
    assert resp.status_code == 404


# --- Route Recommend Tests ---

def test_route_recommend_gj3230_morning(client):
    """GET /api/route-recommend 구암방면(GJ3230) 오전 추천 노선 확인"""
    resp = client.get("/api/route-recommend?station_id=GJ3230&hour=8")
    assert resp.status_code == 200
    routes = resp.json["data"]["routes"]
    assert isinstance(routes, list)
    assert len(routes) >= 1
    assert any(route.get("recommended") is True for route in routes)


def test_route_recommend_bad_station(client):
    """GET /api/route-recommend station_id 오류 시 400 확인"""
    resp = client.get("/api/route-recommend?station_id=&hour=8")
    assert resp.status_code == 400


def test_route_recommend_bad_hour(client):
    """GET /api/route-recommend hour 오류 시 400 확인"""
    resp = client.get("/api/route-recommend?station_id=GJ3230&hour=99")
    assert resp.status_code == 400


# --- GJ BIS / Stations Tests ---

# 진단 §6 P1 반영 (2026-05-16): 기존 "200 또는 502 OK" 테스트는 네트워크 없을 때
# 그냥 통과하여 검증력이 없었음. 아래 mock 테스트로 성공/실패 케이스를 분리해
# 결정론적으로 검증한다. 통합(실 네트워크) 테스트는 옵션 마커로 분리.


def test_stations_endpoint_returns_operational_gwangju_stations_only(client):
    """학생/대시보드 UI에는 서울 샘플·원시 BIS 정류장 대신 운영 정류장만 노출."""
    resp = client.get("/api/stations")
    assert resp.status_code == 200
    rows = resp.json["data"]
    station_ids = [row["ars_no"] for row in rows]

    assert station_ids == ["INS01", "GJ3229", "GJ3230", "DEMO01"]
    assert "22011" not in station_ids

    # 구암방면(GJ3230)은 BIS busstop 1981, 금호아파트방면(GJ3229)은 80
    gj3230 = next(row for row in rows if row["ars_no"] == "GJ3230")
    assert gj3230["gj_busstop_id"] == 1981
    gj3229 = next(row for row in rows if row["ars_no"] == "GJ3229")
    assert gj3229["gj_busstop_id"] == 80


@pytest.mark.network
def test_lines_endpoint_integration(client):
    """[integration] /api/lines 실 광주 BIS 호출 — 네트워크 환경에서만 의미.

    `pytest -m "not network"`로 mock 테스트만 돌릴 수 있다.
    """
    resp = client.get("/api/lines")
    assert resp.status_code in (200, 502)


@pytest.mark.network
def test_arrive_endpoint_integration(client):
    """[integration] /api/arrive/<busstop_id> 실 광주 BIS 호출."""
    resp = client.get("/api/arrive/1981")
    assert resp.status_code in (200, 502)


@responses.activate
def test_lines_endpoint_mocked_success(client):
    """/api/lines — mock 200 응답이 데이터로 정상 변환되는지."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/lineInfo",
        json={
            "RESPONSE": {
                "RESULT": {"CODE": "INFO-000", "MESSAGE": "OK"},
                "LINE_LIST": {
                    "ITEM": [
                        {"LINE_ID": 100, "LINE_NO": "419", "LINE_NAME": "419번"},
                        {"LINE_ID": 101, "LINE_NO": "518", "LINE_NAME": "518번"},
                    ]
                },
            }
        },
        status=200,
    )
    resp = client.get("/api/lines")
    assert resp.status_code == 200
    body = resp.json
    assert body["status"] == "ok"
    assert body["data"]["count"] == 2
    assert body["data"]["items"][0]["LINE_NO"] == "419"


@responses.activate
def test_lines_endpoint_mocked_upstream_failure(client):
    """/api/lines — upstream 500 시 502 반환 + 명시적 메시지."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/lineInfo",
        json={"error": "upstream broken"},
        status=500,
    )
    resp = client.get("/api/lines")
    assert resp.status_code == 502
    assert resp.json["status"] == "error"
    assert "광주 BIS" in resp.json["message"]


@responses.activate
def test_lines_endpoint_mocked_connection_error(client):
    """/api/lines — requests 자체 예외 발생 시 502."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/lineInfo",
        body=ConnectionError("simulated network down"),
    )
    resp = client.get("/api/lines")
    assert resp.status_code == 502


@responses.activate
def test_arrive_endpoint_mocked_success(client):
    """/api/arrive/<id> — mock 200 응답에서 ARRIVE_LIST 정상 추출."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/arriveInfo",
        json={
            "RESPONSE": {
                "RESULT": {"CODE": "INFO-000", "MESSAGE": "OK"},
                "ARRIVE_LIST": {
                    "ITEM": [
                        {"LINE_NAME": "419번", "REMAIN_MIN": 3, "REMAIN_STOP": 1, "LOW_BUS": 1},
                        {"LINE_NAME": "518번", "REMAIN_MIN": 12, "REMAIN_STOP": 5, "LOW_BUS": 0},
                    ]
                },
            }
        },
        status=200,
    )
    resp = client.get("/api/arrive/1981")
    assert resp.status_code == 200
    body = resp.json
    assert body["status"] == "ok"
    assert body["data"]["busstop_id"] == 1981
    assert len(body["data"]["items"]) == 2
    assert body["data"]["items"][0]["LOW_BUS"] == 1


@responses.activate
def test_arrive_endpoint_mocked_empty_item(client):
    """/api/arrive/<id> — 도착 예정 없을 때 빈 목록 200."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/arriveInfo",
        json={
            "RESPONSE": {
                "RESULT": {"CODE": "INFO-200", "MESSAGE": "no data"},
                "ARRIVE_LIST": {},
            }
        },
        status=200,
    )
    resp = client.get("/api/arrive/1981")
    assert resp.status_code == 200
    assert resp.json["data"]["items"] == []


@responses.activate
def test_arrive_endpoint_mocked_failure(client):
    """/api/arrive/<id> — upstream timeout/실패 시 502."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/arriveInfo",
        body=Exception("simulated timeout"),
    )
    resp = client.get("/api/arrive/1981")
    assert resp.status_code == 502


# --- Rule-based Fallback Tests (2026-05-17 Principal Engineer 진단 반영) ---


def test_rule_based_weekday_morning_peak():
    """평일 8시 (출근 피크) → 매우혼잡."""
    from backend.seeds.rule_based import rule_based_predict
    result = rule_based_predict(hour=8, weekday=2)
    assert result["level"] == 3
    assert result["label"] == "매우혼잡"
    assert result["source"] == "rule_based"
    assert abs(sum(result["probabilities"]) - 1.0) < 0.01


def test_rule_based_weekday_late_night():
    """평일 새벽 3시 → 여유."""
    from backend.seeds.rule_based import rule_based_predict
    result = rule_based_predict(hour=3, weekday=1)
    assert result["level"] == 0
    assert result["label"] == "여유"


def test_rule_based_weekend_reduces_level():
    """주말은 평일보다 1단계 낮음 (평일 8시 3 → 주말 8시 2)."""
    from backend.seeds.rule_based import rule_based_predict
    weekday = rule_based_predict(hour=8, weekday=2)
    weekend = rule_based_predict(hour=8, weekday=6)
    assert weekday["level"] == 3
    assert weekend["level"] == 2


def test_rule_based_invalid_hour_raises():
    from backend.seeds.rule_based import rule_based_predict
    with pytest.raises(ValueError):
        rule_based_predict(hour=25, weekday=0)


def test_rule_based_invalid_weekday_raises():
    from backend.seeds.rule_based import rule_based_predict
    with pytest.raises(ValueError):
        rule_based_predict(hour=10, weekday=7)


def test_arrive_endpoint_empty_key_returns_502(client, monkeypatch):
    """/api/arrive/<id> — GJ_BIS_API_KEY가 비어있으면 외부 호출 없이 502.

    config 직접 setattr이 아닌 stations 모듈 import 후 GJ_BIS_API_KEY 패치.
    _call_gj_bis가 빈 키 가드 (2026-05-16 추가)를 타는지 검증.
    """
    from backend.routes import stations
    monkeypatch.setattr(stations, "GJ_BIS_API_KEY", "")
    resp = client.get("/api/arrive/1981")
    assert resp.status_code == 502


# --- Bus Location Tests (2026-05-17: captest에서 본 시스템으로 이관) ---


@responses.activate
def test_bus_location_endpoint_mocked_success(client):
    """/api/bus_location/<line_id> — mock 200에서 차량 GPS 정상 추출."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/busLocationInfo",
        json={
            "RESPONSE": {
                "RESULT": {"CODE": "INFO-000", "MESSAGE": "OK"},
                "BUS_LIST": {
                    "ITEM": [
                        {"PLATE_NO": "광주70자1234", "GPS_LATI": 35.1377, "GPS_LONG": 126.8930},
                        {"PLATE_NO": "광주70자5678", "GPS_LATI": 35.1390, "GPS_LONG": 126.8945},
                    ]
                },
            }
        },
        status=200,
    )
    resp = client.get("/api/bus_location/100")
    assert resp.status_code == 200
    body = resp.json
    assert body["status"] == "ok"
    assert body["data"]["line_id"] == 100
    assert body["data"]["count"] == 2
    assert body["data"]["items"][0]["PLATE_NO"] == "광주70자1234"


@responses.activate
def test_bus_location_endpoint_mocked_failure(client):
    """/api/bus_location/<line_id> — upstream 실패 시 502."""
    responses.add(
        responses.GET,
        f"{GJ_BIS_BASE_URL}/busLocationInfo",
        body=Exception("simulated upstream timeout"),
    )
    resp = client.get("/api/bus_location/100")
    assert resp.status_code == 502
    assert resp.json["status"] == "error"


def test_gj_stops_returns_static_list(client):
    """GET /api/gj-stops 정적 광주대 정류소 목록 확인"""
    resp = client.get("/api/gj-stops")
    assert resp.status_code == 200
    assert isinstance(resp.json["data"], list)
    assert len(resp.json["data"]) == 3


def test_stations_response_has_gj_busstop_id_field(client):
    """GET /api/stations 응답 항목에 gj_busstop_id 필드 포함 확인"""
    resp = client.get("/api/stations")
    assert resp.status_code == 200
    assert all("gj_busstop_id" in station for station in resp.json["data"])


# ---------------------------------------------------------------------------
# Demo 엔드포인트 — POST /api/crowd-count/event
# ---------------------------------------------------------------------------

def test_event_in_from_empty(client):
    """빈 상태에서 IN +1 → count_in=1, current_waiting=1."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    resp = client.post("/api/crowd-count/event", json={
        "station_id": "DEMO01", "event_type": "in"
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["count_in"] == 1
    assert body["count_board"] == 0
    assert body["current_waiting"] == 1


def test_event_board_after_in(client):
    """IN +1 후 BOARD +1 → count_in=1, count_board=1, current_waiting=0."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "in"})
    resp = client.post("/api/crowd-count/event", json={
        "station_id": "DEMO01", "event_type": "board"
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count_in"] == 1
    assert body["count_board"] == 1
    assert body["current_waiting"] == 0


def test_event_board_from_empty_rejected(client):
    """빈 상태에서 BOARD → 400."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    resp = client.post("/api/crowd-count/event", json={
        "station_id": "DEMO01", "event_type": "board"
    })
    assert resp.status_code == 400


def test_event_invalid_type_rejected(client):
    """event_type 화이트리스트 위반 → 400."""
    resp = client.post("/api/crowd-count/event", json={
        "station_id": "DEMO01", "event_type": "invalid"
    })
    assert resp.status_code == 400


def test_event_rejects_non_demo_station(client):
    """INS01 등 다른 station_id 거부 → 400."""
    resp = client.post("/api/crowd-count/event", json={
        "station_id": "INS01", "event_type": "in"
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Demo 엔드포인트 — POST /api/crowd-count/reset
# ---------------------------------------------------------------------------

def test_reset_clears_demo_rows(client):
    """이벤트 2건 주입 후 reset → row 0건."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "in"})
    client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "board"})

    resp = client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["deleted_rows"] >= 2

    # 후속 GET → 404
    get_resp = client.get("/api/crowd-count?station_id=DEMO01")
    assert get_resp.status_code == 404


def test_reset_rejects_non_demo_station(client):
    """INS01 reset 호출 → 400 (실제 데이터 보호)."""
    resp = client.post("/api/crowd-count/reset", json={"station_id": "INS01"})
    assert resp.status_code == 400


def test_reset_on_empty_returns_zero(client):
    """이미 빈 DEMO01에 reset → deleted_rows=0, status ok."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    resp = client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["deleted_rows"] == 0


# ---------------------------------------------------------------------------
# Demo 엔드포인트 — GET /api/crowd-count/recent
# ---------------------------------------------------------------------------

def test_recent_returns_empty_when_no_events(client):
    """이벤트 없는 상태 → events 빈 배열."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    resp = client.get("/api/crowd-count/recent?station_id=DEMO01&limit=5")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["events"] == []


def test_recent_returns_in_then_board(client):
    """IN, BOARD 순서로 주입 → 최신순으로 board, in 반환."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "in"})
    client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "board"})

    resp = client.get("/api/crowd-count/recent?station_id=DEMO01&limit=5")
    body = resp.get_json()
    assert len(body["events"]) == 2
    assert body["events"][0]["event_type"] == "board"
    assert body["events"][0]["current_waiting"] == 0
    assert body["events"][1]["event_type"] == "in"
    assert body["events"][1]["current_waiting"] == 1


def test_recent_respects_limit(client):
    """이벤트 7건 주입 후 limit=3 → 3건만 반환."""
    from backend.models.db import execute as db_execute
    db_execute("DELETE FROM crowd_counts WHERE station_id = 'DEMO01'")
    for _ in range(7):
        client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "in"})

    resp = client.get("/api/crowd-count/recent?station_id=DEMO01&limit=3")
    body = resp.get_json()
    assert len(body["events"]) == 3


def test_recent_rejects_non_demo_station(client):
    """INS01 호출 → 400."""
    resp = client.get("/api/crowd-count/recent?station_id=INS01&limit=5")
    assert resp.status_code == 400
