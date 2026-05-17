"""광주대 노선 단일 진실원 (Single Source of Truth).

기존 분산 정의 (3곳):
  - backend/routes/recommend.py:19-36 STATIC_ROUTES
  - backend/schema.sql:76-85 routes INSERT
  - 기능 추가 시마다 두 곳을 동시 수정해야 했던 결합

2026-05-17 클린 아키텍처 정합화: 본 파일을 단일 정의로 삼고,
  - DB 시드(schema.sql)는 동일 데이터 INSERT
  - recommend.py는 DB 조회 우선 → 빈 결과 시 본 파일 폴백

데이터 자체는 변경하지 않음 (schema.sql의 8건 그대로).
"""

GJ_ROUTES = [
    # GATE01 (광주대 정문 — 시내버스 + 인성관 셔틀)
    {"route_no": "419", "route_name": "419번 (광주역행)",
     "start_station_id": "GATE01",
     "end_stations": ["광주역", "충장로", "금남로"],
     "route_count": 8, "is_shuttle": 0},
    {"route_no": "518", "route_name": "518번 (금남로행)",
     "start_station_id": "GATE01",
     "end_stations": ["금남로", "충장로", "광주대입구"],
     "route_count": 7, "is_shuttle": 0},
    {"route_no": "SHUTTLE3", "route_name": "셔틀 3호차",
     "start_station_id": "GATE01",
     "end_stations": ["인성관"],
     "route_count": 2, "is_shuttle": 1},
    {"route_no": "SHUTTLE4", "route_name": "셔틀 4호차",
     "start_station_id": "GATE01",
     "end_stations": ["인성관"],
     "route_count": 2, "is_shuttle": 1},
    # INS01 (광주대 인성관 — 셔틀 4대)
    {"route_no": "SHUTTLE1", "route_name": "셔틀 1호차",
     "start_station_id": "INS01",
     "end_stations": ["정문"], "route_count": 2, "is_shuttle": 1},
    {"route_no": "SHUTTLE2", "route_name": "셔틀 2호차",
     "start_station_id": "INS01",
     "end_stations": ["정문"], "route_count": 2, "is_shuttle": 1},
    {"route_no": "SHUTTLE5", "route_name": "셔틀 5호차",
     "start_station_id": "INS01",
     "end_stations": ["정문"], "route_count": 2, "is_shuttle": 1},
    {"route_no": "SHUTTLE6", "route_name": "셔틀 6호차",
     "start_station_id": "INS01",
     "end_stations": ["정문"], "route_count": 2, "is_shuttle": 1},
]


def routes_for_station(station_id: str) -> list[dict]:
    """station_id에 해당하는 노선 목록을 ML 입력 형식으로 반환."""
    sid = station_id.upper()
    return [
        {
            "route_no": r["route_no"],
            "route_name": r["route_name"],
            "end_stations": r["end_stations"],
            "route_count": r["route_count"],
        }
        for r in GJ_ROUTES
        if r["start_station_id"] == sid
    ]
