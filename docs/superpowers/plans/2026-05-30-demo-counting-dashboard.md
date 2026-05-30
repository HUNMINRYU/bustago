# 시연용 카운팅 대시보드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한 명이 정류장에 들어와(IN) → 대기 +1 → 버스 탑승(BOARD) → 대기 0으로 떨어지는 한 사이클을, Jetson 카메라 시연 + 관리자 대시보드 백업 버튼 두 경로로 실시간(3초 이내) 보여준다.

**Architecture:** 백엔드 신규 3개 엔드포인트(`/event`, `/reset`, `/recent`)가 DEMO01 정류장 전용으로 동작. counter.py는 라인 통과 즉시 POST. 관리자 대시보드는 2초 폴링 + 카드 플래시 애니메이션 + 이벤트 피드 + 시연 제어 버튼. 모든 시연 UI는 정류장 필터 = DEMO01일 때만 표시.

**Tech Stack:** Flask 3 + SQLite + pytest (백엔드), Python 3.10 + Ultralytics YOLO + DeepSORT + requests (Jetson), Vanilla JS + CSS3 keyframes (프론트엔드).

**Spec:** `docs/superpowers/specs/2026-05-30-demo-counting-dashboard-design.md` (커밋 27c85cc).

---

## File Structure

| 파일 | 변경 종류 | 책임 |
|------|-----------|------|
| `backend/schema.sql` | Modify | DEMO01 정류장 INSERT 1줄 |
| `backend/routes/crowd.py` | Modify | 기존 `crowd_bp`에 신규 3 엔드포인트 추가 + 헬퍼 1개 |
| `backend/test_app.py` | Modify | 신규 엔드포인트 3개의 happy path + 엣지 케이스 테스트 |
| `hardware/counter.py` | Modify | `APIReporter._last_in/_last_board` 상태 + `post_if_changed` 메서드 + 메인 루프 1줄 |
| `hardware/tests/test_api_reporter.py` | Create | `post_if_changed` 단위 테스트 (HTTP 모킹) |
| `frontend/shared/api.js` | Modify | `fetchAPI` POST 지원 확장 + `postEvent`/`postReset`/`fetchRecentEvents` 3 함수 |
| `frontend/admin/index.html` | Modify | DEMO01 정류장 옵션 + 이벤트 피드 패널 + 시연 제어 패널 (둘 다 `hidden`) |
| `frontend/admin/style.css` | Modify | `.flash` 애니메이션 + 이벤트 리스트 + 시연 버튼 스타일 |
| `frontend/admin/dashboard.js` | Modify | 폴링 10s→2s, `setCardValue` 헬퍼, `loadEvents`, 버튼 핸들러, DEMO01 조건부 표시 |

**보안 경계:** 새 엔드포인트 3개 모두 `station_id` 화이트리스트 = `{"DEMO01"}`. INS01/GATE01에는 절대 영향 없음.

---

## Task 1: 백엔드 — DEMO01 정류장 스키마 + 헬퍼

**Files:**
- Modify: `backend/schema.sql:39-55` (광주 INSERT 블록 옆)
- Modify: `backend/routes/crowd.py:18-32` (검증 헬퍼 옆)

- [ ] **Step 1: schema.sql에 DEMO01 INSERT 추가**

`backend/schema.sql` 광주 정류장 INSERT 블록 바로 아래에 추가:

```sql
-- 시연용 정류장 (광주대 좌표와 동일 — 지도 동일점에 찍힘)
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude) VALUES
('DEMO01', '시연용 정류장 (광주대)', 35.1378, 126.8942);
```

- [ ] **Step 2: crowd.py에 DEMO 화이트리스트 헬퍼 추가**

`backend/routes/crowd.py`의 `_validate_non_negative_int` 함수 뒤(33번째 줄 부근)에 추가:

```python
DEMO_STATION_ID = "DEMO01"


def _validate_demo_station(station_id):
    """시연 전용 엔드포인트 진입 전 station_id 검사. DEMO01만 허용."""
    _validate_station_id(station_id)
    if station_id != DEMO_STATION_ID:
        abort(400, description=f"This endpoint only accepts station_id={DEMO_STATION_ID}")
```

- [ ] **Step 3: SQLite DB 재초기화로 DEMO01 적재**

Bash:

```bash
rm -f backend/bustago.db
cd /home/ahble/projects/Capstone/bustago
python3 -c "from backend.models.db import init_db; init_db()"
sqlite3 backend/bustago.db "SELECT ars_no FROM stations WHERE ars_no='DEMO01';"
```

Expected output: `DEMO01`

- [ ] **Step 4: Commit**

```bash
git add backend/schema.sql backend/routes/crowd.py
git commit -m "feat(crowd): DEMO01 시연용 정류장 + DEMO 화이트리스트 헬퍼"
```

