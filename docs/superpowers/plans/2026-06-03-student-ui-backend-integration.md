# 학생용 새 UI ⇄ 실제 백엔드 연결 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 루트 `student/`의 폴리시드 PWA 디자인을 `frontend/student/`에 이식하고 실제 백엔드(`shared/api.js`)에 연결한다.

**Architecture:** 새 UI는 뷰 계층. `data.js` 어댑터 하나가 백엔드 응답을 뷰모델로 변환하며 `fetch`를 아는 유일한 곳이다. `app.js`는 `data.js`만 호출한다. 백엔드·nginx·admin 미변경.

**Tech Stack:** Vanilla JS(ES5 호환 스타일, 기존 코드 관례 따름), Flask 백엔드(무변경), nginx 정적 서빙, Node(순수 매퍼 단위 테스트용), docker-compose(수동 통합 검증).

설계 문서: `docs/superpowers/specs/2026-06-03-student-ui-backend-integration-design.md`

---

## 파일 구조

| 파일 | 책임 | 상태 |
|---|---|---|
| `frontend/student/index.html` | 새 탭형 마크업, script 로딩 순서 | 교체(Task 1) |
| `frontend/student/style.css` | 새 폴리시드 스타일 | 교체(Task 1) |
| `frontend/student/manifest.json` | PWA 매니페스트 | 교체(Task 1) |
| `frontend/student/service-worker.js` | 오프라인 캐시, 버전 bump | 교체(Task 1) |
| `frontend/student/data.js` | **[신규]** 어댑터: 순수 매퍼 + async 페처 | 생성(Task 2,3) |
| `frontend/student/app.js` | UI 로직, `data.js`만 호출 | 교체+수정(Task 1,4,5,6) |
| `frontend/student/data.test.js` | **[신규]** 순수 매퍼 Node 테스트 | 생성(Task 2) |
| `frontend/shared/api.js` | API 래퍼 | 재사용(무변경) |
| `archive/student-design-ref/` | 루트 student/ 보관 | 이동(Task 6) |

**테스트 전략:** JS 러너 미설치. `data.js`의 순수 매퍼(입력 JSON→뷰모델)는 `module.exports`로 노출해 **Node(`node --test`)로 단위 테스트**한다. async 페처와 DOM 로직은 docker-compose 수동 스모크로 검증한다.

---

## 백엔드 응답 형태 (매퍼 입력 — 검증된 실제 shape)

```js
// fetchStations() → 배열
[{ ars_no:"INS01", station_name:"인성관", latitude, longitude, gj_busstop_id:1981 }, ...]

// fetchRouteRecommend(station,hour,weekday,dest) → { ..., routes:[ ... ] }
{ station_id, hour, weekday, routes:[
  { route_no:"songjeong-51", route_name:"송정51", end_stations:["광주역"],
    congestion:{ level:1, label:"보통", ... }, recommended:false }, ... ] }

// fetchPredict(station,hour,weekday) → { prediction, recommendation, next_hour_prediction }
{ prediction:{ level:1, label:"보통" }, recommendation:"...", next_hour_prediction:{level,label} }

// fetchBusArrival(gj_busstop_id) → { items:[...] }  (raw 광주 BIS 필드)
{ items:[ { LINE_ID:1234, LINE_NAME, SHORT_LINE_NAME, REMAIN_MIN:"3",
            REMAIN_STOP:"2", ARRIVE_FLAG:0, LOW_BUS:1, DIR_END:"광주역" }, ... ] }

// fetchBusLocation(line_id) → { line_id, items:[...], count:N }
{ line_id:1234, items:[...], count:3 }
```

> `shared/api.js`의 모든 래퍼는 실패 시 `null` 반환. `fetchAPI`는 `data.data`가 있으면 그것을, 없으면 전체 객체를 반환한다. 따라서 `fetchRouteRecommend(...)`는 `{station_id,...,routes}` 형태를 직접 반환한다.

---

### Task 1: 새 디자인을 frontend/student로 이식 (mock 유지 상태로 우선 서빙)

목표: 새 UI가 nginx에서 그대로 뜨게 한다. 아직 mock 데이터. 이 시점에 동작하는 소프트웨어 확보.

**Files:**
- Modify(교체): `frontend/student/index.html`
- Modify(교체): `frontend/student/style.css`
- Modify(교체): `frontend/student/manifest.json`
- Modify(교체): `frontend/student/service-worker.js`
- Modify(교체): `frontend/student/app.js`

- [ ] **Step 1: 루트 student/ 파일을 frontend/student로 복사**

Run:
```bash
cd /home/ahble/projects/Capstone/bustago
cp student/style.css      frontend/student/style.css
cp student/manifest.json  frontend/student/manifest.json
cp student/service-worker.js frontend/student/service-worker.js
cp student/index.html     frontend/student/index.html
cp student/app.js         frontend/student/app.js
```

- [ ] **Step 2: index.html 에서 날씨 카드 제거**

`frontend/student/index.html` 의 즐겨찾기 패널 안 `<div class="weather-card card"> ... </div>` 블록(아래 전체)을 삭제한다:

```html
      <div class="weather-card card">
        <div class="weather-left">
          <span class="weather-ico">☀️</span>
          <span class="weather-temp">22°C</span>
        </div>
        <div class="weather-right">
          <div><div class="v">55%</div><div class="l">습도</div></div>
          <div><div class="v">2m/s</div><div class="l">바람</div></div>
          <div><div class="v">없음</div><div class="l">강수</div></div>
        </div>
      </div>
```

