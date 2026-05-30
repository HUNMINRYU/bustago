# 시연용 카운팅 대시보드 설계 — 2026-05-30

> 한 명이 정류장에 들어와(IN) → 대기열에 잡히고 → 버스에 탑승(BOARD)하는 한 사이클이 관리자 대시보드에서 실시간으로 보이는 것이 시연 핵심 모먼트다.
> 본 스펙은 그 모먼트를 카메라 시연으로 안정적으로 보여주기 위해 필요한 백엔드·하드웨어·UI 변경을 정의한다.

## 0. 결정 요약 (브레인스토밍 결과)

| 결정 | 선택 |
|------|------|
| 시연 매체 | **하이브리드** — 실제 카메라 우선 + 대시보드 버튼 스크립트 백업 |
| 지연 전략 | **이벤트 기반** — counter.py 즉시 POST + 대시보드 2초 폴링 |
| 화면 표현 | **이벤트 피드 + 카드 애니메이션** 둘 다 |
| 데이터 격리 | **DEMO01 신규 정류장** + 대시보드 리셋 버튼 |
| 백업 트리거 | **대시보드 내 IN+1 / BOARD+1 / 리셋 버튼** |
| 리셋 메커니즘 | **DB 삭제 + counter.py 수동 재시작** (단순화) |

## 1. 시스템 아키텍처

```
[Jetson 카메라 + counter.py]                   [관리자 대시보드 백업 버튼]
    │  사람 라인 통과 감지                          │  운영자 클릭
    │  POST /api/crowd-count  (즉시, 누적값 전달)   │  POST /api/crowd-count/event
    │  station_id=DEMO01                           │  station_id=DEMO01, event_type
    ▼                                              ▼
              ┌──────────────────────────┐
              │  Flask 백엔드             │
              │  crowd_counts INSERT      │
              └──────────────────────────┘
                          │
                          │  GET /api/crowd-count + /recent  (2초 폴링)
                          ▼
              ┌──────────────────────────┐
              │  관리자 대시보드          │
              │  ① 카운팅 카드 + 애니메이션│
              │  ② 최근 이벤트 피드 (5건) │
              │  ③ 시연 제어 패널         │
              └──────────────────────────┘
                          │
                          │  POST /api/crowd-count/reset
                          ▼
              DELETE FROM crowd_counts WHERE station_id='DEMO01'
              (운영자가 별도로 counter.py Ctrl+C → 재실행)
```

### 1.1 핵심 원칙
- **단일 입력 경로 합류** — 카메라와 버튼 모두 동일한 `crowd_counts` 테이블에 INSERT. 대시보드는 출처를 구분하지 않음.
- **DEMO01 격리** — 실제 운영 데이터(INS01/GATE01)와 시연 데이터가 절대 섞이지 않음. 모든 시연 전용 엔드포인트는 `station_id='DEMO01'`만 화이트리스트.
- **리셋의 비대칭** — DB는 백엔드가 비우고, counter.py 메모리 카운터는 운영자가 재시작으로 비움. 자동 동기화 안 함 (복잡도 회피).

## 2. 백엔드 변경

### 2.1 스키마 (`backend/schema.sql`)
기존 광주 `INSERT IGNORE INTO stations` 블록에 1줄 추가.
```sql
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude) VALUES
('DEMO01', '시연용 정류장 (광주대)', 35.1378, 126.8942);
```
- 좌표는 INS01과 동일 (지도에서 같은 점에 찍힘 — 의도된 동작).
- Flask 재시작 시 `_init_sqlite_schema()`가 자동 반영.

### 2.2 신규 엔드포인트
3개 모두 `station_id='DEMO01'`만 허용. 다른 값은 400.

