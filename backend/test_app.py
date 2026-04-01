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
