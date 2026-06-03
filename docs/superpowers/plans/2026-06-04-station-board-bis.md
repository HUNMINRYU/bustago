# 학생앱 Kakao형 정류장 보드 + 노선 상세 + 현재 버스위치 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (인라인 실행, 코덱스/서브에이전트 미사용). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학생앱에 광주 BIS 기반 Kakao형 정류장 보드(P1)·노선 경유정류소 상세(P2)·현재 버스위치(P3)를 추가한다.

**Architecture:** 정류소→노선은 BIS에 없으므로 `lineStationInfo` 120개를 역산해 `station_routes_cache.json`으로 시드(빌드타임 1회). 백엔드 신규 엔드포인트 2종(`/api/station-board`, `/api/line-stations`) + 기존 `/api/bus_location` 재사용. 프론트는 `data.js`(어댑터)만 BIS를 알고 `app.js`(뷰)는 어댑터만 호출.

**Tech Stack:** Flask + SQLite, 바닐라 JS(ES5 스타일, 기존 코드 일치), `responses`(백엔드 mock 테스트), `node:test`(JS 순수 매퍼 테스트).

**참조 spec:** `docs/superpowers/specs/2026-06-04-station-board-bis-design.md`

**공통 사실 (실측 2026-06-04):**
- `LINE_KIND` → 라벨: `{1:"급행", 2:"간선", 3:"지선", 4:"농어촌"}`. 색: 급행 `#ef4444`, 간선 `#3b82f6`, 지선 `#22c55e`, 농어촌 `#f97316`.
- 대상 BIS 정류소: `80`(GJ3229, 금호아파트방면, dir_label "금호타운아파트 방향"), `1981`(GJ3230, 구암방면, dir_label "구암 방향").
- `lineStationInfo(LINE_ID)` → `BUSSTOP_LIST` item: `{BUSSTOP_NUM, LINE_ID, LINE_NAME, BUSSTOP_ID, BUSSTOP_NAME, ARS_ID, LONGITUDE, LATITUDE, RETURN_FLAG, SEQ}`.
- `lineInfo` → `LINE_LIST` item: `{LINE_NUM, LINE_ID, LINE_NAME, DIR_UP_NAME, DIR_DOWN_NAME, FIRST_RUN_TIME, LAST_RUN_TIME, RUN_INTERVAL, LINE_KIND}`.
- `arriveInfo(BUSSTOP_ID)` → `ARRIVE_LIST` item: `{LINE_ID, SHORT_LINE_NAME, LINE_NAME, REMAIN_MIN, REMAIN_STOP, LOW_BUS, ARRIVE_FLAG, DIR_END}`.
- `busLocationInfo(LINE_ID)` → `BUSLOCATION_LIST`: **필드 미확정(운행 0대 시간대)**. P3에서 방어적으로 다룸.

**실행 환경 메모:** 테스트는 `source .venv/bin/activate` 후 실행. 백엔드 BIS 키는 `.env`의 `GJ_BIS_API_KEY`(존재 확인됨).

---

## Task 1: LINE_KIND 라벨 상수 + lineInfo 메타 캐시 헬퍼 (백엔드)

**Files:**
- Modify: `backend/seeds/gj_constants.py` (상수 추가)
- Modify: `backend/routes/stations.py` (lineInfo 메모리 캐시 헬퍼 추가)
- Test: `backend/test_app.py`

- [ ] **Step 1: gj_constants.py에 KIND 라벨 + 대상 정류소 상수 추가**

`backend/seeds/gj_constants.py` 끝에 추가:
```python
# 광주 BIS LINE_KIND 코드 → 한글 라벨 (실측 2026-06-04: 1급행/2간선/3지선/4농어촌)
LINE_KIND_LABELS = {1: "급행", 2: "간선", 3: "지선", 4: "농어촌"}


def kind_label(line_kind) -> str:
    try:
        return LINE_KIND_LABELS.get(int(line_kind), "버스")
    except (TypeError, ValueError):
        return "버스"


# 정류장 보드 대상 BIS 정류소 (busstop_id → 방면 라벨)
STATION_BOARD_TARGETS = {80: "금호타운아파트 방향", 1981: "구암 방향"}
```

- [ ] **Step 2: stations.py에 lineInfo 메타 캐시 헬퍼 작성**

`backend/routes/stations.py`의 `from backend.seeds.gj_constants import GJ_BUSSTOPS as GJ_STOPS` 줄 아래에 추가:
```python
from backend.seeds.gj_constants import kind_label

# lineInfo는 120개 고정 — 프로세스 1회 로드 후 메모리 캐시 (line_id → 메타 dict)
_LINE_META_CACHE = None


def _line_meta_map() -> dict:
    """line_id(int) → {line_name, line_kind, kind_label, dir_up, dir_down, first_run, last_run, interval}."""
    global _LINE_META_CACHE
    if _LINE_META_CACHE is not None:
        return _LINE_META_CACHE
    data = _call_gj_bis("lineInfo")
    out = {}
    if data:
        for it in _gj_bis_items(data, "LINE_LIST"):
            try:
                lid = int(it.get("LINE_ID"))
            except (TypeError, ValueError):
                continue
            kind = it.get("LINE_KIND")
            out[lid] = {
                "line_name": it.get("LINE_NAME", ""),
                "line_kind": kind,
                "kind_label": kind_label(kind),
                "dir_up": it.get("DIR_UP_NAME", ""),
                "dir_down": it.get("DIR_DOWN_NAME", ""),
                "first_run": it.get("FIRST_RUN_TIME", ""),
                "last_run": it.get("LAST_RUN_TIME", ""),
                "interval": it.get("RUN_INTERVAL", ""),
            }
    _LINE_META_CACHE = out
    return out
```

- [ ] **Step 3: kind_label 단위 테스트 작성 (실패 확인용)**