삭제 후 `<section class="tab-panel active" data-panel="fav">` 의 첫 자식은 `<div class="fav-list" id="favList"></div>` 가 된다.

- [ ] **Step 3: index.html script 태그에 shared/api.js와 data.js 추가**

`frontend/student/index.html` 마지막의 `<script src="app.js"></script>` 한 줄을 아래 3줄로 교체:

```html
  <script src="../shared/api.js"></script>
  <script src="data.js"></script>
  <script src="app.js"></script>
```

- [ ] **Step 4: service-worker.js 캐시 버전 bump + 자산 목록 갱신**

`frontend/student/service-worker.js` 상단 두 부분을 교체:

```js
const CACHE = 'bustago-v2';

const ASSETS = [
  'index.html',
  'style.css',
  'app.js',
  'data.js',
  '../shared/api.js',
  'manifest.json',
];
```

- [ ] **Step 5: data.js 빈 스텁 생성 (로딩 에러 방지)**

Create `frontend/student/data.js`:

```js
// BUSTAGO Student - 데이터 어댑터 (스텁; Task 2,3에서 구현)
// 백엔드 응답을 UI 뷰모델로 변환하는 유일한 계층.
```

- [ ] **Step 6: docker-compose로 화면 로딩 수동 검증**

Run:
```bash
cd /home/ahble/projects/Capstone/bustago
docker-compose up -d --build
```
브라우저로 `http://localhost` 접속.
Expected: 새 탭형 UI(즐겨찾기/노선검색/더보기)가 뜨고, 노선 검색 탭에 mock 노선 5개가 보인다. 날씨 카드는 없다. 콘솔에 404(data.js/api.js) 없음.

- [ ] **Step 7: Commit**

```bash
git add frontend/student/
git commit -m "feat(student): 새 폴리시드 UI를 frontend/student로 이식 (날씨카드 제거, mock 유지)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: data.js 순수 매퍼 + Node 단위 테스트 (TDD)

목표: 백엔드 JSON → 뷰모델 변환 함수들을 순수 함수로 만들고 Node로 테스트.

**Files:**
- Modify: `frontend/student/data.js`
- Create: `frontend/student/data.test.js`

- [ ] **Step 1: 실패하는 테스트 작성**

Create `frontend/student/data.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert');
const D = require('./data.js');

test('makeFavId: 정류장+노선 쌍 키 생성', () => {
  assert.strictEqual(D.makeFavId('INS01', '송정51'), 'INS01::송정51');
});

test('deriveBusType: 기본 normal', () => {
  assert.strictEqual(D.deriveBusType('송정51', null), 'normal');
});
test('deriveBusType: 좌석/급행 → express', () => {
  assert.strictEqual(D.deriveBusType('좌석02', null), 'express');
  assert.strictEqual(D.deriveBusType('급행3', null), 'express');
});
test('deriveBusType: 도착항목 LOW_BUS=1 → low', () => {
  assert.strictEqual(D.deriveBusType('송정51', { LOW_BUS: 1 }), 'low');
});

test('mapRoutesToCards: route-recommend → 카드 뷰모델', () => {
  const resp = { routes: [
    { route_no: 'r1', route_name: '송정51', end_stations: ['광주역'],
      congestion: { level: 1 }, recommended: true },
  ]};
  const cards = D.mapRoutesToCards(resp, 'INS01', '인성관');
  assert.strictEqual(cards.length, 1);
  assert.deepStrictEqual(cards[0], {
    id: 'INS01::송정51', stationId: 'INS01', stationName: '인성관',
    name: '송정51', routeNo: 'r1', from: '인성관', to: '광주역',
    level: 1, type: 'normal', recommended: true,
  });
});
test('mapRoutesToCards: null/빈 응답 → []', () => {
  assert.deepStrictEqual(D.mapRoutesToCards(null, 'INS01', 'X'), []);
  assert.deepStrictEqual(D.mapRoutesToCards({ routes: [] }, 'INS01', 'X'), []);
});

test('mapStations: 광주 우선 정렬 + busstop 맵', () => {
  const data = [
    { ars_no: '111', station_name: '서울역', gj_busstop_id: null },
    { ars_no: 'INS01', station_name: '인성관', gj_busstop_id: 1981 },
  ];
  const r = D.mapStations(data);
  assert.strictEqual(r.stations[0].ars_no, 'INS01'); // 광주 먼저
  assert.strictEqual(r.busstopMap['INS01'], 1981);
});

test('mapArrivalsForRoute: 노선명 매칭 + 분 오름차순 + 6개 제한', () => {
  const items = [
    { SHORT_LINE_NAME: '송정51', REMAIN_MIN: '7', REMAIN_STOP: '4', LOW_BUS: 0, DIR_END: '광주역', LINE_ID: 9 },
    { SHORT_LINE_NAME: '송정51', REMAIN_MIN: '3', REMAIN_STOP: '2', LOW_BUS: 1, DIR_END: '광주역', LINE_ID: 9 },
    { SHORT_LINE_NAME: '첨단18', REMAIN_MIN: '1', REMAIN_STOP: '1', LOW_BUS: 0, DIR_END: '전남대', LINE_ID: 8 },
  ];
  const r = D.mapArrivalsForRoute(items, '송정51');
  assert.strictEqual(r.length, 2);
  assert.strictEqual(r[0].min, 3);      // 가까운 것 먼저
  assert.strictEqual(r[0].low, true);
  assert.strictEqual(r[0].lineId, 9);
});