---

## Task 2: 백엔드 — `POST /api/crowd-count/event` 엔드포인트

**Files:**
- Modify: `backend/test_app.py` (테스트 추가)
- Modify: `backend/routes/crowd.py` (엔드포인트 추가)

- [ ] **Step 1: Write failing tests**

`backend/test_app.py` 끝에 추가:

```python
# ---------------------------------------------------------------------------
# Demo 엔드포인트 — POST /api/crowd-count/event
# ---------------------------------------------------------------------------

def test_event_in_from_empty(client):
    """빈 상태에서 IN +1 → count_in=1, current_waiting=1."""
    # 사전 정리
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
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
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
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
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/ahble/projects/Capstone/bustago
python3 -m pytest backend/test_app.py::test_event_in_from_empty -v
```

Expected: FAIL with 404 (엔드포인트 미구현).

- [ ] **Step 3: Implement endpoint**

`backend/routes/crowd.py` 파일 끝에 추가 (`get_crowd_count_history` 뒤):

```python
@crowd_bp.route("/api/crowd-count/event", methods=["POST"])
@limiter.limit("30 per minute")
def post_crowd_count_event():
    """시연용 수동 이벤트 주입. station_id=DEMO01 전용.

    Body: {"station_id": "DEMO01", "event_type": "in" | "board"}
    마지막 row를 읽어와 count_in 또는 count_board 를 +1 한 새 row INSERT.
    """
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="JSON body is required")

    station_id = data.get("station_id")
    _validate_demo_station(station_id)

    event_type = data.get("event_type")
    if event_type not in ("in", "board"):
        abort(400, description="event_type must be 'in' or 'board'")

    last = fetchone(
        "SELECT count_in, count_board FROM crowd_counts "
        "WHERE station_id = ? ORDER BY id DESC LIMIT 1",
        (station_id,),
    )
    last_in = last["count_in"] if last else 0
    last_board = last["count_board"] if last else 0

    if event_type == "in":
        new_in = last_in + 1
        new_board = last_board
    else:
        if last_in - last_board <= 0:
            abort(400, description="대기 인원이 0인데 board 불가")
        new_in = last_in
        new_board = last_board + 1

    new_waiting = max(0, new_in - new_board)

    execute(
        "INSERT INTO crowd_counts (station_id, count_in, count_board, current_waiting, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (station_id, new_in, new_board, new_waiting, "demo_button"),
    )

    return jsonify({
        "status": "ok",
        "count_in": new_in,
        "count_board": new_board,
        "current_waiting": new_waiting,
        "timestamp": datetime.now().isoformat(),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/test_app.py -k "test_event_" -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/test_app.py backend/routes/crowd.py
git commit -m "feat(crowd): POST /api/crowd-count/event — 시연 백업 트리거 (DEMO01)"
```

---

## Task 3: 백엔드 — `POST /api/crowd-count/reset` 엔드포인트

**Files:**
- Modify: `backend/test_app.py`
- Modify: `backend/routes/crowd.py`

- [ ] **Step 1: Write failing tests**

`backend/test_app.py` Task 2 테스트들 아래에 추가:

```python
# ---------------------------------------------------------------------------
# Demo 엔드포인트 — POST /api/crowd-count/reset
# ---------------------------------------------------------------------------

def test_reset_clears_demo_rows(client):
    """이벤트 2건 주입 후 reset → row 0건."""
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
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
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    resp = client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["deleted_rows"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest backend/test_app.py -k "test_reset_" -v
```

Expected: 3 FAIL (404 또는 method not allowed).

- [ ] **Step 3: Implement endpoint**

`backend/routes/crowd.py` `post_crowd_count_event` 함수 뒤에 추가:

```python
@crowd_bp.route("/api/crowd-count/reset", methods=["POST"])
@limiter.limit("5 per minute")
def post_crowd_count_reset():
    """시연 사이 DEMO01 카운트 초기화. INS01 등 실제 데이터는 거부."""
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="JSON body is required")

    station_id = data.get("station_id")
    _validate_demo_station(station_id)

    deleted = execute(
        "DELETE FROM crowd_counts WHERE station_id = ?",
        (station_id,),
    )
    # execute()가 rowcount를 반환하지 않으면 별도 조회
    deleted_rows = deleted if isinstance(deleted, int) else 0

    return jsonify({
        "status": "ok",
        "deleted_rows": deleted_rows,
        "timestamp": datetime.now().isoformat(),
    })
```

> ⚠️ `execute()`가 rowcount를 반환하는지 확실치 않으면, 다음 단계에서 `db.py` 확인 후 보정. 안전을 위해 fallback 0 사용.

- [ ] **Step 4: `db.execute` 반환값 확인**

```bash
grep -n "def execute" backend/models/db.py
```