#### `POST /api/crowd-count/event` — 수동 이벤트 주입
```json
요청 : {"station_id": "DEMO01", "event_type": "in" | "board"}
응답 : {"status": "ok", "count_in": 3, "count_board": 2, "current_waiting": 1}
```
- 서버가 `crowd_counts`의 마지막 row를 읽어와 `event_type`에 따라 `count_in` 또는 `count_board` +1 한 새 row INSERT.
- `current_waiting = max(0, count_in - count_board)`.
- 마지막 row 없으면 0에서 시작.
- 빈 상태에서 `event_type="board"` → 400 ("대기 0인데 탑승 불가").
- Rate limit: 30/min.

#### `POST /api/crowd-count/reset` — DEMO01 카운트 초기화
```json
요청 : {"station_id": "DEMO01"}
응답 : {"status": "ok", "deleted_rows": 12}
```
- `DELETE FROM crowd_counts WHERE station_id='DEMO01'`.
- DEMO01 외 station_id → 400 (실수 방지).
- Rate limit: 5/min.

#### `GET /api/crowd-count/recent?station_id=DEMO01&limit=5` — 이벤트 피드
```json
응답 : {"events": [
  {"created_at": "18:04:38", "event_type": "board", "current_waiting": 0},
  {"created_at": "18:04:22", "event_type": "in",    "current_waiting": 1}
]}
```
- `crowd_counts`에서 station_id 마지막 N+1개 row 조회 (limit=5면 6개).
- 인접 row 쌍을 비교해 event_type 판정:
  - 새 row.count_in > 이전.count_in → `"in"`
  - 새 row.count_board > 이전.count_board → `"board"`
  - 동일 → `"tick"` (응답에서 제외)
- 결과는 최신순 정렬, limit=5면 최대 5건.
- Rate limit: 60/min.

### 2.3 기존 엔드포인트는 변경 없음
- `POST /api/crowd-count`: counter.py가 누적값 통째로 전달하는 기존 동작 유지. 변경 X.
- `GET /api/crowd-count?station_id=...`: 마지막 row 반환하는 기존 동작 유지. 변경 X.

## 3. `hardware/counter.py` 변경

### 3.1 `APIReporter` 클래스 — 이벤트 기반 POST 메서드 추가
```python
def __init__(self, ...):
    ...
    self._last_in = 0
    self._last_board = 0

def post_if_changed(self, counter) -> bool:
    """count_in 또는 count_board 가 직전 호출 이후 변하면 즉시 POST.

    Returns:
        True if POST sent, False otherwise.
    """
    if counter.count_in != self._last_in or counter.count_board != self._last_board:
        self._last_in = counter.count_in
        self._last_board = counter.count_board
        return self.post_now(counter)  # interval 무시하고 강제 전송
    return False
```

### 3.2 메인 루프 변경 — `counter.py:295` 부근
```python
# 기존
reporter.maybe_post(lc)

# 변경 후
reporter.post_if_changed(lc)   # 신규: 이벤트 발생 즉시 POST
reporter.maybe_post(lc)        # 유지: 10초 주기 heartbeat (Jetson 연결 상태 유지)
```

**heartbeat 유지 이유:** 이벤트 POST는 사람이 들어올 때만 발생. 사람이 안 들어오면 대시보드가 60초 무수신으로 "Jetson 미연결" 표시. 10초 heartbeat가 이를 방지.

### 3.3 시연 실행 명령
```bash
cd ~/bustago/hardware
python3 counter.py --camera 0 --model ~/bustago/yolo11n.engine \
    --server http://localhost:5000 \
    --station-id DEMO01 \
    --post-interval 10 \
    --debug
```

### 3.4 영향 범위
- 단일 파일 (`hardware/counter.py`), 추가 약 10줄.
- 기존 INS01 운영 모드와 호환 — `post_if_changed`는 변화 없으면 no-op.

## 4. 관리자 대시보드 변경

### 4.1 폴링 주기 변경 (`dashboard.js:26`)
```js
var CROWD_REFRESH_MS = 10000;   // → 2000
```

### 4.2 컴포넌트 ① — 카운팅 카드 애니메이션
기존 `cnt-waiting / cnt-in / cnt-board` 카드 숫자 변경 시 녹색 플래시 + 살짝 확대.