test('mapPredictsToForecast: predict 결과 배열 → 막대 데이터', () => {
  const preds = [
    { prediction: { level: 1 } }, null, { prediction: { level: 3 } },
  ];
  const r = D.mapPredictsToForecast(preds, 8); // 시작시각 8시
  assert.deepStrictEqual(r.hours, [8, 9, 10]);
  assert.strictEqual(r.levels[0], 1);
  assert.strictEqual(r.levels[2], 3);
  assert.ok(typeof r.levels[1] === 'number'); // null은 데모값으로 채움
});
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd frontend/student && node --test data.test.js`
Expected: FAIL — `D.makeFavId is not a function` 등 (data.js가 아직 스텁).

- [ ] **Step 3: data.js에 순수 매퍼 구현**

`frontend/student/data.js` 를 아래로 교체:

```js
// BUSTAGO Student - 데이터 어댑터
// 백엔드 응답을 UI 뷰모델로 변환하는 유일한 계층.
// 순수 매퍼(아래)는 Node 테스트 대상이며 브라우저 전역에 의존하지 않는다.

// 혼잡도 데모 폴백 — 시간대 기반 추정 (API 실패 시 사용)
function demoLevel(hour) {
  if ((hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)) return 3;
  if (hour >= 10 && hour <= 16) return 1;
  return 0;
}

// 즐겨찾기 키 = 정류장+노선 쌍
function makeFavId(stationId, routeName) {
  return stationId + '::' + routeName;
}

// 버스 유형 추론: 도착항목 LOW_BUS 우선, 다음 노선명 패턴, 기본 normal
function deriveBusType(routeName, arrivalItem) {
  if (arrivalItem && Number(arrivalItem.LOW_BUS) === 1) return 'low';
  if (/좌석|급행/.test(routeName || '')) return 'express';
  return 'normal';
}

// route-recommend 응답 → 노선 카드 뷰모델 배열
function mapRoutesToCards(resp, stationId, stationName) {
  if (!resp || !Array.isArray(resp.routes)) return [];
  return resp.routes.map(function (r) {
    return {
      id: makeFavId(stationId, r.route_name),
      stationId: stationId,
      stationName: stationName,
      name: r.route_name,
      routeNo: r.route_no,
      from: stationName,
      to: (r.end_stations || []).join('/'),
      level: (r.congestion && typeof r.congestion.level === 'number') ? r.congestion.level : 0,
      type: deriveBusType(r.route_name, null),
      recommended: !!r.recommended,
    };
  });
}

// stations 응답 → { stations(광주 우선 정렬), busstopMap }
function mapStations(data) {
  if (!Array.isArray(data)) return { stations: [], busstopMap: {} };
  var stations = data.slice().sort(function (a, b) {
    var aGJ = /^(INS|GATE|GJ)/.test(a.ars_no) ? 0 : 1;
    var bGJ = /^(INS|GATE|GJ)/.test(b.ars_no) ? 0 : 1;
    return aGJ - bGJ;
  });
  var busstopMap = {};
  stations.forEach(function (s) {
    if (s.gj_busstop_id) busstopMap[s.ars_no] = s.gj_busstop_id;
  });
  return { stations: stations, busstopMap: busstopMap };
}

// BIS 도착 items → 특정 노선의 도착 뷰모델 (분 오름차순, 최대 6개)
function mapArrivalsForRoute(items, routeName) {
  if (!Array.isArray(items)) return [];
  return items
    .filter(function (it) {
      var nm = it.SHORT_LINE_NAME || it.LINE_NAME || '';
      return nm === routeName;
    })
    .map(function (it) {
      return {
        lineId: it.LINE_ID != null ? Number(it.LINE_ID) : null,
        lineName: it.SHORT_LINE_NAME || it.LINE_NAME || routeName,
        min: parseInt(it.REMAIN_MIN, 10) || 0,
        stops: parseInt(it.REMAIN_STOP, 10) || 0,
        low: Number(it.LOW_BUS) === 1,
        imminent: Number(it.ARRIVE_FLAG) === 1,
        dirEnd: it.DIR_END || '',
      };
    })
    .sort(function (a, b) { return a.min - b.min; })
    .slice(0, 6);
}

// predict 결과 배열(6개) → 막대 그래프 데이터 (null은 데모값)
function mapPredictsToForecast(preds, startHour) {
  var hours = [], levels = [];
  for (var i = 0; i < preds.length; i++) {
    var h = (startHour + i) % 24;
    hours.push(h);
    var p = preds[i];
    levels.push((p && p.prediction && typeof p.prediction.level === 'number')
      ? p.prediction.level : demoLevel(h));
  }
  return { hours: hours, levels: levels };
}

// Node 테스트용 export (브라우저에서는 무시됨)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    demoLevel: demoLevel,
    makeFavId: makeFavId,
    deriveBusType: deriveBusType,
    mapRoutesToCards: mapRoutesToCards,
    mapStations: mapStations,
    mapArrivalsForRoute: mapArrivalsForRoute,
    mapPredictsToForecast: mapPredictsToForecast,
  };
}
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

Run: `cd frontend/student && node --test data.test.js`
Expected: PASS (모든 테스트 통과, `# pass 9` 류 출력).

- [ ] **Step 5: Commit**

```bash
git add frontend/student/data.js frontend/student/data.test.js
git commit -m "feat(student): data.js 순수 매퍼 + Node 단위 테스트 (route/station/arrival/forecast)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: data.js async 페처 (shared/api.js 래핑)

목표: 매퍼 위에 실제 API를 호출하는 async 함수를 얹는다. 브라우저 전역(`fetchStations` 등) 사용.

**Files:**
- Modify: `frontend/student/data.js`

- [ ] **Step 1: async 페처를 data.js 끝(export 블록 앞)에 추가**

`frontend/student/data.js` 의 `// Node 테스트용 export` 주석 **바로 위**에 아래를 삽입:

```js
// =============================================================
// async 페처 — shared/api.js 전역 함수를 호출 (브라우저 전용)
// =============================================================

// 정류장 목록 로드 (정렬됨) + busstopMap. 실패 시 빈 셋.
async function loadStations() {
  var data = await fetchStations();           // shared/api.js
  return mapStations(data);
}

// 특정 정류장의 현재 시각 노선 카드. 실패 시 [].
async function loadRoutesForStation(stationId, stationName) {
  var now = new Date();
  var hour = now.getHours();
  var jsDay = now.getDay();
  var weekday = jsDay === 0 ? 6 : jsDay - 1;   // 0=월
  var resp = await fetchRouteRecommend(stationId, hour, weekday);
  return mapRoutesToCards(resp, stationId, stationName);
}

// 노선 시트용 시간대별 예측(다음 6시간, 정류장 단위). 실패분은 데모값.
async function loadForecast(stationId) {
  var now = new Date();
  var startHour = now.getHours();
  var jsDay = now.getDay();
  var weekday = jsDay === 0 ? 6 : jsDay - 1;
  var promises = [];
  for (var i = 0; i < 6; i++) {
    promises.push(fetchPredict(stationId, (startHour + i) % 24, weekday));
  }
  var preds = await Promise.all(promises);
  return mapPredictsToForecast(preds, startHour);
}

// 노선 시트용 도착 + 운행 대수. busstopId 없으면 빈 결과.
// 반환: { arrivals:[...], runningCount:Number|null }
async function loadArrivalAndRunning(busstopId, routeName) {
  if (!busstopId) return { arrivals: [], runningCount: null };
  var data = await fetchBusArrival(busstopId);
  var items = (data && data.items) ? data.items : [];
  var arrivals = mapArrivalsForRoute(items, routeName);

  var runningCount = null;
  var lineId = arrivals.length ? arrivals[0].lineId : null;
  if (lineId != null) {
    var loc = await fetchBusLocation(lineId);
    if (loc && typeof loc.count === 'number') runningCount = loc.count;
  }
  return { arrivals: arrivals, runningCount: runningCount };
}
```

- [ ] **Step 2: 페처도 export에 추가**

`module.exports = { ... }` 객체 안에 아래 줄들을 추가(매퍼 export 뒤):

```js
    loadStations: typeof fetchStations !== 'undefined' ? loadStations : undefined,
    loadRoutesForStation: typeof fetchRouteRecommend !== 'undefined' ? loadRoutesForStation : undefined,
    loadForecast: typeof fetchPredict !== 'undefined' ? loadForecast : undefined,
    loadArrivalAndRunning: typeof fetchBusArrival !== 'undefined' ? loadArrivalAndRunning : undefined,
```

> 비고: Node 환경에는 `fetchStations` 등 전역이 없어 `undefined`로 export되지만, async 페처는 Node 테스트 대상이 아니므로 문제 없다. 매퍼 테스트(Task 2)는 그대로 통과한다.

- [ ] **Step 3: 매퍼 테스트가 여전히 통과하는지 확인 (회귀)**

Run: `cd frontend/student && node --test data.test.js`
Expected: PASS (Task 2와 동일, 깨지지 않음).

- [ ] **Step 4: Commit**

```bash
git add frontend/student/data.js
git commit -m "feat(student): data.js async 페처 (stations/routes/forecast/arrival+running)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: app.js — 즐겨찾기/검색 탭을 실데이터로 (mock 제거)

목표: `MOCK_ROUTES` 제거. 정류장-우선 검색 흐름과 (정류장+노선) 즐겨찾기 구현.

**Files:**
- Modify: `frontend/student/app.js`
- Modify: `frontend/student/index.html` (검색 탭에 정류장 컨텍스트 칩 추가)

- [ ] **Step 1: index.html 검색 패널에 정류장 컨텍스트 칩 추가**

`frontend/student/index.html` 의 `<section class="tab-panel" data-panel="search">` 안,
`<input ... id="searchInput" ...>` **바로 아래**에 추가:

```html
      <div class="station-ctx" id="stationCtx" hidden>
        <button class="station-ctx-btn" id="stationCtxBtn">← 정류장 변경</button>
        <span class="station-ctx-name" id="stationCtxName"></span>
      </div>
      <div class="station-list" id="stationList"></div>