`execute`가 rowcount를 반환하면 그대로, 아니면 `cursor.rowcount`를 반환하도록 라우트에서 별도 조회로 보정:

```python
# 만약 execute가 rowcount 미반환이면 → 사전 SELECT COUNT로 산출
before = fetchone("SELECT COUNT(*) AS c FROM crowd_counts WHERE station_id = ?", (station_id,))
execute("DELETE FROM crowd_counts WHERE station_id = ?", (station_id,))
deleted_rows = before["c"] if before else 0
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest backend/test_app.py -k "test_reset_" -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/test_app.py backend/routes/crowd.py
git commit -m "feat(crowd): POST /api/crowd-count/reset — DEMO01 카운트 초기화"
```

---

## Task 4: 백엔드 — `GET /api/crowd-count/recent` 엔드포인트

**Files:**
- Modify: `backend/test_app.py`
- Modify: `backend/routes/crowd.py`

- [ ] **Step 1: Write failing tests**

`backend/test_app.py`에 추가:

```python
# ---------------------------------------------------------------------------
# Demo 엔드포인트 — GET /api/crowd-count/recent
# ---------------------------------------------------------------------------

def test_recent_returns_empty_when_no_events(client):
    """이벤트 없는 상태 → events 빈 배열."""
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    resp = client.get("/api/crowd-count/recent?station_id=DEMO01&limit=5")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["events"] == []


def test_recent_returns_in_then_board(client):
    """IN, BOARD 순서로 주입 → 최신순으로 board, in 반환."""
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
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
    client.post("/api/crowd-count/reset", json={"station_id": "DEMO01"})
    for _ in range(7):
        client.post("/api/crowd-count/event", json={"station_id": "DEMO01", "event_type": "in"})

    resp = client.get("/api/crowd-count/recent?station_id=DEMO01&limit=3")
    body = resp.get_json()
    assert len(body["events"]) == 3


def test_recent_rejects_non_demo_station(client):
    """INS01 호출 → 400."""
    resp = client.get("/api/crowd-count/recent?station_id=INS01&limit=5")
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest backend/test_app.py -k "test_recent_" -v
```

Expected: 4 FAIL (404).

- [ ] **Step 3: Implement endpoint**

`backend/routes/crowd.py` `post_crowd_count_reset` 함수 뒤에 추가:

```python
@crowd_bp.route("/api/crowd-count/recent", methods=["GET"])
@limiter.limit("60 per minute")
def get_crowd_count_recent():
    """대시보드 이벤트 피드 — 최근 N건의 IN/BOARD 전이만 반환.

    인접 row 쌍의 count_in / count_board 차분을 비교해 event_type 판정.
    동일 카운트 row(예: heartbeat)는 제외.
    """
    station_id = request.args.get("station_id")
    _validate_demo_station(station_id)

    limit_str = request.args.get("limit", "5")
    if not limit_str.isdigit() or int(limit_str) < 1 or int(limit_str) > 50:
        abort(400, description="limit must be 1-50")
    limit = int(limit_str)

    # 차분 계산 위해 limit+1 개 row 조회 (가장 오래된 1건은 이전값 비교용)
    rows = fetchall(
        "SELECT count_in, count_board, current_waiting, created_at "
        "FROM crowd_counts WHERE station_id = ? ORDER BY id DESC LIMIT ?",
        (station_id, limit + 1),
    )

    events = []
    for i in range(len(rows) - 1):
        cur = rows[i]
        prev = rows[i + 1]
        if cur["count_in"] > prev["count_in"]:
            event_type = "in"
        elif cur["count_board"] > prev["count_board"]:
            event_type = "board"
        else:
            continue  # tick (변화 없음)
        events.append({
            "created_at": cur["created_at"],
            "event_type": event_type,
            "current_waiting": cur["current_waiting"],
        })

    # 가장 오래된 row가 첫 이벤트인지 확인 (이전값이 없어서 위 루프에서 제외됨)
    if rows and len(rows) <= limit:
        first = rows[-1]
        if first["count_in"] > 0 and first["count_board"] == 0:
            events.append({
                "created_at": first["created_at"],
                "event_type": "in",
                "current_waiting": first["current_waiting"],
            })

    return jsonify({
        "status": "ok",
        "events": events[:limit],
        "timestamp": datetime.now().isoformat(),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest backend/test_app.py -k "test_recent_" -v
```

Expected: 4 passed.

- [ ] **Step 5: Run all backend tests**

```bash
python3 -m pytest backend/test_app.py -v
```

Expected: all green (기존 + 신규 12건).

- [ ] **Step 6: Commit**

```bash
git add backend/test_app.py backend/routes/crowd.py
git commit -m "feat(crowd): GET /api/crowd-count/recent — 이벤트 피드 (차분 판정)"
```

---

## Task 5: counter.py — `post_if_changed` 메서드 + 메인 루프 통합

