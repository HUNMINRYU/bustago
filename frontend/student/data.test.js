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

test('mapStations: 서울 샘플 제외 + GJ 양방향 정류장 포함 + 각 정류장 자체 busstop_id', () => {
  const data = [
    { ars_no: '22011', station_name: '지하철2호선강남역', gj_busstop_id: null },
    { ars_no: 'INS01', station_name: '광주대 인성관', gj_busstop_id: null },
    { ars_no: 'GJ3229', station_name: '광주대 금호아파트방면', gj_busstop_id: 80 },
    { ars_no: 'GJ3230', station_name: '광주대 구암방면', gj_busstop_id: 1981 },
    { ars_no: 'DEMO01', station_name: '시연용 정류장', gj_busstop_id: null },
  ];
  const r = D.mapStations(data);
  // 서울(22011) 제외, 나머지 4개 유지
  assert.deepStrictEqual(r.stations.map((s) => s.ars_no).sort(),
    ['DEMO01', 'GJ3229', 'GJ3230', 'INS01']);
  // busstopMap은 각 정류장 자체 gj_busstop_id (GATE01 fallback 제거됨)
  assert.strictEqual(r.busstopMap.GJ3230, 1981);
  assert.strictEqual(r.busstopMap.GJ3229, 80);
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
test('mapArrivalsForRoute: 7개 이상 → 6개로 제한 + 가장 가까운 것 먼저', () => {
  const mins = [9, 8, 7, 6, 5, 4, 3, 2];
  const items = mins.map(function (m) {
    return { SHORT_LINE_NAME: '송정51', REMAIN_MIN: String(m), REMAIN_STOP: '1', LOW_BUS: 0, DIR_END: '광주역', LINE_ID: 9 };
  });
  const r = D.mapArrivalsForRoute(items, '송정51');
  assert.strictEqual(r.length, 6);
  assert.strictEqual(r[0].min, 2); // 가장 가까운 것 먼저
});

test('mapArrivalsForRoute: route-recommend 표시명과 BIS 단축 노선명 표기 차이 허용', () => {
  const items = [
    { SHORT_LINE_NAME: '419', REMAIN_MIN: '4', REMAIN_STOP: '2', LOW_BUS: 0, DIR_END: '광주역', LINE_ID: 419 },
    { SHORT_LINE_NAME: '518번', REMAIN_MIN: '9', REMAIN_STOP: '5', LOW_BUS: 0, DIR_END: '금남로', LINE_ID: 518 },
  ];
  const r = D.mapArrivalsForRoute(items, '419번 (광주역행)');
  assert.strictEqual(r.length, 1);
  assert.strictEqual(r[0].lineId, 419);
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
test('mapPredictsToForecast: null 입력 → 빈 결과 (안전 degradation)', () => {
  assert.deepStrictEqual(D.mapPredictsToForecast(null, 8), { hours: [], levels: [] });
});

test('mapCrowdCount: crowd-count 응답을 정류장 현황 뷰모델로 변환', () => {
  const r = D.mapCrowdCount({
    current_waiting: 7,
    count_in: 12,
    count_board: 5,
    source: 'jetson',
    created_at: '2026-06-03T10:00:00',
  }, new Date('2026-06-03T10:00:30').getTime());
  assert.deepStrictEqual(r, {
    waiting: 7,
    countIn: 12,
    countBoard: 5,
    source: 'jetson',
    createdAt: '2026-06-03T10:00:00',
    ageSec: 30,
    stale: false,
  });
});

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
  assert.deepStrictEqual(D.mapBusPositions([{ BUSSTOP_ID: 80 }], stops), [2]);
  assert.deepStrictEqual(
    D.mapBusPositions([{ LATITUDE: 35.108, LONGITUDE: 126.898 }], stops), [2]);
  assert.deepStrictEqual(D.mapBusPositions([{}], stops), []);
});