```

그리고 검색 input 의 placeholder를 정류장 검색용으로 변경:
`placeholder="정류장 이름으로 검색 (예: 인성관)"`

- [ ] **Step 2: app.js 의 mock/상수/상태 교체**

`frontend/student/app.js` 상단의 `MOCK_ROUTES` 상수 블록 전체(주석 포함, `const MOCK_ROUTES = [ ... ];`)를 삭제하고, `FORECAST_HOURS/FORECAST_LEVELS/CURRENT_HOUR_IDX` 상수 블록도 삭제한다(시트에서 동적 로드로 대체).

`state` 객체를 아래로 교체:

```js
const state = {
  tab: 'fav',
  query: '',
  stations: [],            // 정렬된 정류장 목록
  busstopMap: {},          // ars_no → gj_busstop_id
  activeStation: null,     // { ars_no, station_name }
  routeCards: [],          // 현재 activeStation의 노선 카드 (검색 탭)
  favs: new Map(JSON.parse(localStorage.getItem('bustago_favs_v2') || '[]')), // id → fav객체
  sheetRoute: null,
  sheetOpen: false,
  closing: false,
  reopenTimer: null,
  arrivalTimer: null,      // 시트 도착 30초 갱신
  theme: localStorage.getItem('bustago_theme') || 'light',
};
```

> `bustago_favs_v2`는 `[[id, favObj], ...]` 형태(Map 직렬화). 구버전 `bustago_favs`(문자열 배열)는 무시 → 즐겨찾기 초기화(시연 영향 없음, 설계서 §10).

- [ ] **Step 3: DOM 캐시에 신규 요소 추가**

`const searchCountEl = $('searchCount');` 줄 아래에 추가:

```js
const stationListEl  = $('stationList');
const stationCtxEl   = $('stationCtx');
const stationCtxBtn  = $('stationCtxBtn');
const stationCtxName = $('stationCtxName');
```

- [ ] **Step 4: 부트스트랩을 async 초기화로 교체**

`renderFavs(); renderRouteList();` 를 호출하던 부트스트랩 블록을 아래로 교체:

```js
document.body.setAttribute('data-theme', state.theme);
updateThemeUI();

(async function init() {
  var r = await Data.loadStations();
  state.stations = r.stations;
  state.busstopMap = r.busstopMap;
  // 기본 정류장: INS01 → 첫 광주 → 첫 번째
  state.activeStation =
    state.stations.find(function (s) { return s.ars_no === 'INS01'; }) ||
    state.stations.find(function (s) { return /^(GATE|GJ)/.test(s.ars_no); }) ||
    state.stations[0] || null;
  if (state.activeStation) {
    state.routeCards = await Data.loadRoutesForStation(
      state.activeStation.ars_no, state.activeStation.station_name);
  }
  renderFavs();
  renderStationContext();
  renderSearchResults();
})();
```

> `Data`는 전역. data.js 끝에 브라우저 전역 노출을 추가해야 한다 → Step 5.

- [ ] **Step 5: data.js 에 브라우저 전역 `Data` 노출**

`frontend/student/data.js` 의 `if (typeof module ...)` 블록 **위**에 추가:

```js
// 브라우저 전역으로 노출 (app.js가 Data.* 로 호출)
if (typeof window !== 'undefined') {
  window.Data = {
    demoLevel: demoLevel, makeFavId: makeFavId, deriveBusType: deriveBusType,
    mapRoutesToCards: mapRoutesToCards, mapStations: mapStations,
    mapArrivalsForRoute: mapArrivalsForRoute, mapPredictsToForecast: mapPredictsToForecast,
    loadStations: loadStations, loadRoutesForStation: loadRoutesForStation,
    loadForecast: loadForecast, loadArrivalAndRunning: loadArrivalAndRunning,
  };
}
```

- [ ] **Step 6: 검색/렌더 함수 교체**

`filterRoutes()`, `renderRouteList()`, `renderFavs()` 와 검색 input 리스너를 아래로 교체:

```js
// 검색 input: 정류장 검색 (activeStation 미선택 상태에서) 또는 노선 필터
searchInput.addEventListener('input', (e) => {
  state.query = e.target.value;
  renderSearchResults();
});

// 정류장 변경 버튼: 노선 목록 → 정류장 검색 모드로
stationCtxBtn.addEventListener('click', () => {
  state.activeStation = null;
  state.routeCards = [];
  renderStationContext();
  renderSearchResults();
});

// 검색 탭 렌더: activeStation 있으면 노선 카드, 없으면 정류장 목록
function renderSearchResults() {
  if (state.activeStation) {
    stationListEl.innerHTML = '';
    const q = state.query.trim().toLowerCase();
    const routes = !q ? state.routeCards : state.routeCards.filter((r) =>
      r.name.toLowerCase().includes(q) || r.to.toLowerCase().includes(q));
    searchCountEl.textContent = routes.length;
    routeListEl.innerHTML = routes.map(routeCardHTML).join('');
    bindRouteCards(routeListEl);
  } else {
    routeListEl.innerHTML = '';
    const q = state.query.trim().toLowerCase();
    const list = !q ? state.stations : state.stations.filter((s) =>
      (s.station_name || '').toLowerCase().includes(q) ||
      (s.ars_no || '').toLowerCase().includes(q));
    searchCountEl.textContent = list.length;
    stationListEl.innerHTML = list.map(stationItemHTML).join('');
    bindStationItems();
  }
}

// 정류장 컨텍스트 칩 표시/숨김
function renderStationContext() {
  if (state.activeStation) {
    stationCtxEl.hidden = false;
    stationCtxName.textContent = state.activeStation.station_name;
  } else {
    stationCtxEl.hidden = true;
  }
}

// 정류장 한 줄 HTML
function stationItemHTML(s) {
  return '<div class="station-item card" role="button" tabindex="0" data-ars="' + s.ars_no + '">' +
    '<span class="si-name">' + s.station_name + '</span>' +
    '<span class="si-chev">›</span></div>';
}

// 정류장 선택 → 그 정류장 노선 로드
function bindStationItems() {
  stationListEl.querySelectorAll('.station-item').forEach((el) => {
    el.addEventListener('click', async () => {
      const s = state.stations.find((x) => x.ars_no === el.dataset.ars);
      if (!s) return;
      state.activeStation = s;
      state.query = '';
      searchInput.value = '';
      state.routeCards = await Data.loadRoutesForStation(s.ars_no, s.station_name);
      renderStationContext();
      renderSearchResults();
    });
  });
}

