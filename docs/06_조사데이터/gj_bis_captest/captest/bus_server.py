# 실행: python bus_server.py
# 접속: http://localhost:5000

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder=".")
CORS(app)

# API키
SERVICE_KEY = "bN25YqJDY0QChe%2BqqNsdxd%2FYQy3krb4JYe0Vc06Fi4%2FtV%2BH0ECGdD1h%2FNuQF5CdNH0bIxWkfniL4%2FM6ce13GIQ%3D%3D"

BASE_URL = "https://apis.data.go.kr/6290000/gj_bis"

# 광주대 정류소
TARGET_STOPS = [
    {"name": "광주대 (3230)",      "busstop_id": 1981},
    {"name": "광주대 (3229)",      "busstop_id": 80},
    {"name": "광주대입구 (3228)",  "busstop_id": 3219},
]


def call_api(endpoint: str, params: dict = {}) -> dict | None:
    full_url = f"{BASE_URL}/{endpoint}?serviceKey={SERVICE_KEY}"
    try:
        res = requests.get(full_url, params=params, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"[API 오류] {endpoint}: {e}")
    return None


def get_items(data: dict, list_key: str) -> list:
    try:
        item = data["RESPONSE"][list_key]["ITEM"]
        return item if isinstance(item, list) else [item]
    except (KeyError, TypeError):
        return []

# API 라우트
@app.route("/api/arrive/<int:busstop_id>")
def arrive(busstop_id):
    """도착 정보"""
    data = call_api("arriveInfo", {"BUSSTOP_ID": busstop_id})
    if not data:
        return jsonify({"error": "API 호출 실패"}), 500
    items = get_items(data, "ARRIVE_LIST")
    return jsonify({"items": items, "busstop_id": busstop_id})


@app.route("/api/stops")
def stops():
    """광주대 정류소 목록"""
    return jsonify({"stops": TARGET_STOPS})


@app.route("/api/lines")
def lines():
    """전체 노선 목록"""
    data = call_api("lineInfo")
    if not data:
        return jsonify({"error": "API 호출 실패"}), 500
    items = get_items(data, "LINE_LIST")
    return jsonify({"items": items})


@app.route("/api/bus_location/<int:line_id>")
def bus_location(line_id):
    """실시간 버스 위치"""
    data = call_api("busLocationInfo", {"LINE_ID": line_id})
    if not data:
        return jsonify({"error": "API 호출 실패"}), 500
    resp = data.get("RESPONSE", {})
    list_key = next((k for k in resp if k != "RESULT"), None)
    items = get_items(data, list_key) if list_key else []
    return jsonify({"items": items})


@app.route("/")
def index():
    return send_from_directory(".", "dashboard.html")


if __name__ == "__main__":
    print("=" * 50)
    print("  광주버스 실시간 대시보드 서버 시작")
    print("  접속 주소: http://localhost:5000")
    print("=" * 50)
    if "여기에" in SERVICE_KEY:
        print("⚠️  SERVICE_KEY를 먼저 입력하세요!")
    app.run(debug=True, port=5000)