**Files:**
- Modify: `hardware/counter.py:137-171` (APIReporter 클래스)
- Modify: `hardware/counter.py:295` (메인 루프)
- Create: `hardware/tests/test_api_reporter.py`

- [ ] **Step 1: Write failing test**

`hardware/tests/test_api_reporter.py` 생성:

```python
"""APIReporter.post_if_changed 단위 테스트 (HTTP 모킹).

dev 머신에 torch/ultralytics 미설치 시 자동 skip — Jetson에서만 실행되도록.
"""

import pytest
from unittest.mock import patch, MagicMock

# counter.py를 모듈로 import — sys.path 보강
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from counter import APIReporter, LineCrossingCounter
except ImportError as e:
    pytest.skip(f"counter import 실패 (Jetson 의존성 필요): {e}", allow_module_level=True)


@pytest.fixture
def reporter():
    return APIReporter(server_url="http://localhost:5000", station_id="DEMO01", interval=10.0)


@pytest.fixture
def counter():
    return LineCrossingCounter(frame_width=640, in_ratio=0.7, board_ratio=0.3)


def test_post_if_changed_skips_when_unchanged(reporter, counter):
    """count_in, count_board 둘 다 0이면 POST 안 보냄."""
    with patch("counter.requests.post") as mock_post:
        result = reporter.post_if_changed(counter)
    assert result is False
    mock_post.assert_not_called()


def test_post_if_changed_sends_when_count_in_increases(reporter, counter):
    """count_in 증가 시 즉시 POST 발사."""
    counter.count_in = 1
    with patch("counter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        reporter.post_if_changed(counter)
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["count_in"] == 1


def test_post_if_changed_remembers_state(reporter, counter):
    """동일 값 재호출 시 POST 안 보냄."""
    counter.count_in = 1
    with patch("counter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        reporter.post_if_changed(counter)  # 첫 호출 → POST
        reporter.post_if_changed(counter)  # 두 번째 → no-op
    assert mock_post.call_count == 1
```

- [ ] **Step 2: Run test to verify failure**

```bash
cd /home/ahble/projects/Capstone/bustago
python3 -m pytest hardware/tests/test_api_reporter.py -v
```

Expected: FAIL with AttributeError: 'APIReporter' object has no attribute 'post_if_changed'.

- [ ] **Step 3: Implement `post_if_changed`**

`hardware/counter.py:137-171` `APIReporter` 클래스의 `__init__` 끝에 2줄, `post_now` 뒤에 메서드 추가:

```python
    def __init__(self, server_url: str, station_id: str, interval: float = 10.0):
        self.url = server_url.rstrip("/")
        if not self.url.endswith("/api/crowd-count"):
            self.url += "/api/crowd-count"
        self.station_id = station_id
        self.interval = interval
        self._last_post = 0.0
        self._last_in = 0       # ← 신규
        self._last_board = 0    # ← 신규

    # (maybe_post 그대로 유지)

    def post_now(self, counter: LineCrossingCounter):
        """interval 무시하고 즉시 POST."""
        self._last_post = 0.0
        self.maybe_post(counter)

    def post_if_changed(self, counter: LineCrossingCounter) -> bool:
        """count_in/board 가 직전 호출 이후 변하면 즉시 POST.

        Returns:
            True if POST sent, False otherwise.
        """
        if counter.count_in != self._last_in or counter.count_board != self._last_board:
            self._last_in = counter.count_in
            self._last_board = counter.count_board
            self.post_now(counter)
            return True
        return False
```

- [ ] **Step 4: Run test to verify pass**

```bash
python3 -m pytest hardware/tests/test_api_reporter.py -v
```

Expected: 3 passed.

- [ ] **Step 5: 메인 루프에 1줄 추가**

`hardware/counter.py:295` `reporter.maybe_post(lc)` 줄 바로 위에 추가:

```python
            # API POST — 이벤트 발생 즉시 + 10초 heartbeat
            reporter.post_if_changed(lc)   # ← 신규: 변화 감지 시 즉시
            reporter.maybe_post(lc)         # ← 유지: 10초 heartbeat
```

- [ ] **Step 6: 전체 hardware 테스트 실행**

```bash
python3 -m pytest hardware/tests/ -v
```

Expected: 기존 + 신규 모두 통과.

- [ ] **Step 7: Commit**

```bash
git add hardware/counter.py hardware/tests/test_api_reporter.py
git commit -m "feat(counter): 라인 통과 시 즉시 POST (post_if_changed) + 10s heartbeat 유지"
```

---

## Task 6: 프론트엔드 — `shared/api.js` POST 지원 + 신규 3 함수

**Files:**
- Modify: `frontend/shared/api.js`

- [ ] **Step 1: `fetchAPI` 시그니처 확장 (POST 지원)**