// 즐겨찾기 탭: 저장된 (정류장,노선) 쌍을 정류장별 그룹핑하여 실시간 혼잡도 로드
async function renderFavs() {
  const favArr = [...state.favs.values()];
  favEmptyEl.classList.toggle('show', favArr.length === 0);
  if (favArr.length === 0) { favListEl.innerHTML = ''; return; }

  // 정류장별 그룹핑 → 정류장당 1회 route-recommend
  const byStation = {};
  favArr.forEach((f) => {
    (byStation[f.stationId] = byStation[f.stationId] || { name: f.stationName, favs: [] }).favs.push(f);
  });
  const cards = [];
  for (const sid of Object.keys(byStation)) {
    const live = await Data.loadRoutesForStation(sid, byStation[sid].name);
    byStation[sid].favs.forEach((f) => {
      const match = live.find((c) => c.name === f.routeName);
      cards.push(match || {  // 매칭 실패 시 데모 레벨로 카드 유지
        id: f.id, stationId: f.stationId, stationName: f.stationName,
        name: f.routeName, routeNo: f.routeNo, from: f.stationName, to: '-',
        level: Data.demoLevel(new Date().getHours()), type: 'normal', recommended: false,
      });
    });
  }
  favListEl.innerHTML = cards.map(routeCardHTML).join('');
  bindRouteCards(favListEl);
}
```

- [ ] **Step 7: 즐겨찾기 토글을 Map(쌍) 기반으로 교체**

기존 `toggleFav(id)` 함수와 `routeCardHTML`의 즐겨찾기 판정(`state.favIds.has`)을 교체.

`routeCardHTML` 안의 `const isFav = state.favIds.has(r.id);` 를:
```js
  const isFav = state.favs.has(r.id);
```

`toggleFav` 함수를 아래로 교체(인자를 카드 객체 `r`로 받음):
```js
function toggleFav(r) {
  if (state.favs.has(r.id)) state.favs.delete(r.id);
  else state.favs.set(r.id, {
    id: r.id, stationId: r.stationId, stationName: r.stationName,
    routeName: r.name, routeNo: r.routeNo,
  });
  localStorage.setItem('bustago_favs_v2', JSON.stringify([...state.favs]));
  renderFavs();
  renderSearchResults();
  if (state.sheetRoute && state.sheetRoute.id === r.id) updateSheetFavBtn();
}
```

`bindRouteCards`의 별(`.rc-fav`) 클릭 핸들러를 카드 객체 전달로 수정:
```js
  root.querySelectorAll('.rc-fav').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const r = findCardById(btn.dataset.fav);
      if (r) toggleFav(r);
    });
  });
```

`bindRouteCards`의 카드 클릭 핸들러도 `findCardById` 사용:
```js
    card.addEventListener('click', (e) => {
      if (e.target.closest('.rc-fav')) return;
      const r = findCardById(card.dataset.id);
      if (r) openRoute(r);
    });
```

그리고 헬퍼 추가(파일 내 카드 검색):
```js
// 현재 화면에 존재하는 카드 객체를 id로 찾음 (검색 결과 또는 즐겨찾기)
function findCardById(id) {
  return state.routeCards.find((c) => c.id === id)
      || [...state.favs.values()].map(favToCardStub).find((c) => c.id === id);
}
function favToCardStub(f) {
  return { id: f.id, stationId: f.stationId, stationName: f.stationName,
           name: f.routeName, routeNo: f.routeNo, from: f.stationName, to: '-',
           level: 0, type: 'normal', recommended: false };
}
```

`sheetFavBtn` 클릭 핸들러도 교체:
```js
sheetFavBtn.addEventListener('click', () => {
  if (state.sheetRoute) toggleFav(state.sheetRoute);
});
```

- [ ] **Step 8: 검색 탭 정류장 목록/칩 스타일 추가**

`frontend/student/style.css` 끝에 추가:

```css
/* 정류장 검색 결과 / 컨텍스트 칩 */
.station-ctx { display:flex; align-items:center; gap:8px; margin:4px 0 10px; }
.station-ctx-btn { background:var(--search-count-bg); color:var(--search-count-fg);
  border:none; border-radius:999px; padding:6px 12px; font-size:13px; cursor:pointer; }
.station-ctx-name { font-weight:700; color:var(--text-primary); }
.station-list { display:flex; flex-direction:column; gap:8px; }
.station-item { display:flex; justify-content:space-between; align-items:center;
  padding:14px 16px; cursor:pointer; }
.si-name { color:var(--text-primary); font-weight:500; }
.si-chev { color:var(--text-muted); font-size:18px; }
```

- [ ] **Step 9: docker-compose 수동 스모크**

Run: `docker-compose up -d --build` → `http://localhost`
Expected:
- 노선 검색 탭: 처음엔 정류장 목록(광주 먼저). 검색창에 "인성관" → 필터됨.
- 정류장 누름 → 그 정류장 노선 카드 표시, "← 정류장 변경" 칩 표시.
- 노선 카드의 ☆ 누름 → ★ 토글, 즐겨찾기 탭에 표시. 새로고침해도 유지.
- 즐겨찾기 비었을 때 empty-state 표시.

- [ ] **Step 10: Commit**