`backend/test_app.py` 끝에 추가:
```python
def test_kind_label_maps_known_codes():
    from backend.seeds.gj_constants import kind_label
    assert kind_label(1) == "급행"
    assert kind_label(2) == "간선"
    assert kind_label(3) == "지선"
    assert kind_label(4) == "농어촌"
    assert kind_label("3") == "지선"   # 문자열도 허용
    assert kind_label(None) == "버스"  # 폴백
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

Run: `source .venv/bin/activate && python -m pytest backend/test_app.py::test_kind_label_maps_known_codes -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/seeds/gj_constants.py backend/routes/stations.py backend/test_app.py
git commit -m "feat(bis): LINE_KIND 라벨 상수 + lineInfo 메타 메모리 캐시 헬퍼"
```

---

## Task 2: 정류소→노선 역산 시드 스크립트 + 캐시 JSON

**Files:**
- Create: `backend/seeds/derive_station_routes.py`
- Create: `backend/seeds/station_routes_cache.json` (스크립트로 생성, 커밋)
- Test: 스크립트 실행 결과 수동 대조 (사용자 캡처와 일치)

- [ ] **Step 1: 역산 스크립트 작성**

`backend/seeds/derive_station_routes.py` 생성:
```python
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
```

- [ ] **Step 2: 스크립트 실행 → 캐시 생성**

Run: `source .venv/bin/activate && python -m backend.seeds.derive_station_routes`
Expected (대략): busstop 80 / 1981 각각에 `송암47(간선), 진월177(지선), 진월77(지선), 수완03(급행), 318...(농어촌), 318-1...(농어촌)` 류가 출력. `backend/seeds/station_routes_cache.json` 생성됨.

- [ ] **Step 3: 캡처와 수동 대조**

생성된 노선 목록이 사용자 캡처(송암47·진월177·진월77·수완03·318·318-1)를 **포함**하는지 눈으로 확인. (BIS가 더 많은 노선을 줄 수 있음 — 포함되면 정상.)

- [ ] **Step 4: 커밋**

```bash
git add backend/seeds/derive_station_routes.py backend/seeds/station_routes_cache.json
git commit -m "feat(bis): 정류소→노선 역산 시드 스크립트 + GJ3229/GJ3230 캐시"
```

---

## Task 3: `/api/station-board/<busstop_id>` 엔드포인트 (P1)

**Files:**
- Modify: `backend/routes/stations.py`
- Test: `backend/test_app.py`

- [ ] **Step 1: 캐시 로더 + 엔드포인트 작성**

`backend/routes/stations.py`의 `_line_meta_map` 아래에 추가:
```python
import json as _json

_STATION_ROUTES_CACHE = None


def _station_routes_cache() -> dict:
    """station_routes_cache.json 로드 (1회). busstop_id(str) → {dir_label, routes:[...]}"""
    global _STATION_ROUTES_CACHE
    if _STATION_ROUTES_CACHE is None:
        path = os.path.join(PROJECT_ROOT, "backend", "seeds", "station_routes_cache.json")
        try:
            with open(path, encoding="utf-8") as f:
                _STATION_ROUTES_CACHE = _json.load(f)
        except (OSError, ValueError):
            _STATION_ROUTES_CACHE = {}
    return _STATION_ROUTES_CACHE
```

`backend/routes/stations.py` 상단 import에 `PROJECT_ROOT`가 없으면 추가 — 파일 상단 import 영역을 확인하고, 없으면:
```python
from backend.config import GJ_BIS_API_KEY, GJ_BIS_BASE_URL, PROJECT_ROOT
```
(기존 `from backend.config import ...` 줄에 `PROJECT_ROOT`를 합칠 것. config.py에 `PROJECT_ROOT` 정의 존재함.)

`/api/gj-stops` 라우트 아래에 엔드포인트 추가:
```python
@stations_bp.route("/api/station-board/<int:busstop_id>")
@limiter.limit("30 per minute")
def station_board(busstop_id: int):
    """정류소 경유노선(캐시) + 실시간 도착(arriveInfo) 병합 — Kakao형 정류장 보드."""
    entry = _station_routes_cache().get(str(busstop_id))
    if not entry:
        return jsonify({
            "status": "ok",
            "data": {"busstop_id": busstop_id, "dir_label": "", "routes": []},
            "timestamp": datetime.now().isoformat(),
        })

    # 실시간 도착 (line_id → arrival)
    arr_by_line = {}
    data = _call_gj_bis("arriveInfo", {"BUSSTOP_ID": busstop_id})
    for it in (_gj_bis_items(data, "ARRIVE_LIST") if data else []):
        try:
            lid = int(it.get("LINE_ID"))
        except (TypeError, ValueError):
            continue
        arr_by_line[lid] = {
            "min": int(it.get("REMAIN_MIN") or 0),
            "stops": int(it.get("REMAIN_STOP") or 0),
            "low": int(it.get("LOW_BUS") or 0) == 1,
            "imminent": int(it.get("ARRIVE_FLAG") or 0) == 1,
        }

    routes = []
    for r in entry["routes"]:
        lid = r["line_id"]
        routes.append({
            "line_id": lid,
            "line_name": r["line_name"],
            "line_kind": r["line_kind"],
            "kind_label": kind_label(r["line_kind"]),
            "arrival": arr_by_line.get(lid),  # 없으면 None = 정보없음
        })

    return jsonify({
        "status": "ok",
        "data": {"busstop_id": busstop_id, "dir_label": entry["dir_label"], "routes": routes},
        "timestamp": datetime.now().isoformat(),
    })
