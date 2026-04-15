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
