"""광주대 정류장 / 광주 BIS 정류소 ID 단일 정의.

기존 분산 정의:
  - backend/schema.sql:56-57 stations INSERT
  - backend/routes/stations.py:139-141 GJ_STOPS 리스트
  - backend/test_app.py:46/91/107/212 INS01/GATE01/1981 산재
  - frontend (.js)에서는 동적 fetch

2026-05-17 클린 아키텍처 정합화: 본 파일을 backend 측 단일 정의로 사용.
schema.sql은 동일 좌표로 INSERT, stations.py는 GJ_BUSSTOPS를 import.
"""

# 광주대 정류장 — 좌표는 schema.sql과 동일 (실측 2026-06-04)
STATIONS = {
    "INS01":  {"name": "광주대 인성관 (셔틀)",         "lat": 35.1058481, "lon": 126.8963590},
    "GJ3229": {"name": "광주대 금호아파트방면 (3229)", "lat": 35.1074148, "lon": 126.8972338},
    "GJ3230": {"name": "광주대 구암방면 (3230)",       "lat": 35.1071759, "lon": 126.8970661},
}

# 광주 BIS busstop_id 매핑
# 출처: captest/bus_server.py 통합 시 확인된 실제 ID (2026-05-13)
GJ_BUSSTOPS = [
    {"name": "광주대 구암방면 (3230)",       "busstop_id": 1981, "ars_no": "GJ3230"},
    {"name": "광주대 금호아파트방면 (3229)", "busstop_id": 80,   "ars_no": "GJ3229"},
    {"name": "광주대입구 (3228)",            "busstop_id": 3219, "ars_no": "GJ3228"},
]
