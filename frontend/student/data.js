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