```

- [ ] **Step 2: 테스트 작성 (mock arriveInfo)**

`backend/test_app.py`의 import 영역에 `responses`, `GJ_BIS_BASE_URL`가 이미 있음(기존 arrive 테스트 참고). 끝에 추가:
```python
@responses.activate
def test_station_board_merges_cache_with_arrival(client, monkeypatch):
    """캐시 노선 목록 + arriveInfo ETA 병합, 매칭 없으면 arrival=None."""
    import backend.routes.stations as st
    # 캐시 강제 주입 (실파일 의존 제거)
    monkeypatch.setattr(st, "_STATION_ROUTES_CACHE", {
        "80": {"dir_label": "금호타운아파트 방향", "routes": [
            {"line_id": 24, "line_name": "송암47", "line_kind": 2},
            {"line_id": 99, "line_name": "수완03", "line_kind": 1},
        ]}
    })
    responses.add(
        responses.GET, f"{GJ_BIS_BASE_URL}/arriveInfo",
        json={"RESPONSE": {"RESULT": {"RESULT_CODE": "SUCCESS"},
              "ARRIVE_LIST": {"ITEM": [
                  {"LINE_ID": 24, "REMAIN_MIN": 3, "REMAIN_STOP": 2, "LOW_BUS": 0, "ARRIVE_FLAG": 0}
              ]}}},
        status=200,
    )
    resp = client.get("/api/station-board/80")
    assert resp.status_code == 200
    data = resp.json["data"]
    assert data["dir_label"] == "금호타운아파트 방향"
    by_id = {r["line_id"]: r for r in data["routes"]}
    assert by_id[24]["kind_label"] == "간선"
    assert by_id[24]["arrival"]["min"] == 3
    assert by_id[99]["arrival"] is None   # 도착 없음 = 정보없음


def test_station_board_unknown_busstop_returns_empty(client):
    resp = client.get("/api/station-board/12345")
    assert resp.status_code == 200
    assert resp.json["data"]["routes"] == []
```

- [ ] **Step 3: 테스트 실행**

Run: `source .venv/bin/activate && python -m pytest backend/test_app.py -k station_board -v`
Expected: 2 PASS

- [ ] **Step 4: 커밋**

```bash
git add backend/routes/stations.py backend/test_app.py
git commit -m "feat(bis): /api/station-board — 정류소 경유노선 + 실시간 도착 병합"
```

---

## Task 4: `/api/line-stations/<line_id>` 엔드포인트 (P2)

**Files:**
- Modify: `backend/routes/stations.py`
- Test: `backend/test_app.py`

- [ ] **Step 1: 엔드포인트 작성**

`station_board` 아래에 추가:
```python
@stations_bp.route("/api/line-stations/<int:line_id>")
@limiter.limit("30 per minute")
def line_stations(line_id: int):
    """노선 경유정류소 순서(SEQ) + 노선 메타 — Kakao형 노선 상세."""
    data = _call_gj_bis("lineStationInfo", {"LINE_ID": line_id})
    raw = _gj_bis_items(data, "BUSSTOP_LIST") if data else []
    stops = []
    for s in raw:
        try:
            stops.append({
                "seq": int(s.get("SEQ") or 0),
                "busstop_id": int(s.get("BUSSTOP_ID")),
                "ars_id": s.get("ARS_ID", ""),
                "name": s.get("BUSSTOP_NAME", ""),
                "lat": float(s.get("LATITUDE")) if s.get("LATITUDE") else None,
                "lng": float(s.get("LONGITUDE")) if s.get("LONGITUDE") else None,
            })
        except (TypeError, ValueError):
            continue
    stops.sort(key=lambda x: x["seq"])

    meta = _line_meta_map().get(line_id, {})
    return jsonify({
        "status": "ok",
        "data": {
            "line_id": line_id,
            "line_name": meta.get("line_name", ""),
            "line_kind": meta.get("line_kind"),
            "kind_label": meta.get("kind_label", "버스"),
            "dir_up": meta.get("dir_up", ""),
            "dir_down": meta.get("dir_down", ""),
            "first_run": meta.get("first_run", ""),
            "last_run": meta.get("last_run", ""),
            "interval": meta.get("interval", ""),
            "stops": stops,
        },
        "timestamp": datetime.now().isoformat(),
    })
```

- [ ] **Step 2: 테스트 작성 (mock lineStationInfo + lineInfo)**

`backend/test_app.py` 끝에 추가:
```python
@responses.activate
def test_line_stations_returns_ordered_stops(client, monkeypatch):
    import backend.routes.stations as st
    monkeypatch.setattr(st, "_LINE_META_CACHE", {
        24: {"line_name": "송암47", "line_kind": 2, "kind_label": "간선",
             "dir_up": "덕남마을 입구", "dir_down": "장등동",
             "first_run": "05:40", "last_run": "22:30", "interval": "15"},
    })
    responses.add(
        responses.GET, f"{GJ_BIS_BASE_URL}/lineStationInfo",
        json={"RESPONSE": {"RESULT": {"RESULT_CODE": "SUCCESS"},
              "BUSSTOP_LIST": {"ITEM": [
                  {"SEQ": 2, "BUSSTOP_ID": 332, "ARS_ID": "4226", "BUSSTOP_NAME": "도선사",
                   "LATITUDE": 35.195626, "LONGITUDE": 126.934697},
                  {"SEQ": 1, "BUSSTOP_ID": 1165, "ARS_ID": "4311", "BUSSTOP_NAME": "장등동",
                   "LATITUDE": 35.200203, "LONGITUDE": 126.933688},
              ]}}},
        status=200,
    )
    resp = client.get("/api/line-stations/24")
    assert resp.status_code == 200
    d = resp.json["data"]
    assert d["kind_label"] == "간선"
    assert d["first_run"] == "05:40"
    # SEQ 정렬 확인
    assert [s["name"] for s in d["stops"]] == ["장등동", "도선사"]
    assert d["stops"][0]["ars_id"] == "4311"