```bash
git add frontend/student/
git commit -m "feat(student): 정류장-우선 검색 + (정류장,노선) 즐겨찾기 실데이터 연결 (mock 제거)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: app.js — 노선 상세 시트 실데이터 (혼잡도/예측/도착/운행대수)

목표: 시트의 정적/mock 영역을 실제 데이터로. 30초 도착 갱신. 트랙 A안.

**Files:**
- Modify: `frontend/student/app.js`
- Modify: `frontend/student/index.html` (시트 트랙 마크업 단순화)

- [ ] **Step 1: index.html 시트의 정류장 트랙을 2점+운행칩 구조로 교체**

`frontend/student/index.html` 의 `<div class="stops-card"> ... </div>` 내부를 아래로 교체:

```html
      <div class="stops-card">
        <div class="stops-meta">
          <span class="bus-ico">🚌</span>
          <span id="sheetRouteDir">출발 → 도착</span>
          <span class="running-pill" id="sheetRunning" hidden></span>
        </div>
        <div class="stops-track stops-track-2" id="sheetStops"></div>
      </div>
```

- [ ] **Step 2: app.js openRoute/renderSheet를 async 상세 로드로 교체**

`openRoute(r)` 는 그대로 두고(시트 열기 분기 로직 재사용), 단 `renderSheet()` 호출 뒤 상세 로드를 트리거하도록 `renderSheet` 를 동기(기본 정보)와 비동기(라이브) 두 단계로 나눈다. 기존 `renderSheet()` 함수를 아래로 교체:

```js
// 시트 기본 정보(즉시) + 라이브 데이터(비동기) 렌더
function renderSheet() {
  const r = state.sheetRoute;
  if (!r) return;
  const c = CONGESTION[r.level];
  const t = BUS_TYPE[r.type];

  $('sheetRouteName').textContent = r.name;
  const tb = $('sheetBusType');
  tb.textContent = t.label; tb.style.background = t.color;
  $('sheetRouteDir').textContent = `${r.from} → ${r.to}`;

  // 출발→도착 2점 트랙
  $('sheetStops').innerHTML = [r.from, r.to].map((s, idx) => {
    const cls = idx === 0 ? 'past' : 'future';
    return `<div class="stop-item"><div class="stop-dot ${cls}"></div>` +
           `<span class="stop-name ${cls}">${s}</span></div>`;
  }).join('');

  // 현재 혼잡도 원
  const cc = $('sheetCongCircle');
  cc.textContent = c.label; cc.style.background = c.color;
  $('sheetCongTitle').textContent = c.title;
  $('sheetCongMsg').textContent = c.msg;

  // 운행 칩/예측/도착은 로딩 표시 후 비동기 채움
  $('sheetRunning').hidden = true;
  $('sheetForecast').innerHTML = '';
  $('sheetForecastLabels').innerHTML = '';
  updateSheetFavBtn();

  loadSheetLive(r);
}

// 시트 라이브 데이터: 예측 막대 + 도착 + 운행 대수. 30초 도착 갱신.
async function loadSheetLive(r) {
  // 시간대별 예측 (정류장 단위)
  const fc = await Data.loadForecast(r.stationId);
  const nowIdx = 0; // 첫 막대가 현재 시각
  $('sheetForecast').innerHTML = fc.levels.map((lvl, i) => {
    const info = CONGESTION[lvl];
    const h = ((lvl + 1) / 4) * 100;
    const isNow = i === nowIdx;
    return `<div class="fc-col"><div class="fc-bar ${isNow ? 'current' : ''}" ` +
      `style="height:${h}%;background:${info.color};${isNow ? `box-shadow:0 0 12px ${info.color}80;` : ''}"></div></div>`;
  }).join('');
  $('sheetForecastLabels').innerHTML = fc.hours.map((h, i) =>
    `<span class="fc-label ${i === nowIdx ? 'current' : ''}">${h}시${i === nowIdx ? ' ←' : ''}</span>`
  ).join('');

  await refreshSheetArrival(r);  // 도착 + 운행 + 타이머
}

// 도착/운행 갱신 (30초 주기). 시트가 닫히거나 다른 노선이면 중단.
async function refreshSheetArrival(r) {
  if (!state.sheetOpen || !state.sheetRoute || state.sheetRoute.id !== r.id) return;
  const busstopId = state.busstopMap[r.stationId];
  const res = await Data.loadArrivalAndRunning(busstopId, r.name);

  // 운행 대수 칩
  const pill = $('sheetRunning');
  if (res.runningCount != null) {
    pill.textContent = `운행 중 ${res.runningCount}대`;
    pill.hidden = false;
  } else {
    pill.hidden = true;
  }

  // 첫 도착을 헤더 도착 카드에 반영
  if (res.arrivals.length) {
    const a = res.arrivals[0];
    $('sheetArrName').textContent = r.name;
    $('sheetArrDest').textContent = `→ ${a.dirEnd || r.to}`;
    $('sheetArrMin').textContent = `${a.min}분`;
    $('sheetArrStop').textContent = `${a.stops}정류장`;
  } else {
    $('sheetArrName').textContent = r.name;
    $('sheetArrDest').textContent = `→ ${r.to}`;
    $('sheetArrMin').textContent = '정보 없음';
    $('sheetArrStop').textContent = '';
  }

  // 30초 후 재갱신 예약
  if (state.arrivalTimer) clearTimeout(state.arrivalTimer);
  state.arrivalTimer = setTimeout(() => refreshSheetArrival(r), 30000);
}
```

- [ ] **Step 3: 시트 닫을 때 도착 타이머 정리**

`closeSheet()` 함수 본문 끝(`state.closing = true;` 줄 위)에 추가:

```js
  if (state.arrivalTimer) { clearTimeout(state.arrivalTimer); state.arrivalTimer = null; }
