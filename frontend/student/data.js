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

function isOperationalStation(station) {
  var id = station && station.ars_no;
  return id === 'INS01' || id === 'DEMO01' || /^GJ/.test(id || '');
}

// 버스 유형 추론: 도착항목 LOW_BUS 우선, 다음 노선명 패턴, 기본 normal
function deriveBusType(routeName, arrivalItem) {
  if (arrivalItem && Number(arrivalItem.LOW_BUS) === 1) return 'low';
  if (/좌석|급행/.test(routeName || '')) return 'express';
  return 'normal';
}

function normalizeRouteName(routeName) {
  return String(routeName == null ? '' : routeName)
    .replace(/\([^)]*\)/g, '')
    .replace(/번/g, '')
    .replace(/\s+/g, '')
    .toUpperCase();
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
  var stations = data.filter(isOperationalStation).slice().sort(function (a, b) {
    var aGJ = /^(INS|GJ)/.test(a.ars_no) ? 0 : 1;
    var bGJ = /^(INS|GJ)/.test(b.ars_no) ? 0 : 1;
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
  var target = normalizeRouteName(routeName);
  return items
    .filter(function (it) {
      var nm = it.SHORT_LINE_NAME || it.LINE_NAME || '';
      var normalized = normalizeRouteName(nm);
      return normalized === target ||
        (!!target && normalized.indexOf(target) >= 0) ||
        (!!normalized && target.indexOf(normalized) >= 0);
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

// crowd-count 응답 → 정류장 현황 뷰모델. nowMs는 테스트에서 시간 고정용.
function mapCrowdCount(data, nowMs) {
  if (!data) return null;
  var createdAt = data.created_at || '';
  var ts = createdAt ? new Date(createdAt).getTime() : NaN;
  var ageSec = Number.isFinite(ts) ? Math.max(0, Math.floor(((nowMs || Date.now()) - ts) / 1000)) : null;
  return {
    waiting: Number(data.current_waiting) || 0,
    countIn: Number(data.count_in) || 0,
    countBoard: Number(data.count_board) || 0,
    source: data.source || '',
    createdAt: createdAt,
    ageSec: ageSec,
    stale: ageSec != null ? ageSec > 60 : true,
  };
}

// predict 결과 배열(6개) → 막대 그래프 데이터 (null은 데모값)
function mapPredictsToForecast(preds, startHour) {
  if (!Array.isArray(preds)) preds = [];
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
    var total = startHour + i;
    var h = total % 24;
    var wd = total >= 24 ? (weekday + 1) % 7 : weekday;
    promises.push(fetchPredict(stationId, h, wd));
  }
  var preds = await Promise.all(promises);
  return mapPredictsToForecast(preds, startHour);
}

// 학생 홈용 실시간 정류장 현황. 데이터 없으면 null.
async function loadStationStatus(stationId) {
  if (!stationId) return null;
  var data = await fetchCrowdCount(stationId);
  return mapCrowdCount(data);
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

// 브라우저 전역으로 노출 (app.js가 Data.* 로 호출)
if (typeof window !== 'undefined') {
  window.Data = {
    demoLevel: demoLevel, makeFavId: makeFavId, deriveBusType: deriveBusType,
    mapRoutesToCards: mapRoutesToCards, mapStations: mapStations,
    mapArrivalsForRoute: mapArrivalsForRoute, mapPredictsToForecast: mapPredictsToForecast,
    mapCrowdCount: mapCrowdCount, normalizeRouteName: normalizeRouteName,
    loadStations: loadStations, loadRoutesForStation: loadRoutesForStation,
    loadForecast: loadForecast, loadStationStatus: loadStationStatus,
    loadArrivalAndRunning: loadArrivalAndRunning,
    mapStationBoard: mapStationBoard, mapLineStations: mapLineStations,
    mapBusPositions: mapBusPositions,
    loadStationBoard: loadStationBoard, loadLineStations: loadLineStations,
    loadBusPositions: loadBusPositions,
  };
}

// Node 테스트용 export (브라우저에서는 무시됨)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    demoLevel: demoLevel,
    makeFavId: makeFavId,
    isOperationalStation: isOperationalStation,
    deriveBusType: deriveBusType,
    normalizeRouteName: normalizeRouteName,
    mapRoutesToCards: mapRoutesToCards,
    mapStations: mapStations,
    mapArrivalsForRoute: mapArrivalsForRoute,
    mapPredictsToForecast: mapPredictsToForecast,
    mapCrowdCount: mapCrowdCount,
    mapStationBoard: mapStationBoard,
    mapLineStations: mapLineStations,
    mapBusPositions: mapBusPositions,
    loadStations: typeof fetchStations !== 'undefined' ? loadStations : undefined,
    loadRoutesForStation: typeof fetchRouteRecommend !== 'undefined' ? loadRoutesForStation : undefined,
    loadForecast: typeof fetchPredict !== 'undefined' ? loadForecast : undefined,
    loadStationStatus: typeof fetchCrowdCount !== 'undefined' ? loadStationStatus : undefined,
    loadArrivalAndRunning: typeof fetchBusArrival !== 'undefined' ? loadArrivalAndRunning : undefined,
  };
}