```

- [ ] **Step 3: 테스트 실행**

Run: `source .venv/bin/activate && python -m pytest backend/test_app.py -k line_stations -v`
Expected: PASS

- [ ] **Step 4: 커밋**

```bash
git add backend/routes/stations.py backend/test_app.py
git commit -m "feat(bis): /api/line-stations — 노선 경유정류소 순서 + 메타"
```

---

## Task 5: 프론트 데이터 계층 (api.js 래퍼 + data.js 매퍼 + 테스트)

**Files:**
- Modify: `frontend/shared/api.js`
- Modify: `frontend/student/data.js`
- Test: `frontend/student/data.test.js`

- [ ] **Step 1: shared/api.js 래퍼 추가**

`frontend/shared/api.js`의 `fetchRecentEvents` 아래(파일 끝)에 추가:
```javascript
// 2026-06-04: Kakao형 정류장 보드 / 노선 상세
async function fetchStationBoard(busstopId) {
  return fetchAPI('/station-board/' + busstopId);
}

async function fetchLineStations(lineId) {
  return fetchAPI('/line-stations/' + lineId);
}
```
(`fetchBusLocation`은 이미 존재 — P3에서 재사용.)

- [ ] **Step 2: data.js 매퍼 작성 (mapStationBoard, mapLineStations, mapBusPositions)**

`frontend/student/data.js`의 `mapArrivalsForRoute` 함수 아래에 추가:
```javascript
// station-board 응답 → 보드 뷰모델 (백엔드가 대부분 정형화; 패스스루 + 안전 가드)
function mapStationBoard(data) {
  if (!data || !Array.isArray(data.routes)) return { dirLabel: '', routes: [] };
  return {
    dirLabel: data.dir_label || '',
    routes: data.routes.map(function (r) {
      var a = r.arrival;
      return {
        lineId: r.line_id,
        lineName: r.line_name || '',
        kindLabel: r.kind_label || '버스',
        arrival: a ? { min: a.min, stops: a.stops, low: !!a.low, imminent: !!a.imminent } : null,
      };
    }),
  };
}

// line-stations 응답 → 노선 상세 뷰모델. myBusstopIds(배열) 중 하나면 isMine=true.
function mapLineStations(data, myBusstopIds) {
  if (!data) return null;
  var mine = {};
  (myBusstopIds || []).forEach(function (id) { mine[Number(id)] = true; });
  var stops = (Array.isArray(data.stops) ? data.stops : []).map(function (s) {
    return {
      seq: s.seq, busstopId: s.busstop_id, arsId: s.ars_id || '',
      name: s.name || '', lat: s.lat, lng: s.lng,
      isMine: !!mine[Number(s.busstop_id)],
    };
  });
  return {
    lineId: data.line_id, lineName: data.line_name || '', kindLabel: data.kind_label || '버스',
    dirUp: data.dir_up || '', dirDown: data.dir_down || '',
    firstRun: data.first_run || '', lastRun: data.last_run || '', interval: data.interval || '',
    stops: stops,
  };
}

// bus_location items → 경유정류소 stops 위의 SEQ 위치 배열. 필드 미확정 → 방어적.
// 1순위 BUSSTOP_ID 매칭, 2순위 BUSSTOP_SEQ, 3순위 lat/lng 최근접. 못 찾으면 제외.
function mapBusPositions(items, stops) {
  if (!Array.isArray(items) || !Array.isArray(stops) || !stops.length) return [];
  var byBusstop = {};
  stops.forEach(function (s) { byBusstop[Number(s.busstopId)] = s.seq; });
  var positions = [];
  items.forEach(function (it) {
    var seq = null;
    var bid = it.BUSSTOP_ID != null ? Number(it.BUSSTOP_ID) : null;
    if (bid != null && byBusstop[bid] != null) {
      seq = byBusstop[bid];
    } else if (it.BUSSTOP_SEQ != null || it.SEQ != null) {
      seq = Number(it.BUSSTOP_SEQ != null ? it.BUSSTOP_SEQ : it.SEQ);
    } else if (it.LATITUDE != null && it.LONGITUDE != null) {
      var best = null, bestD = Infinity;
      var la = Number(it.LATITUDE), lo = Number(it.LONGITUDE);
      stops.forEach(function (s) {
        if (s.lat == null || s.lng == null) return;
        var d = (s.lat - la) * (s.lat - la) + (s.lng - lo) * (s.lng - lo);
        if (d < bestD) { bestD = d; best = s.seq; }
      });
      seq = best;
    }
    if (seq != null) positions.push(seq);
  });
  return positions;
}
```

- [ ] **Step 3: data.js 비동기 페처 작성**

`frontend/student/data.js`의 `loadArrivalAndRunning` 아래에 추가:
```javascript
// 정류장 보드: busstopId 없으면 빈 보드.
async function loadStationBoard(busstopId) {
  if (!busstopId) return { dirLabel: '', routes: [] };
  var data = await fetchStationBoard(busstopId);   // shared/api.js
  return mapStationBoard(data);
}

// 노선 상세: 경유정류소 + 메타. myBusstopIds로 내 정류장 하이라이트.
async function loadLineStations(lineId, myBusstopIds) {
  var data = await fetchLineStations(lineId);
  return mapLineStations(data, myBusstopIds);
}

// 노선 현재 차량 위치 → stops 위 SEQ 배열.
async function loadBusPositions(lineId, stops) {
  var data = await fetchBusLocation(lineId);
  var items = (data && data.items) ? data.items : [];
  return mapBusPositions(items, stops);
}
```

- [ ] **Step 4: data.js export에 신규 함수 추가**

`frontend/student/data.js` 맨 아래 `window.Data = {...}` 또는 module.exports 블록을 확인하고, 신규 함수들을 노출. 현재 export 형태를 따라 추가:
- 브라우저 노출(`window.Data = { ... }`)이면: `mapStationBoard, mapLineStations, mapBusPositions, loadStationBoard, loadLineStations, loadBusPositions` 추가.
- Node 테스트용 `module.exports`가 별도면 거기에도 `mapStationBoard, mapLineStations, mapBusPositions` 추가.

(파일 하단 export 블록을 Read로 확인 후 동일 패턴으로 키 추가할 것. 매퍼 3종은 테스트 대상이라 반드시 export.)

- [ ] **Step 5: data.test.js 테스트 작성**

`frontend/student/data.test.js` 끝에 추가:
```javascript
test('mapStationBoard: 도착 매칭 + 정보없음(null) + 종류 라벨', () => {
  const r = D.mapStationBoard({
    dir_label: '구암 방향',
    routes: [
      { line_id: 24, line_name: '송암47', kind_label: '간선',
        arrival: { min: 3, stops: 2, low: false, imminent: false } },
      { line_id: 99, line_name: '수완03', kind_label: '급행', arrival: null },
    ],
  });
  assert.strictEqual(r.dirLabel, '구암 방향');
  assert.strictEqual(r.routes[0].arrival.min, 3);
  assert.strictEqual(r.routes[0].kindLabel, '간선');
  assert.strictEqual(r.routes[1].arrival, null);
});