**JS 헬퍼:**
```js
function setCardValue(id, newVal) {
  var el = document.getElementById(id);
  if (el.textContent !== String(newVal)) {
    el.classList.add('flash');
    setTimeout(function() { el.classList.remove('flash'); }, 600);
  }
  el.textContent = newVal;
}
```

**CSS:**
```css
.counting-value.flash { animation: flashGreen 0.6s ease-out; }
@keyframes flashGreen {
  0%   { background: #4CAF50; color: white; transform: scale(1.15); }
  100% { background: transparent; color: #1976D2; transform: scale(1); }
}
```

### 4.3 컴포넌트 ② — 최근 이벤트 피드 패널
카운팅 패널 옆 신규 섹션, 최대 5건 롤링.

**HTML (`admin/index.html`):**
```html
<section class="panel events-panel" id="events-panel" hidden>
  <h2>최근 이벤트 <span class="live-badge">LIVE</span></h2>
  <ul id="events-list" class="events-list">
    <li class="events-empty">이벤트 대기 중...</li>
  </ul>
</section>
```

**JS — 신규 `loadEvents()`:**
- 2초마다 `GET /api/crowd-count/recent?station_id=DEMO01&limit=5`.
- 결과를 `<li>`로 렌더. 새 항목은 최상단에 slideInTop 애니메이션.
- 표시 형식: `18:04:22  🚶 IN +1  (대기 1명)` / `18:04:38  🚌 BOARD +1  (대기 0명)`.

### 4.4 컴포넌트 ③ — 시연 제어 패널 (DEMO01 전용)
**HTML:**
```html
<section class="panel demo-control-panel" id="demo-control-panel" hidden>
  <h2>시연 제어</h2>
  <div class="demo-buttons">
    <button id="btn-in"    class="demo-btn demo-in">🚶 IN +1</button>
    <button id="btn-board" class="demo-btn demo-board">🚌 BOARD +1</button>
    <button id="btn-reset" class="demo-btn demo-reset">↺ 리셋</button>
  </div>
  <p class="demo-hint">카메라가 사람을 놓쳤을 때 백업. DEMO01 전용.</p>
</section>
```

**JS 핸들러:**
```js
btnIn.addEventListener('click', async function() { 
  await postEvent('in'); 
  loadCrowdCount(); loadEvents();   // 즉시 갱신
});
btnBoard.addEventListener('click', async function() { 
  await postEvent('board'); 
  loadCrowdCount(); loadEvents();
});
btnReset.addEventListener('click', async function() {
  if (confirm('DEMO01 카운트를 모두 0으로 되돌립니다. counter.py도 재시작해 주세요.')) {
    await postReset();
    loadCrowdCount(); loadEvents();
  }
});
```

### 4.5 조건부 표시 — 정류장 필터 연동
정류장 필터에 `DEMO01` 옵션 추가. 선택 변경 시:
- DEMO01 → 시연 제어 + 이벤트 피드 패널 **표시**
- INS01/GATE01 → 두 패널 **숨김** (운영 화면 깔끔하게)

```js
function onStationChange() {
  var isDemo = (stationFilter.value === 'DEMO01');
  document.getElementById('demo-control-panel').hidden = !isDemo;
  document.getElementById('events-panel').hidden = !isDemo;
  loadCrowdCount();
  loadEvents();
}
```

### 4.6 `frontend/shared/api.js` — 신규 함수 + POST 지원
```js
async function postEvent(type) {
  return fetchAPI('/crowd-count/event', null, 'POST',
                  { station_id: 'DEMO01', event_type: type });
}
async function postReset() {
  return fetchAPI('/crowd-count/reset', null, 'POST',
                  { station_id: 'DEMO01' });
}
async function fetchRecentEvents(stationId, limit) {
  return fetchAPI('/crowd-count/recent',
                  { station_id: stationId, limit: limit || 5 });
}
```
기존 `fetchAPI` 시그니처 확장 — `method`, `body` 인자 추가 (POST/PUT 지원).

