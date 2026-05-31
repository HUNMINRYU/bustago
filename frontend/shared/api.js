// BUSTAGO Shared API Wrapper

var API_BASE = window.location.origin + '/api';

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

// Convenience wrappers matching API contract endpoints
async function fetchPredict(stationId, hour, weekday) {
  var params = { station_id: stationId, hour: hour };
  if (weekday !== undefined) params.weekday = weekday;
  return fetchAPI('/predict', params);
}

async function fetchStats(stationId, period) {
  var params = { station_id: stationId };
  if (period) params.period = period;
  return fetchAPI('/stats', params);
}

async function fetchStations() {
  return fetchAPI('/stations');
}

// 2026-05-17 단순화 C: fetchWeather 제거 (/api/weather/current 엔드포인트 제거됨).

async function fetchCrowdCount(stationId) {
  return fetchAPI('/crowd-count', { station_id: stationId });
}

async function fetchRouteRecommend(stationId, hour, weekday, dest) {
  var params = { station_id: stationId, hour: hour };
  if (weekday !== undefined) params.weekday = weekday;
  if (dest) params.dest = dest;
  return fetchAPI('/route-recommend', params);
}

async function fetchBusArrival(busstopId) {
  return fetchAPI('/arrive/' + busstopId);
}

// 2026-05-17: 광주 BIS 실시간 버스 위치 — captest에서 본 시스템으로 이관
async function fetchBusLocation(lineId) {
  return fetchAPI('/bus_location/' + lineId);
}

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