```

- [ ] **Step 4: 운행 칩 스타일 추가**

`frontend/student/style.css` 끝에 추가:

```css
/* 시트 운행 대수 라이브 칩 */
.running-pill { margin-left:auto; background:#22c55e; color:#fff;
  border-radius:999px; padding:3px 10px; font-size:12px; font-weight:700; }
/* 2점 트랙은 양끝 정렬 */
.stops-track-2 { justify-content:space-between; }
```

- [ ] **Step 5: docker-compose 수동 스모크**

Run: `docker-compose up -d --build` → `http://localhost`, INS01 노선 카드 탭
Expected:
- 시트 열림: 혼잡도 원/제목/문구가 노선 레벨에 맞게 표시.
- 출발→도착 2점 트랙 표시.
- 시간대별 막대 6개가 채워짐(첫 막대 현재 강조).
- 도착 정보가 분/정류장으로 표시(없으면 "정보 없음").
- BIS 응답 시 "운행 중 N대" 칩 표시. (실패 시 칩 숨김, 화면 정상)
- 30초 후 도착 갱신, 시트 닫으면 갱신 중단.

- [ ] **Step 6: Commit**

```bash
git add frontend/student/
git commit -m "feat(student): 노선 상세 시트 실데이터 (혼잡도/예측/BIS도착/운행대수, 30초 갱신, 트랙 A안)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 폴백 견고화 · 정리 · 최종 검증

목표: API 실패 시에도 화면 유지 확인, 루트 student/ 보관 이동, 백엔드 회귀, 최종 스모크.

**Files:**
- Move: `student/` → `archive/student-design-ref/`
- (검증 전용, 코드 변경 없음 가능)

- [ ] **Step 1: 검색/즐겨찾기 빈/실패 경로 확인**

백엔드를 잠시 내려 폴백 확인:
Run:
```bash
docker-compose stop backend
```
브라우저 새로고침.
Expected: 정류장 목록은 비거나 데모 셋, 노선 카드는 비더라도 콘솔 `console.error/warn`만 출력되고 페이지는 깨지지 않음(탭/테마/시트 닫기 동작). 확인 후:
```bash
docker-compose start backend
```

- [ ] **Step 2: 매퍼 단위 테스트 회귀**

Run: `cd frontend/student && node --test data.test.js`
Expected: PASS (9개 통과).

- [ ] **Step 3: 백엔드 테스트 회귀 (무변경 확인)**

Run:
```bash
cd /home/ahble/projects/Capstone/bustago && python -m pytest backend/test_app.py -q
```
Expected: 기존과 동일하게 PASS (백엔드 미변경).

- [ ] **Step 4: 루트 student/ 를 archive로 이동**

Run:
```bash
cd /home/ahble/projects/Capstone/bustago
mkdir -p archive
git mv student archive/student-design-ref 2>/dev/null || { mkdir -p archive/student-design-ref && mv student/* archive/student-design-ref/ && rmdir student; }
```

- [ ] **Step 5: 최종 통합 스모크 체크리스트 (docker-compose)**

Run: `docker-compose up -d --build` → `http://localhost`
Expected(모두 통과):
- [ ] 첫 화면 즐겨찾기 탭, 날씨 카드 없음
- [ ] 노선 검색: 정류장 목록 → "인성관" 검색 → 정류장 선택 → 노선 카드
- [ ] 즐겨찾기 추가/해제, 새로고침 유지
- [ ] 시트: 혼잡도/막대/도착/운행칩, 30초 갱신, 드래그 닫기
- [ ] 다크모드 토글 유지
- [ ] 오프라인(개발자도구 Network offline)에서 셸 로딩(SW v2)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore(student): 루트 student/ 디자인 참고본 archive 이동 + 통합 검증 완료

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (작성자 점검 결과)

**1. 스펙 커버리지:**
- §3 아키텍처(data.js 어댑터, 관심사 분리) → Task 1·2·3·4(Step5 Data 전역) ✅
- §4 뷰모델 계약 → Task 2 `mapRoutesToCards` ✅
- §5 정류장-우선 검색 → Task 4 ✅; 즐겨찾기 그룹핑 → Task 4 Step6 `renderFavs` ✅
- §5 상세 시트(혼잡도/예측/도착/30초) → Task 5 ✅
- §6 트랙 A안(2점+운행칩) → Task 5 Step1·2 ✅
- §7 폴백 표 → 매퍼 null 처리(Task2) + Task 6 Step1 ✅
- §8 테스트(매퍼 Node + 백엔드 pytest + 수동) → Task 2·6 ✅
- §9 마이그레이션(교체/추가/archive) → Task 1·6 ✅
- 날씨 카드 제거 → Task 1 Step2 ✅

**2. Placeholder 스캔:** TBD/TODO/"적절히 처리" 없음. 모든 코드 스텝에 실제 코드 포함. ✅

**3. 타입/명칭 일관성:**
- 뷰모델 키(`id,stationId,stationName,name,routeNo,from,to,level,type,recommended`) Task2 정의 ↔ Task4·5 사용 일치 ✅
- `Data.loadStations/loadRoutesForStation/loadForecast/loadArrivalAndRunning` Task3 정의 ↔ Task4·5 호출 일치 ✅
- `makeFavId` 형식 `a::b` Task2 ↔ 즐겨찾기 키 Task4 일치 ✅
- localStorage 키 `bustago_favs_v2` Task4 Step2·7 일관 ✅
- `state.arrivalTimer` Task4 정의 ↔ Task5 사용/정리 일치 ✅
