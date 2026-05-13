import pytest
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app

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

def test_route_recommend_gate01_morning(client):
    """GET /api/route-recommend 정문 오전 추천 노선 확인"""
    resp = client.get("/api/route-recommend?station_id=GATE01&hour=8")
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
    resp = client.get("/api/route-recommend?station_id=GATE01&hour=99")
    assert resp.status_code == 400


# --- GJ BIS / Stations Tests ---

def test_lines_endpoint_returns_ok_or_502(client):
    """GET /api/lines 광주 BIS 호출 성공 또는 실패 응답 확인"""
    resp = client.get("/api/lines")
    assert resp.status_code in (200, 502)


def test_arrive_endpoint_returns_ok_or_502(client):
    """GET /api/arrive/<busstop_id> 광주 BIS 호출 성공 또는 실패 응답 확인"""
    resp = client.get("/api/arrive/1981")
    assert resp.status_code in (200, 502)


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