test('mapLineStations: SEQ 정류소 + 내 정류장 하이라이트', () => {
  const r = D.mapLineStations({
    line_id: 24, line_name: '송암47', kind_label: '간선',
    first_run: '05:40', last_run: '22:30', interval: '15',
    stops: [
      { seq: 1, busstop_id: 1165, ars_id: '4311', name: '장등동', lat: 35.2, lng: 126.9 },
      { seq: 2, busstop_id: 80, ars_id: '3229', name: '광주대', lat: 35.107, lng: 126.897 },
    ],
  }, [80, 1981]);
  assert.strictEqual(r.kindLabel, '간선');
  assert.strictEqual(r.stops[1].isMine, true);
  assert.strictEqual(r.stops[0].isMine, false);
});

test('mapBusPositions: BUSSTOP_ID 매칭 → SEQ, 없으면 lat/lng 최근접', () => {
  const stops = [
    { seq: 1, busstopId: 1165, lat: 35.20, lng: 126.93 },
    { seq: 2, busstopId: 80, lat: 35.107, lng: 126.897 },
  ];
  // BUSSTOP_ID 매칭
  assert.deepStrictEqual(D.mapBusPositions([{ BUSSTOP_ID: 80 }], stops), [2]);
  // 좌표 최근접 (광주대 근처)
  assert.deepStrictEqual(
    D.mapBusPositions([{ LATITUDE: 35.108, LONGITUDE: 126.898 }], stops), [2]);
  // 매칭 불가 → 제외
  assert.deepStrictEqual(D.mapBusPositions([{}], stops), []);
});
```

- [ ] **Step 6: 테스트 실행**

Run: `node frontend/student/data.test.js`
Expected: 기존 14 + 신규 3 = `pass 17  fail 0`

- [ ] **Step 7: 커밋**

```bash
git add frontend/shared/api.js frontend/student/data.js frontend/student/data.test.js
git commit -m "feat(student): 정류장 보드/노선상세/차량위치 매퍼 + 페처 + 단위 테스트"
```

---

## Task 6: 정류장 보드 뷰 (P1) — 검색 탭

**Files:**
- Modify: `frontend/student/index.html`
- Modify: `frontend/student/app.js`
- Modify: `frontend/student/style.css`

- [ ] **Step 1: index.html — 검색 패널에 보드 컨테이너 추가**

`frontend/student/index.html`의 검색 패널(`data-panel="search"`) 안, `routeList` div **앞**에 추가:
```html
      <div class="board-head" id="boardHead" hidden>
        <div>
          <div class="board-dir" id="boardDir"></div>
        </div>
        <button class="board-refresh" id="boardRefresh" aria-label="새로고침">↻</button>
      </div>
      <div class="board-list" id="boardList"></div>
```
(`routeList`/`searchCount` 등 기존 노선 추천 카드 영역은 §Task 9에서 정리. 이번 Task는 보드 추가만.)

- [ ] **Step 2: app.js — DOM 캐시 + 보드 상태 추가**

`frontend/student/app.js` 상단 DOM 캐시 영역(`const stationStatusMeta = $('stationStatusMeta');` 부근)에 추가:
```javascript
const boardHead    = $('boardHead');
const boardDir     = $('boardDir');
const boardList    = $('boardList');
const boardRefresh = $('boardRefresh');
```
`state` 객체에 추가(예: `statusTimer: null,` 옆):
```javascript
  boardTimer: null,        // 정류장 보드 30초 갱신
```
공용 상수(파일 상단 CONGESTION 부근)에 추가:
```javascript
// 노선 종류 라벨 → 배지 색
const KIND_COLOR = { '급행': '#ef4444', '간선': '#3b82f6', '지선': '#22c55e', '농어촌': '#f97316' };
```

- [ ] **Step 3: app.js — 보드 렌더/로드 함수 작성**

`renderSearchResults` 함수 아래에 추가:
```javascript
function arrivalText(a) {
  if (!a) return '<span class="bd-noinfo">정보없음</span>';
  if (a.imminent) return '<span class="bd-soon">곧 도착</span>';
  return '<span class="bd-eta">' + a.min + '분<small>·' + a.stops + '정거장</small></span>';
}

function boardRowHTML(r, dirLabel) {
  var color = KIND_COLOR[r.kindLabel] || '#64748b';
  return '<div class="bd-row" role="button" tabindex="0" data-line="' + r.lineId + '">' +
    '<div class="bd-left">' +
      '<span class="bd-badge" style="background:' + color + '">' + esc(r.kindLabel) + '</span>' +
      '<span class="bd-name">' + esc(r.lineName) + '</span>' +
      (r.arrival && r.arrival.low ? '<span class="bd-low">저상</span>' : '') +
      '<div class="bd-dir">' + esc(dirLabel) + '</div>' +
    '</div>' +
    '<div class="bd-right">' + arrivalText(r.arrival) + '</div>' +
  '</div>';
}

