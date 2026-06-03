"""정류소 → 경유 노선 역산 시드.

광주 BIS에는 "정류소→노선" 엔드포인트가 없어, 전체 lineInfo(120개)의
lineStationInfo(경유정류소)를 돌려 대상 정류소를 지나는 노선을 추출한다.
결과는 station_routes_cache.json으로 커밋 — 런타임은 이 캐시 + arriveInfo만 사용.

실행: source .venv/bin/activate && python -m backend.seeds.derive_station_routes
"""
import json
import os

from backend.routes.stations import _call_gj_bis, _gj_bis_items
from backend.seeds.gj_constants import STATION_BOARD_TARGETS, kind_label

OUT_PATH = os.path.join(os.path.dirname(__file__), "station_routes_cache.json")


def derive() -> dict:
    data = _call_gj_bis("lineInfo")
    lines = _gj_bis_items(data, "LINE_LIST") if data else []
    cache = {
        str(bs): {"dir_label": label, "routes": []}
        for bs, label in STATION_BOARD_TARGETS.items()
    }
    for it in lines:
        try:
            line_id = int(it.get("LINE_ID"))
        except (TypeError, ValueError):
            continue
        ls = _call_gj_bis("lineStationInfo", {"LINE_ID": line_id})
        stops = _gj_bis_items(ls, "BUSSTOP_LIST") if ls else []
        stop_ids = set()
        for s in stops:
            try:
                stop_ids.add(int(s.get("BUSSTOP_ID")))
            except (TypeError, ValueError):
                pass
        for bs in STATION_BOARD_TARGETS:
            if bs in stop_ids:
                cache[str(bs)]["routes"].append({
                    "line_id": line_id,
                    "line_name": it.get("LINE_NAME", ""),
                    "line_kind": it.get("LINE_KIND"),
                })
    # 종류(급행1<간선2<지선3<농어촌4) → 이름 순 정렬로 표시 일관성
    for bs in cache:
        cache[bs]["routes"].sort(key=lambda r: (int(r["line_kind"] or 9), r["line_name"]))
    return cache


if __name__ == "__main__":
    cache = derive()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    for bs, v in cache.items():
        names = [f"{r['line_name']}({kind_label(r['line_kind'])})" for r in v["routes"]]
        print(f"busstop {bs} ({v['dir_label']}): {len(names)}개 → {', '.join(names)}")