### 4.7 변경 파일 요약
| 파일 | 변경량 |
|------|--------|
| `frontend/admin/index.html` | +40줄 (패널 2개) |
| `frontend/admin/dashboard.js` | +80줄 (loadEvents, setCardValue, 핸들러, 조건부 표시) + 1줄 변경(폴링 주기) |
| `frontend/admin/style.css` | +50줄 (애니메이션, 리스트, 버튼) |
| `frontend/shared/api.js` | +15줄 (POST 지원, 신규 3함수) |

## 5. 시연 운영 절차 (Runbook)

### 5.1 시연 시작 전 (5분)
| 단계 | 위치 | 명령/액션 |
|------|------|-----------|
| 백엔드 기동 | Jetson | `cd ~/bustago && python3 -m backend.app` |
| DEMO01 확인 | Jetson | `sqlite3 ~/bustago/backend/bustago.db "SELECT ars_no FROM stations WHERE ars_no='DEMO01';"` → 1행 |
| 카운터 기동 | Jetson | (3.3 명령) |
| 대시보드 접속 | 노트북 | `http://172.30.1.75:5000/admin/` → 정류장 필터 **DEMO01** |
| 카메라 프레이밍 | Jetson debug 창 | IN/BOARD 세로 라인 위치 + 시연자 동선 일치 확인 |

### 5.2 시연 한 사이클 (약 20초)
```
t=0초   상태 0/0/0       대시보드 IN=0, BOARD=0, 대기=0
t=3초   시연자 우→좌 통과 카메라 IN 라인 감지
t=5초   대시보드 반응     IN +1 플래시, 대기 +1 플래시, 이벤트 피드 "🚶 IN +1"
t=8초   설명 멘트         "한 명이 도착, 시스템이 대기로 인식"
t=12초  시연자 다시 통과  BOARD 라인 감지
t=14초  대시보드 반응     BOARD +1 플래시, 대기 -1 플래시, 이벤트 피드 "🚌 BOARD +1"
t=17초  설명 멘트         "버스 탑승, 대기 0 복귀"
```

### 5.3 카메라 인식 실패 시
- 시연자 통과 후 카드 무반응 → 운영자가 즉시 대시보드 [🚶 IN +1] 클릭.
- 카드/피드 동일 반응. 청중 인지 불가.

### 5.4 반복 시연
- 그대로 다시 통과 → 카드 누적(IN=2, BOARD=2, 대기=0). 청중에게 자연스럽게 설명.
- 깔끔한 0/0/0 복귀 필요 시 §5.5.

### 5.5 깔끔한 리셋 (30초)
1. 대시보드 [↺ 리셋] 클릭 → 확인 → DB 비움
2. Jetson 터미널: `Ctrl+C` → `↑ Enter`
3. ~5초 후 카드 0/0/0 → 다음 시연 준비 완료

### 5.6 시연 종료
- Jetson: counter.py `Ctrl+C`. 백엔드는 유지.
- 대시보드: 정류장 필터 INS01로 복귀.

## 6. 검증 시나리오

### 6.1 End-to-End Happy Path (구현 직후 셀프 테스트)
```bash
# 1) DEMO01 정류장 존재
sqlite3 ~/bustago/backend/bustago.db "SELECT * FROM stations WHERE ars_no='DEMO01';"

# 2) IN 이벤트
curl -X POST http://localhost:5000/api/crowd-count/event \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01","event_type":"in"}'
# → {"status":"ok","count_in":1,"count_board":0,"current_waiting":1}

# 3) BOARD 이벤트
curl -X POST http://localhost:5000/api/crowd-count/event \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01","event_type":"board"}'
# → {"status":"ok","count_in":1,"count_board":1,"current_waiting":0}

# 4) 최근 이벤트 5건
curl "http://localhost:5000/api/crowd-count/recent?station_id=DEMO01&limit=5"
# → 2건 (board, in)

# 5) 리셋
curl -X POST http://localhost:5000/api/crowd-count/reset \
  -H "Content-Type: application/json" -d '{"station_id":"DEMO01"}'
# → {"status":"ok","deleted_rows":2}

# 6) 빈 상태
curl "http://localhost:5000/api/crowd-count?station_id=DEMO01"
# → 빈 응답 또는 null
```