async function loadBoard() {
  var s = state.activeStation;
  var busstopId = s ? state.busstopMap[s.ars_no] : null;
  if (!s) { boardHead.hidden = true; boardList.innerHTML = ''; return; }
  if (!busstopId) {
    boardHead.hidden = true;
    boardList.innerHTML = '<div class="bd-empty">🚍 셔틀 정류장 · 실시간 시내버스 도착 없음</div>';
    return;
  }
  var board = await Data.loadStationBoard(busstopId);
  // 정류장 전환 race 가드
  if (!state.activeStation || state.busstopMap[state.activeStation.ars_no] !== busstopId) return;
  boardHead.hidden = false;
  boardDir.textContent = board.dirLabel;
  if (!board.routes.length) {
    boardList.innerHTML = '<div class="bd-empty">경유 노선 정보가 없습니다</div>';
    return;
  }
  boardList.innerHTML = board.routes.map(function (r) {
    return boardRowHTML(r, board.dirLabel);
  }).join('');
  bindBoardRows();
}

function bindBoardRows() {
  boardList.querySelectorAll('.bd-row').forEach(function (el) {
    el.addEventListener('click', function () {
      openLineDetail(Number(el.dataset.line));   // Task 7에서 정의
    });
  });
}

function startBoardTimer() {
  stopBoardTimer();
  state.boardTimer = setInterval(loadBoard, 30000);
}
function stopBoardTimer() {
  if (state.boardTimer) { clearInterval(state.boardTimer); state.boardTimer = null; }
}
```

- [ ] **Step 4: app.js — 정류장 선택/탭 전환에 보드 연결**

`bindStationItems`의 정류장 선택 핸들러(현재 `refreshStationStatus();` 호출 부근)에 `loadBoard(); startBoardTimer();` 추가. `stationCtxBtn`(정류장 변경) 핸들러에는 `stopBoardTimer(); boardHead.hidden = true; boardList.innerHTML = '';` 추가. 탭 전환 핸들러(`tabsEl.addEventListener('click', ...)`)에서 검색 탭을 떠나면 `stopBoardTimer()`, 검색 탭이고 정류장 있으면 `startBoardTimer()`.
보드 새로고침 버튼:
```javascript
boardRefresh.addEventListener('click', loadBoard);
```

- [ ] **Step 5: style.css — 보드 스타일**

`frontend/student/style.css` 끝에 추가:
```css
/* 정류장 보드 (Kakao형) */
.board-head { display:flex; align-items:center; justify-content:space-between; padding:8px 2px; }
.board-dir { font-size:13px; color:var(--text-secondary); }
.board-refresh { background:none; border:none; font-size:18px; cursor:pointer; color:var(--text-secondary); }
.board-list { display:flex; flex-direction:column; }
.bd-row { display:flex; align-items:center; justify-content:space-between; gap:10px;
  padding:12px 6px; border-bottom:1px solid var(--search-input-border); cursor:pointer; }
.bd-left { min-width:0; }
.bd-badge { display:inline-block; color:#fff; font-size:11px; font-weight:700;
  padding:2px 6px; border-radius:4px; margin-right:6px; vertical-align:middle; }
