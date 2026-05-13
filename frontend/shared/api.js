// BUSTAGO Shared API Wrapper

var API_BASE = window.location.origin + '/api';

async function fetchAPI(endpoint, params) {
  params = params || {};
  var url = new URL(API_BASE + endpoint);
  Object.entries(params).forEach(function (entry) {
    url.searchParams.set(entry[0], entry[1]);
  });
  try {
    var res = await fetch(url);
    var data = await res.json();
    if (data.status !== 'ok') throw new Error(data.message);
    return data.data;
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

async function fetchWeather() {
  return fetchAPI('/weather/current');
}

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
