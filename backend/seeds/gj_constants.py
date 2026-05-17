"""광주대 정류장 / 광주 BIS 정류소 ID 단일 정의.

기존 분산 정의:
  - backend/schema.sql:56-57 stations INSERT
  - backend/routes/stations.py:139-141 GJ_STOPS 리스트
  - backend/test_app.py:46/91/107/212 INS01/GATE01/1981 산재
  - frontend (.js)에서는 동적 fetch

2026-05-17 클린 아키텍처 정합화: 본 파일을 backend 측 단일 정의로 사용.
schema.sql은 동일 좌표로 INSERT, stations.py는 GJ_BUSSTOPS를 import.
"""

# 광주대 정류장 — 좌표는 schema.sql과 동일 (검증 완료)
STATIONS = {
    "INS01":  {"name": "광주대 인성관 (셔틀)",    "lat": 35.1377000, "lon": 126.8930000},
    "GATE01": {"name": "광주대 정문 (시내버스)",  "lat": 35.1380000, "lon": 126.8955000},
}

# 광주 BIS busstop_id 매핑
# 출처: captest/bus_server.py 통합 시 확인된 실제 ID (2026-05-13)
GJ_BUSSTOPS = [
    {"name": "광주대 (3230)",      "busstop_id": 1981, "ars_no": "GATE01"},
    {"name": "광주대 (3229)",      "busstop_id": 80,   "ars_no": "GATE01"},
    {"name": "광주대입구 (3228)",  "busstop_id": 3219, "ars_no": "GATE01"},
]