.bd-name { font-size:15px; font-weight:700; color:var(--text-primary); vertical-align:middle; }
.bd-low { display:inline-block; margin-left:6px; font-size:10px; color:#0369a1;
  background:#e0f2fe; border-radius:4px; padding:1px 4px; vertical-align:middle; }
.bd-dir { font-size:12px; color:var(--text-secondary); margin-top:3px; }
.bd-right { flex-shrink:0; text-align:right; }
.bd-eta { font-size:15px; font-weight:800; color:var(--text-primary); }
.bd-eta small { font-size:11px; font-weight:500; color:var(--text-secondary); margin-left:2px; }
.bd-soon { font-size:14px; font-weight:800; color:#ef4444; }
.bd-noinfo { font-size:13px; color:var(--text-secondary); }
.bd-empty { padding:24px 8px; text-align:center; color:var(--text-secondary); font-size:14px; }
```

- [ ] **Step 6: 수동 스모크 (백엔드 띄우고)**

Run: `source .venv/bin/activate && python3 -m backend.app` (별도 터미널) 후 브라우저 `http://localhost:5000/student/` → 검색 → 정류장 "광주대 구암방면" 선택 → 보드에 노선 목록 + ETA/정보없음 표시. INS01 선택 → 셔틀 안내.

- [ ] **Step 7: 커밋**

```bash
git add frontend/student/index.html frontend/student/app.js frontend/student/style.css
git commit -m "feat(student): 정류장 보드 뷰 (P1) — 경유노선+배지+실시간ETA, 30초 갱신"
```

---

## Task 7: 노선 상세 뷰 (P2) — 경유정류소 타임라인

**Files:**
- Modify: `frontend/student/index.html`
- Modify: `frontend/student/app.js`
- Modify: `frontend/student/style.css`

- [ ] **Step 1: index.html — 노선 상세 바텀시트 마크업 추가**

`frontend/student/index.html`의 기존 노선 시트(`routeSheet`) 마크업 아래(또는 `</main>` 직전 시트 영역)에 추가:
```html
  <div class="sheet-backdrop" id="lineBackdrop" hidden></div>
  <section class="line-sheet" id="lineSheet" hidden aria-label="노선 상세">
    <div class="sheet-handle" id="lineHandle"></div>
    <div class="line-head">
      <span class="bd-badge" id="lineKind"></span>
      <span class="line-name" id="lineName"></span>
    </div>
    <div class="line-dir" id="lineDir"></div>
    <div class="line-meta" id="lineMeta"></div>
    <div class="line-run" id="lineRun"></div>
    <ul class="line-stops" id="lineStops"></ul>
  </section>
```

- [ ] **Step 2: app.js — DOM 캐시 + 상태**

DOM 캐시 영역에 추가:
```javascript
const lineSheet    = $('lineSheet');
const lineBackdrop = $('lineBackdrop');
const lineKind     = $('lineKind');
const lineName     = $('lineName');
const lineDir      = $('lineDir');
const lineMeta     = $('lineMeta');
const lineRun      = $('lineRun');
const lineStops    = $('lineStops');
```
`state`에 추가:
```javascript
  lineSheetOpen: false,
  posTimer: null,          // 현재 위치 20초 갱신 (Task 8)
  curLine: null,           // 현재 열린 노선 상세 뷰모델
```
공용 상수에 추가:
```javascript
const MY_BUSSTOP_IDS = [80, 1981];   // 광주대 GJ3229/GJ3230
```

- [ ] **Step 3: app.js — 노선 상세 열기/렌더/닫기**

Task 6의 `bindBoardRows`가 호출하는 `openLineDetail`를 작성. `loadBoard` 아래에 추가:
```javascript
async function openLineDetail(lineId) {
  lineSheet.hidden = false;
  lineBackdrop.hidden = false;
  state.lineSheetOpen = true;
  lineStops.innerHTML = '<li class="ls-loading">불러오는 중…</li>';
  var detail = await Data.loadLineStations(lineId, MY_BUSSTOP_IDS);
  if (!state.lineSheetOpen) return;   // 그 사이 닫힘
  if (!detail) {
    lineStops.innerHTML = '<li class="ls-loading">노선 정보를 불러오지 못했습니다</li>';
    return;
  }
  state.curLine = detail;
  renderLineDetail(detail);
  startPosTimer();                    // Task 8
}

function renderLineDetail(d) {
  lineKind.textContent = d.kindLabel;
  lineKind.style.background = KIND_COLOR[d.kindLabel] || '#64748b';
  lineName.textContent = d.lineName;
  lineDir.textContent = (d.dirDown && d.dirUp) ? (d.dirDown + ' ↔ ' + d.dirUp) : '';
  var parts = [];
  if (d.firstRun) parts.push('첫차 ' + d.firstRun);
  if (d.lastRun) parts.push('막차 ' + d.lastRun);
  if (d.interval) parts.push('배차 ' + d.interval + '분');
  lineMeta.textContent = parts.join(' · ');
  renderLineStops(d.stops, []);       // 위치는 Task 8에서 갱신
}

// positions: 현재 차량이 있는 seq 배열 (Task 8)
function renderLineStops(stops, positions) {
  var posSet = {};
  (positions || []).forEach(function (sq) { posSet[sq] = true; });
  lineStops.innerHTML = stops.map(function (s) {
    return '<li class="ls-stop' + (s.isMine ? ' ls-mine' : '') + '">' +
      '<span class="ls-dot' + (posSet[s.seq] ? ' ls-bus' : '') + '">' +
        (posSet[s.seq] ? '🚌' : '') + '</span>' +
      '<span class="ls-body"><span class="ls-name">' + esc(s.name) +
        (s.isMine ? ' <b>(현위치)</b>' : '') + '</span>' +
        '<span class="ls-ars">' + esc(s.arsId) + '</span></span>' +
    '</li>';
  }).join('');
}

function closeLineDetail() {
  lineSheet.hidden = true;
  lineBackdrop.hidden = true;
  state.lineSheetOpen = false;
  state.curLine = null;
  stopPosTimer();                     // Task 8
}
```

- [ ] **Step 4: app.js — 닫기 바인딩**

부트스트랩(이벤트 바인딩 영역)에 추가:
```javascript
lineBackdrop.addEventListener('click', closeLineDetail);
$('lineHandle').addEventListener('click', closeLineDetail);
```

- [ ] **Step 5: style.css — 노선 상세 스타일**

`frontend/student/style.css` 끝에 추가:
```css
/* 노선 상세 시트 */
.line-sheet { position:fixed; left:0; right:0; bottom:0; max-height:85vh; overflow-y:auto;
  background:var(--bg-card); border-radius:18px 18px 0 0; z-index:50; padding:8px 16px 28px;
  box-shadow:0 -4px 24px rgba(0,0,0,.18); }
.line-head { display:flex; align-items:center; gap:8px; margin-top:6px; }
.line-name { font-size:20px; font-weight:800; color:var(--text-primary); }
.line-dir { font-size:13px; color:var(--text-secondary); margin-top:4px; }
.line-meta { font-size:12px; color:var(--text-secondary); margin:4px 0 6px; }
.line-run { font-size:13px; color:var(--text-secondary); }
.line-stops { list-style:none; margin:10px 0 0; padding:0; }
.ls-stop { display:flex; align-items:flex-start; gap:10px; padding:2px 0; position:relative; }
.ls-dot { width:18px; display:flex; justify-content:center; align-items:center;
  font-size:13px; color:#cbd5e1; }
.ls-dot::before { content:''; width:9px; height:9px; border-radius:50%;
  background:#cbd5e1; border:2px solid var(--bg-card); }
.ls-dot.ls-bus::before { content:none; }
.ls-body { display:flex; flex-direction:column; padding:8px 0;
  border-bottom:1px solid var(--search-input-border); flex:1; }
.ls-name { font-size:14px; color:var(--text-primary); }
.ls-ars { font-size:11px; color:var(--text-secondary); margin-top:2px; }
.ls-mine .ls-name { font-weight:800; color:#2563eb; }
.ls-mine .ls-dot::before { background:#2563eb; width:13px; height:13px; }
.ls-loading { padding:20px; text-align:center; color:var(--text-secondary); }
```

- [ ] **Step 6: 수동 스모크**

백엔드 띄운 상태에서 보드의 노선 한 줄 탭 → 시트 열림 → 경유정류소 타임라인 + 광주대 행 하이라이트(현위치). 배경/핸들 탭 → 닫힘.

- [ ] **Step 7: 커밋**

```bash
git add frontend/student/index.html frontend/student/app.js frontend/student/style.css
git commit -m "feat(student): 노선 상세 뷰 (P2) — 경유정류소 타임라인 + 광주대 하이라이트"
```

---

## Task 8: 현재 버스 위치 (P3) — 노선 상세 위 차량 표시

**Files:**
- Modify: `frontend/student/app.js`

- [ ] **Step 1: app.js — 위치 로드/타이머**

Task 7의 `openLineDetail`가 호출하는 `startPosTimer`/`stopPosTimer`를 작성. `closeLineDetail` 아래에 추가:
```javascript
async function refreshBusPositions() {
  var d = state.curLine;
  if (!d || !state.lineSheetOpen) return;
  var positions = await Data.loadBusPositions(d.lineId, d.stops);
  if (!state.lineSheetOpen || !state.curLine || state.curLine.lineId !== d.lineId) return;
  // 헤더에 운행 상태
  lineRun.textContent = positions.length
    ? ('🚌 현재 운행 중 ' + positions.length + '대')
    : '현재 운행중인 버스 없음';
  renderLineStops(d.stops, positions);
}

function startPosTimer() {
  stopPosTimer();
  refreshBusPositions();                       // 즉시 1회
  state.posTimer = setInterval(refreshBusPositions, 20000);
}
function stopPosTimer() {
  if (state.posTimer) { clearInterval(state.posTimer); state.posTimer = null; }
}
```

- [ ] **Step 2: 수동 스모크 (운행 시간대)**

운행 차량이 있는 시간대에 보드→노선 탭 → 타임라인에 🚌가 현재 정류소에 표시 + 헤더 "현재 운행 중 N대". 운행 0대면 "현재 운행중인 버스 없음" (정상). 20초마다 갱신.

> ⚠️ `busLocationInfo` 차량 필드(BUSSTOP_ID/SEQ/좌표 유무)는 운행 차량으로 최종 확인. `mapBusPositions`가 세 경로(BUSSTOP_ID→SEQ→좌표)로 방어하므로 어느 필드가 와도 동작. 만약 셋 다 없으면 위치는 안 뜨고 "운행중 버스 없음"으로 표시(깨지지 않음).

- [ ] **Step 3: 커밋**

```bash
git add frontend/student/app.js
git commit -m "feat(student): 현재 버스 위치 (P3) — 노선 타임라인 위 차량 표시, 20초 갱신"
```

---

## Task 9: 정류장 뷰 정리 — 기존 노선추천 카드 → 보드로 교체, 혼잡도 공존

**Files:**
- Modify: `frontend/student/app.js`
- Modify: `frontend/student/index.html` (필요 시)

- [ ] **Step 1: 검색 탭에서 노선추천 카드 렌더 비활성화**

`renderSearchResults`에서 정류장 선택 상태일 때 `routeListEl`에 노선 추천 카드를 그리던 부분을 **보드가 대체**하므로, 정류장 선택 시에는 `routeListEl.innerHTML = ''`로 비우고 `searchCount`/노선카드 렌더를 건너뛴다. (정류장 미선택=정류장 검색 목록은 그대로 유지.) `loadRoutesForStation` 호출도 정류장 선택 핸들러에서 제거(보드가 대신함). 단 **혼잡도 예측은 노선 상세(§Task 7 renderLineDetail) 하단 섹션 또는 홈 카드로 유지** — 이번 단계에서 노선추천 카드만 화면에서 내린다.

> 구체: `bindStationItems`의 선택 핸들러에서 `const cards = await Data.loadRoutesForStation(...)`와 `state.routeCards = cards;` 줄 제거, 대신 `loadBoard(); startBoardTimer();` 유지. `renderSearchResults`의 `state.activeStation` 분기에서 노선 카드 렌더 대신 `routeListEl.innerHTML=''; searchCountEl.textContent='';` 처리하고 보드(`boardList`)가 노선 표시를 담당.

- [ ] **Step 2: 홈 혼잡도 카드 유지 확인**

홈(즐겨찾기 탭)의 "실시간 정류장 상황" 카드(`stationStatusCard`)는 그대로 둔다 — 변경 없음. (혼잡도 USP 공존: §spec 7.)

- [ ] **Step 3: 회귀 — 기존 JS/백엔드 테스트 전체 재실행**

Run: `node frontend/student/data.test.js && source .venv/bin/activate && python -m pytest backend/test_app.py -q`
Expected: data.test `pass 17 fail 0`, pytest 전부 PASS.

- [ ] **Step 4: 수동 스모크 — 전체 흐름**

정류장 검색→선택→보드(노선+ETA)→노선 탭→경유정류소+현위치→닫기→다른 정류장 전환(타이머 정리 확인)→홈 혼잡도 카드 정상.

- [ ] **Step 5: 커밋**

```bash
git add frontend/student/app.js frontend/student/index.html
git commit -m "refactor(student): 정류장 뷰를 BIS 보드로 교체, 혼잡도는 홈/노선상세로 공존"
```

---

## Self-Review (완료)

- **Spec 커버리지:** P1(Task 3,6)·P2(Task 4,7)·P3(Task 8)·정류소→노선 역산(Task 2)·LINE_KIND 배지(Task 1)·혼잡도 공존(Task 9)·에러 폴백(각 엔드포인트/로더 None 가드)·테스트(Task 1,3,4,5,9) 모두 태스크 존재.
- **타입 일관성:** 백엔드 `line_id/line_name/line_kind/kind_label/arrival{min,stops,low,imminent}` ↔ 프론트 `lineId/lineName/kindLabel/arrival{min,stops,low,imminent}` 매퍼에서 일관 변환. `stops[].busstop_id`↔`busstopId`, `isMine` 일관. `mapBusPositions`는 seq 배열, `renderLineStops(stops, positions)` 시그니처 일치.
- **플레이스홀더:** 없음(모든 코드 단계에 실제 코드 포함). Task 5 Step4·Task 9 Step1은 기존 파일 구조 확인 후 동일 패턴 적용 지시(파일별 export/렌더 형태가 한 가지라 모호성 없음).