`frontend/shared/api.js:5-20` 의 `fetchAPI` 함수를 다음으로 교체:

```javascript
async function fetchAPI(endpoint, params, method, body) {
  params = params || {};
  method = method || 'GET';
  var url = new URL(API_BASE + endpoint);
  Object.entries(params).forEach(function (entry) {
    url.searchParams.set(entry[0], entry[1]);
  });
  var init = { method: method, headers: {} };
  if (body) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  try {
    var res = await fetch(url, init);
    var data = await res.json();
    if (data.status !== 'ok') throw new Error(data.message);
    // POST 응답은 data.data 가 없을 수 있으므로 전체 반환
    return data.data !== undefined ? data.data : data;
  } catch (e) {
    console.error('API Error: ' + endpoint, e);
    return null;
  }
}
```

- [ ] **Step 2: 신규 3 함수 추가**

`frontend/shared/api.js` 파일 끝(`fetchBusLocation` 함수 뒤)에 추가:

```javascript
// 2026-05-30: 시연 대시보드 — 수동 이벤트 / 리셋 / 이벤트 피드 (DEMO01 전용)
async function postDemoEvent(eventType) {
  return fetchAPI('/crowd-count/event', null, 'POST',
                  { station_id: 'DEMO01', event_type: eventType });
}

async function postDemoReset() {
  return fetchAPI('/crowd-count/reset', null, 'POST',
                  { station_id: 'DEMO01' });
}

async function fetchRecentEvents(stationId, limit) {
  return fetchAPI('/crowd-count/recent',
                  { station_id: stationId, limit: limit || 5 });
}
```

- [ ] **Step 3: 백엔드 띄워서 수동 확인**

새 터미널에서:

```bash
cd /home/ahble/projects/Capstone/bustago && python3 -m backend.app
```

다른 터미널에서:

```bash
curl -X POST http://localhost:5000/api/crowd-count/reset \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01"}'
curl -X POST http://localhost:5000/api/crowd-count/event \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01","event_type":"in"}'
curl "http://localhost:5000/api/crowd-count/recent?station_id=DEMO01&limit=5"
```

Expected: 마지막 호출에서 `{"events":[{"event_type":"in","current_waiting":1,...}],...}`.

- [ ] **Step 4: Commit**

```bash
git add frontend/shared/api.js
git commit -m "feat(api): fetchAPI POST 지원 + 시연 3함수 (postDemoEvent/Reset/fetchRecentEvents)"
```

---

## Task 7: 프론트엔드 — `admin/index.html` 마크업 추가

**Files:**
- Modify: `frontend/admin/index.html`

- [ ] **Step 1: 정류장 필터에 DEMO01 옵션 추가**

`frontend/admin/index.html`에서 `<select id="station-filter">` 부분을 찾아 `DEMO01` 옵션을 마지막에 추가. 예:

```html
<select id="station-filter">
  <option value="all">전체</option>
  <option value="INS01">광주대 인성관</option>
  <option value="GATE01">광주대 정문</option>
  <option value="DEMO01">시연용 정류장</option>
</select>
```

> ⚠️ 정류장 옵션이 동적 로딩(loadStations)이라면 마크업 수정 대신 dashboard.js에서 DEMO01을 명시 추가하도록 보정 (Task 9 Step 3 참고).

- [ ] **Step 2: 카운팅 패널 옆에 이벤트 피드 패널 추가**

기존 `<section class="panel counting-panel">` 블록 바로 다음에 추가:

```html
<!-- Realtime Event Feed (DEMO01 전용) -->
<section class="panel events-panel" id="events-panel" hidden>
  <h2>최근 이벤트 <span class="live-badge">LIVE</span></h2>
  <ul id="events-list" class="events-list">
    <li class="events-empty">이벤트 대기 중...</li>
  </ul>
</section>
```

- [ ] **Step 3: 시연 제어 패널 추가**

이벤트 피드 패널 바로 다음에 추가:

```html
<!-- Demo Control Panel (DEMO01 전용) -->
<section class="panel demo-control-panel" id="demo-control-panel" hidden>
  <h2>시연 제어</h2>
  <div class="demo-buttons">
    <button id="btn-in"    class="demo-btn demo-in">🚶 IN +1</button>
    <button id="btn-board" class="demo-btn demo-board">🚌 BOARD +1</button>
    <button id="btn-reset" class="demo-btn demo-reset">↺ 리셋</button>
  </div>
  <p class="demo-hint">카메라가 사람을 놓쳤을 때 백업. DEMO01 전용. 리셋은 counter.py 재시작 필요.</p>
</section>
```

- [ ] **Step 4: 브라우저로 마크업 확인**

```bash
# 백엔드 띄운 상태에서
xdg-open http://localhost:5000/admin/ 2>/dev/null || echo "수동으로 브라우저 열기"
```