### 6.2 엣지 케이스
| 케이스 | 기대 동작 |
|--------|-----------|
| 빈 상태에서 BOARD +1 | 400 "대기 0인데 탑승 불가" |
| INS01에 reset 호출 | 400 "DEMO01만 허용" |
| event_type="invalid" | 400 화이트리스트 위반 |
| 동시 POST + 버튼 클릭 race | 둘 다 INSERT, 다음 폴링에서 최신값 표시 |
| 백엔드 재시작 후 DEMO01 | 데이터 유지 (sqlite 영속) |

### 6.3 D-1 통합 리허설
- [ ] DEMO01 모드 카운터 5분, 사람 5회 통과 → 5/5/0 + 이벤트 5건
- [ ] 백업 버튼 IN/BOARD 각 3회 → 8/8/0
- [ ] 리셋 → 0/0/0, counter.py 재시작 → 0/0/0 유지
- [ ] 통과 → 화면 반영 **3초 이내**
- [ ] 60초 무이벤트 → "Jetson 연결됨" 유지(heartbeat 동작)

## 7. 변경 파일 목록 (구현 순서)

```
1. backend/schema.sql                            DEMO01 정류장 INSERT 1줄
2. backend/routes/crowd.py                       기존 `crowd_bp`에 신규 3 엔드포인트 (event/reset/recent)
3. backend/app.py                                변경 불필요 — `crowd_bp`는 line 53에서 이미 등록됨
4. hardware/counter.py                           APIReporter.post_if_changed + 메인루프 1줄
5. frontend/shared/api.js                        POST 지원 + 신규 3함수
6. frontend/admin/index.html                     이벤트 패널 + 시연 제어 패널 (hidden)
7. frontend/admin/dashboard.js                   폴링 2초, loadEvents, setCardValue, 핸들러, 조건부
8. frontend/admin/style.css                      flash 애니메이션, events-list, demo-btn
```

## 8. 스코프 외 (의도적 제외)

- **Jetson↔백엔드 양방향 통신**: 리셋 시 counter.py 자동 동기화 안 함. 운영자 재시작으로 단순화.
- **DEMO01 카메라 풀 이지** 외 정류장에서 시연 모드: 한 곳만 지원.
- **이벤트 영구 보존**: `crowd_counts`는 시연 중에만 의미. 리셋으로 전부 삭제 가능.
- **다중 시연자 동시 카운트 분석**: 통계·차트 추가 없음. 카드 + 피드만.
- **다국어 / 모바일 반응형**: 노트북 1280px 가로 기준만.

## 9. 리스크 & 완화

| 리스크 | 완화책 |
|--------|--------|
| counter.py 즉시 POST가 네트워크 지연으로 느림 | `requests.post(timeout=5)` 유지. 5초 이상 걸려도 메인 루프는 멈추지 않음 (별도 스레드 검토 — 단, 현재 동기 POST가 100ms 이내라 보류) |
| 동시 다발 이벤트 (5명 한 번에 통과) | 각 이벤트별 POST 누적. 큐가 쌓이면 다음 frame에서 한꺼번에 push (DeepSORT 처리량 의존). 시연은 1명 시나리오라 무영향 |
| 대시보드 2초 폴링 트래픽 | localhost 통신, 시연 1시간 = 1800 요청. Flask-Limiter 60/min로 안전 |
| 시연자가 라인을 비스듬히 통과 | 운영자가 즉시 백업 버튼. 청중 인지 불가 |
| DB 동시 INSERT (counter + 버튼) | sqlite 직렬화로 safe. row 순서는 timestamp로 확인 가능 |
| 리셋 후 counter.py 재시작 실패 | 운영자 절차서 §5.5 — `Ctrl+C → ↑ Enter`로 표준화 |