- [ ] **Step 5: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat(admin): 이벤트 피드 + 시연 제어 패널 마크업 (둘 다 hidden 기본)"
```

---

## Task 8: 프론트엔드 — `admin/style.css` 애니메이션 + 레이아웃

**Files:**
- Modify: `frontend/admin/style.css`

- [ ] **Step 1: 카드 플래시 애니메이션 추가**

`frontend/admin/style.css` 끝에 추가:

```css
/* 2026-05-30: 시연 대시보드 — 카드 플래시 + 이벤트 피드 + 시연 버튼 */

.counting-value.flash {
  animation: flashGreen 0.6s ease-out;
}

@keyframes flashGreen {
  0%   { background: #4CAF50; color: white; transform: scale(1.15); border-radius: 8px; }
  100% { background: transparent; color: #1976D2; transform: scale(1); }
}
```

- [ ] **Step 2: 이벤트 피드 패널 스타일 추가**

```css
.events-panel { margin-bottom: 24px; }
.events-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 240px;
  overflow-y: auto;
}
.events-list li {
  padding: 10px 14px;
  border-bottom: 1px solid #EEE;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  animation: slideInTop 0.3s ease-out;
}
.events-list li.events-empty {
  color: #BDBDBD;
  font-style: italic;
  font-family: inherit;
}
.events-list li.event-in    { color: #2E7D32; }
.events-list li.event-board { color: #1565C0; }

@keyframes slideInTop {
  0%   { opacity: 0; transform: translateY(-8px); }
  100% { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 3: 시연 제어 버튼 스타일 추가**

```css
.demo-control-panel { margin-bottom: 24px; background: #FFF8E1; border: 1px dashed #FFB300; }
.demo-control-panel h2 { color: #E65100; }
.demo-buttons { display: flex; gap: 12px; flex-wrap: wrap; }
.demo-btn {
  flex: 1;
  min-width: 120px;
  padding: 14px 16px;
  font-size: 1rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.1s ease-out, background 0.2s;
}
.demo-btn:active { transform: scale(0.96); }
.demo-in    { background: #2E7D32; color: white; }
.demo-in:hover    { background: #1B5E20; }
.demo-board { background: #1565C0; color: white; }
.demo-board:hover { background: #0D47A1; }
.demo-reset { background: #757575; color: white; }
.demo-reset:hover { background: #424242; }
.demo-hint { font-size: 0.8rem; color: #757575; margin-top: 12px; }
```

- [ ] **Step 4: 브라우저 새로고침 후 정류장 필터 DEMO01 선택해 패널 숨김/표시 확인**

(아직 dashboard.js 미수정이므로 패널이 안 보일 수 있음 — 마크업의 `hidden` 속성을 임시로 떼서 시각 확인만 하고 다시 붙임)

- [ ] **Step 5: Commit**

```bash
git add frontend/admin/style.css
git commit -m "style(admin): 카드 플래시 + 이벤트 피드 + 시연 버튼 (DEMO01 패널)"
```

---

## Task 9: 프론트엔드 — `admin/dashboard.js` 로직 전부 연결

**Files:**
- Modify: `frontend/admin/dashboard.js`

- [ ] **Step 1: 폴링 주기 변경**

`frontend/admin/dashboard.js:26` 의 `CROWD_REFRESH_MS` 값을 변경:

```javascript
var CROWD_REFRESH_MS = 2000;   // 기존 10000 → 2초 (시연 실시간성)
```

- [ ] **Step 2: `setCardValue` 헬퍼 추가 + `loadCrowdCount` 안에서 사용**

`loadCrowdCount` 함수 위에 헬퍼 추가:

```javascript
function setCardValue(id, newVal) {
  var el = document.getElementById(id);
  if (!el) return;
  var current = el.textContent;
  if (current !== String(newVal)) {
    el.classList.remove('flash');   // 재시작 위해
    // 강제 reflow → animation restart
    void el.offsetWidth;
    el.classList.add('flash');
    setTimeout(function() { el.classList.remove('flash'); }, 600);
  }
  el.textContent = newVal;
}
```

`loadCrowdCount` 내부의 `document.getElementById('cnt-waiting').textContent = ...` 등 3줄을 다음으로 교체:

```javascript
    setCardValue('cnt-waiting', data.current_waiting);
    setCardValue('cnt-in', data.count_in);
    setCardValue('cnt-board', data.count_board);
```

- [ ] **Step 3: 정류장 필터에 DEMO01 옵션이 누락됐다면 강제 삽입**

`DOMContentLoaded` 핸들러 위쪽에 한 번만 실행되는 로직 추가:

```javascript
// DEMO01 옵션 누락 시 강제 추가 (마크업에 이미 있으면 noop)
(function ensureDemoOption() {
  if (!stationFilter) return;
  var hasDemo = false;
  for (var i = 0; i < stationFilter.options.length; i++) {
    if (stationFilter.options[i].value === 'DEMO01') { hasDemo = true; break; }
  }
  if (!hasDemo) {
    var opt = document.createElement('option');
    opt.value = 'DEMO01';
    opt.textContent = '시연용 정류장';
    stationFilter.appendChild(opt);
  }
})();
```

- [ ] **Step 4: `loadEvents` + DEMO01 조건부 표시 추가**

`loadCrowdCount` 함수 뒤에 추가:

```javascript
async function loadEvents() {
  var sid = stationFilter.value;
  if (sid !== 'DEMO01') return;   // DEMO01 외엔 피드 안 받음

  var data = await fetchRecentEvents('DEMO01', 5);
  var list = document.getElementById('events-list');
  if (!list) return;

  if (!data || !data.events || data.events.length === 0) {
    list.innerHTML = '<li class="events-empty">이벤트 대기 중...</li>';
    return;
  }

  list.innerHTML = data.events.map(function(ev) {
    var icon = ev.event_type === 'in' ? '🚶' : '🚌';
    var label = ev.event_type === 'in' ? 'IN +1' : 'BOARD +1';
    var cls = 'event-' + ev.event_type;
    var time = (ev.created_at || '').slice(11, 19);   // "HH:MM:SS"
    return '<li class="' + cls + '">' +
      time + '  ' + icon + ' ' + label +
      '  (대기 ' + ev.current_waiting + '명)' +
    '</li>';
  }).join('');
}

function applyDemoVisibility() {
  var isDemo = (stationFilter.value === 'DEMO01');
  var demoPanel = document.getElementById('demo-control-panel');
  var eventsPanel = document.getElementById('events-panel');
  if (demoPanel)   demoPanel.hidden = !isDemo;
  if (eventsPanel) eventsPanel.hidden = !isDemo;
}
```

- [ ] **Step 5: 시연 버튼 핸들러 등록**

`DOMContentLoaded` 핸들러 내부 (`stationFilter.addEventListener` 부근)에 추가:

```javascript
var btnIn    = document.getElementById('btn-in');
var btnBoard = document.getElementById('btn-board');
var btnReset = document.getElementById('btn-reset');

if (btnIn) btnIn.addEventListener('click', async function() {
  await postDemoEvent('in');
  loadCrowdCount();
  loadEvents();
});
if (btnBoard) btnBoard.addEventListener('click', async function() {
  await postDemoEvent('board');
  loadCrowdCount();
  loadEvents();
});
if (btnReset) btnReset.addEventListener('click', async function() {
  if (!confirm('DEMO01 카운트를 모두 0으로 되돌립니다. counter.py도 Ctrl+C → 재실행해 주세요.')) return;
  await postDemoReset();
  loadCrowdCount();
  loadEvents();
});
```

- [ ] **Step 6: 폴링·표시 흐름 통합**

`DOMContentLoaded` 내부 초기화 블록(`loadCrowdCount(); setInterval(loadCrowdCount, CROWD_REFRESH_MS);`)을 다음으로 교체:

```javascript
applyDemoVisibility();
loadCrowdCount();
loadEvents();
setInterval(function() {
  loadCrowdCount();
  loadEvents();
}, CROWD_REFRESH_MS);
```

`stationFilter.addEventListener('change', loadCrowdCount)`도 다음으로 교체:

```javascript
stationFilter.addEventListener('change', function() {
  applyDemoVisibility();
  loadCrowdCount();
  loadEvents();
});
```

- [ ] **Step 7: 브라우저 통합 확인**

백엔드를 띄운 채로:

1. `http://localhost:5000/admin/` 접속
2. 정류장 필터 = **DEMO01** 선택 → 이벤트 피드 + 시연 제어 패널 표시 확인
3. `[🚶 IN +1]` 클릭 → 카드 IN/대기 녹색 플래시, 이벤트 피드 1건 표시, 2초 안에 반영
4. `[🚌 BOARD +1]` 클릭 → BOARD/대기 플래시, 피드 추가
5. `[↺ 리셋]` 클릭 → 확인창 → 0/0/0 복귀
6. 정류장 필터 INS01로 변경 → 두 패널 숨김 확인

- [ ] **Step 8: Commit**

```bash
git add frontend/admin/dashboard.js
git commit -m "feat(admin): 2초 폴링 + 카드 플래시 + 이벤트 피드 + 시연 제어 핸들러 (DEMO01 조건부)"
```

---

## Task 10: End-to-End 통합 검증

**Files:** 변경 없음 — 검증만.

- [ ] **Step 1: 전체 백엔드 테스트**

```bash
cd /home/ahble/projects/Capstone/bustago
python3 -m pytest backend/test_app.py -v
```

Expected: 모든 테스트 PASS (기존 + 신규 12건).

- [ ] **Step 2: 전체 hardware 테스트**

```bash
python3 -m pytest hardware/tests/ -v
```

Expected: 모든 테스트 PASS.

- [ ] **Step 3: 수동 cURL 시나리오 (스펙 §6.1)**

백엔드 띄운 상태에서:

```bash
# 0) 초기 리셋
curl -X POST http://localhost:5000/api/crowd-count/reset \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01"}'

# 1) IN +1
curl -X POST http://localhost:5000/api/crowd-count/event \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01","event_type":"in"}'
# 기대: count_in=1, current_waiting=1

# 2) BOARD +1
curl -X POST http://localhost:5000/api/crowd-count/event \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01","event_type":"board"}'
# 기대: count_in=1, count_board=1, current_waiting=0

# 3) 이벤트 피드 2건
curl "http://localhost:5000/api/crowd-count/recent?station_id=DEMO01&limit=5"
# 기대: events 배열에 board, in 순으로 2건

# 4) 리셋
curl -X POST http://localhost:5000/api/crowd-count/reset \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01"}'
# 기대: deleted_rows >= 2

# 5) 빈 상태 확인
curl "http://localhost:5000/api/crowd-count?station_id=DEMO01"
# 기대: 404 또는 빈 응답
```

- [ ] **Step 4: 브라우저 시각 검증 (스펙 §6.3 일부)**

브라우저로 `http://localhost:5000/admin/` → DEMO01 선택:

- [ ] 시연 제어 패널 + 이벤트 피드 패널 둘 다 표시
- [ ] `[IN +1]` 5회 클릭 → 카드 5/0/5, 피드 5건
- [ ] `[BOARD +1]` 5회 클릭 → 카드 5/5/0, 피드 최신 5건만(롤링)
- [ ] `[↺ 리셋]` → 0/0/0 복귀, 피드 비어있음
- [ ] 정류장 필터 → INS01 변경 시 두 패널 사라짐
- [ ] 정류장 필터 → DEMO01 복귀 시 두 패널 다시 표시

- [ ] **Step 5: 카메라 통합 검증 (Jetson 실기 — 옵션, D-1 리허설용)**

Jetson에서:

```bash
cd ~/bustago/hardware
python3 counter.py --camera 0 --model ~/bustago/yolo11n.engine \
    --server http://localhost:5000 \
    --station-id DEMO01 \
    --post-interval 10 \
    --debug
```

대시보드 띄운 노트북에서:

- [ ] 사람 1명이 카메라 앞 우→좌 통과 → **3초 이내** 카드 IN/대기 +1 + 이벤트 피드 슬라이드인
- [ ] 사람 1명이 다시 통과(BOARD 라인) → **3초 이내** 카드 BOARD/대기 변화 + 피드
- [ ] 60초 무이벤트 → "Jetson 연결됨" 유지 (heartbeat 동작 확인)

- [ ] **Step 6: 최종 푸시**

```bash
git push origin develop
```

Expected: `develop -> develop` 정상 푸시 메시지.

- [ ] **Step 7: 스펙·플랜 완료 표시 커밋**

`docs/PROGRESS.md` 또는 STATUS 파일이 있다면 시연 대시보드 구현 완료를 1줄 추가하고 커밋. 없으면 skip.

---

## 변경 파일 종합 (Quick reference)

| 파일 | 추가/수정 |
|------|-----------|
| `backend/schema.sql` | +3줄 (DEMO01 INSERT) |
| `backend/routes/crowd.py` | +10줄(헬퍼), +90줄(엔드포인트 3개) |
| `backend/test_app.py` | +12 테스트 |
| `hardware/counter.py` | +12줄 (`post_if_changed` + 메인 루프 1줄) |
| `hardware/tests/test_api_reporter.py` | 신규 +35줄 |
| `frontend/shared/api.js` | `fetchAPI` 시그니처 확장 + 3 함수 |
| `frontend/admin/index.html` | +25줄 (옵션 1줄 + 패널 2개) |
| `frontend/admin/style.css` | +50줄 (애니메이션 + 리스트 + 버튼) |
| `frontend/admin/dashboard.js` | +80줄 (헬퍼, loadEvents, 핸들러, 조건부) + 1줄 변경(폴링) |

## 시연 실행 (참고 — 구현 후)

스펙 §5 운영 절차 그대로:

```bash
# Jetson 터미널 1: 백엔드
cd ~/bustago && python3 -m backend.app

# Jetson 터미널 2: 카운터
cd ~/bustago/hardware && python3 counter.py --camera 0 \
    --model ~/bustago/yolo11n.engine --server http://localhost:5000 \
    --station-id DEMO01 --post-interval 10 --debug

# 노트북 브라우저
http://172.30.1.75:5000/admin/  → 정류장 필터 = DEMO01
```
