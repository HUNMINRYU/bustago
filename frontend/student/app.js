// BUSTAGO Student PWA - App Logic

var CONGESTION = {
  0: { label: '여유', color: '#4CAF50', icon: '\uD83D\uDFE2', bg: '#E8F5E9',
       message: '여유로운 시간대입니다. 탑승을 추천합니다.' },
  1: { label: '보통', color: '#FFC107', icon: '\uD83D\uDFE1', bg: '#FFF8E1',
       message: '평균적인 혼잡도입니다.' },
  2: { label: '혼잡', color: '#FF9800', icon: '\uD83D\uDFE0', bg: '#FFF3E0',
       message: '혼잡이 예상됩니다. 다음 시간대를 추천합니다.' },
  3: { label: '매우혼잡', color: '#F44336', icon: '\uD83D\uDD34', bg: '#FFEBEE',
       message: '매우 혼잡합니다. 대안 교통을 고려하세요.' }
};

// 정류장 → gj_busstop_id 캐시 (stations API 응답에서 채워짐)
var STATION_BUSSTOP_MAP = {};

// 광주 BIS 실시간 도착 자동 갱신
var ARRIVAL_REFRESH_MS = 30000;
var arrivalTimer = null;
var arrivalCountdown = 30;
var arrivalCountdownTimer = null;

// DOM Elements
var stationSelect = document.getElementById('station-select');
var destSelect = document.getElementById('dest-select');
var congestionDisplay = document.getElementById('congestion-display');
var congestionCircle = document.getElementById('congestion-circle');
var congestionIcon = document.getElementById('congestion-icon');
var congestionLabel = document.getElementById('congestion-label');
var congestionMessage = document.getElementById('congestion-message');
var recommendation = document.getElementById('recommendation');
var recommendationContent = document.getElementById('recommendation-content');
var forecast = document.getElementById('forecast');
var forecastBars = document.getElementById('forecast-bars');

// Event Listeners
stationSelect.addEventListener('change', onStationChange);
if (destSelect) {
  destSelect.addEventListener('change', function() { loadRouteRecommend(); });
}

// Register Service Worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('service-worker.js');
}

// Load stations from API on init
// 광주 정류장(INS01, GATE01, GJ*)을 상단에 표시하고 INS01을 자동 선택 (시연 UX)
(async function loadStationOptions() {
  var data = await fetchStations();
  if (data && Array.isArray(data)) {
    // 광주 정류장 우선 정렬: 광주(INS01/GATE01/GJ*)는 앞으로, 서울은 뒤로
    data.sort(function(a, b) {
      var aGJ = /^(INS|GATE|GJ)/.test(a.ars_no) ? 0 : 1;
      var bGJ = /^(INS|GATE|GJ)/.test(b.ars_no) ? 0 : 1;
      return aGJ - bGJ;
    });

    data.forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s.ars_no;
      opt.textContent = s.station_name;
      stationSelect.appendChild(opt);
      if (s.gj_busstop_id) {
        STATION_BUSSTOP_MAP[s.ars_no] = s.gj_busstop_id;
      }
    });

    // 기본 선택: INS01(인성관 셔틀, 시연 메인 정류장) → 없으면 첫 광주 정류장
    var defaultStation = data.find(function(s) { return s.ars_no === 'INS01'; })
                      || data.find(function(s) { return /^(GATE|GJ)/.test(s.ars_no); })
                      || data[0];
    if (defaultStation) {
      stationSelect.value = defaultStation.ars_no;
      stationSelect.dispatchEvent(new Event('change'));
    }
  }
})();

function onStationChange() {
  var stationId = stationSelect.value;
  if (!stationId) {
    hideResults();
    return;
  }
  var hour = new Date().getHours();
  loadPrediction(stationId, hour);
}

function hideResults() {
  congestionDisplay.classList.add('hidden');
  recommendation.classList.add('hidden');
  forecast.classList.add('hidden');
  var rrs = document.getElementById('route-recommend-section');
  if (rrs) rrs.classList.add('hidden');
  var as = document.getElementById('arrival-section');
  if (as) as.classList.add('hidden');
  stopArrivalTimers();
}

// Load prediction from API
async function loadPrediction(stationId, hour) {
  // Show loading state
  congestionDisplay.classList.remove('hidden');
  congestionCircle.style.backgroundColor = '#E0E0E0';
  congestionIcon.textContent = '';
  congestionLabel.textContent = '...';
  congestionMessage.textContent = '서버 연결 중...';
  recommendation.classList.add('hidden');
  forecast.classList.add('hidden');

  var data = await fetchPredict(stationId, hour);

  if (data) {
    var level = data.prediction.level;
    updateCongestionDisplay(level);
    updateRecommendation(level, data.recommendation, data.next_hour_prediction);
    loadForecast(stationId, hour);
  } else {
    // API failed -- use demo fallback
    var demoLevel = getDemoLevel(hour);
    updateCongestionDisplay(demoLevel);
    updateRecommendation(demoLevel);
    updateForecastDemo(hour);
  }
  loadRouteRecommend();
  loadBusArrival();
}

// Load forecast for next 6 hours via API
async function loadForecast(stationId, currentHour) {
  forecastBars.innerHTML = '';
  var weekday = new Date().getDay();
  // JS getDay: 0=Sun, convert to 0=Mon
  weekday = weekday === 0 ? 6 : weekday - 1;

  var promises = [];
  for (var i = 0; i < 6; i++) {
    var h = (currentHour + i) % 24;
    promises.push(fetchPredict(stationId, h, weekday));
  }

  var results = await Promise.all(promises);
  var allFailed = true;

  for (var i = 0; i < 6; i++) {
    var h = (currentHour + i) % 24;
    var level;
    if (results[i]) {
      level = results[i].prediction.level;
      allFailed = false;
    } else {
      level = getDemoLevel(h);
    }
    appendForecastBar(h, level);
  }

  forecast.classList.remove('hidden');
}

function appendForecastBar(hour, level) {
  var info = CONGESTION[level];
  var heightPercent = ((level + 1) / 4) * 100;

  var wrapper = document.createElement('div');
  wrapper.className = 'forecast-bar-wrapper';

  var bar = document.createElement('div');
  bar.className = 'forecast-bar';
  bar.style.height = heightPercent + '%';
  bar.style.backgroundColor = info.color;
  bar.title = info.label;

  var label = document.createElement('span');
  label.className = 'forecast-bar-label';
  label.textContent = hour + '시';

  wrapper.appendChild(bar);
  wrapper.appendChild(label);
  forecastBars.appendChild(wrapper);
}

// Demo fallback forecast
function updateForecastDemo(currentHour) {
  forecastBars.innerHTML = '';
  for (var i = 0; i < 6; i++) {
    var h = (currentHour + i) % 24;
    appendForecastBar(h, getDemoLevel(h));
  }
  forecast.classList.remove('hidden');
}

// Demo congestion level based on hour
function getDemoLevel(hour) {
  if (hour >= 7 && hour <= 9) return 3;
  if (hour >= 17 && hour <= 19) return 3;
  if (hour >= 10 && hour <= 16) return 1;
  if (hour === 6) return 0;
  return 0;
}

// Update congestion circle display
function updateCongestionDisplay(level) {
  var info = CONGESTION[level];
  congestionCircle.style.backgroundColor = info.color;
  congestionIcon.textContent = info.icon;
  congestionLabel.textContent = info.label;
  congestionMessage.textContent = info.message;
  congestionDisplay.classList.remove('hidden');
}

// Load route recommendations from API
async function loadRouteRecommend() {
  var stationId = stationSelect ? stationSelect.value : '';
  if (!stationId) return;

  var now = new Date();
  var hour = now.getHours();
  var jsDay = now.getDay();
  var weekday = jsDay === 0 ? 6 : jsDay - 1;
  var dest = destSelect ? destSelect.value : '';

  var section = document.getElementById('route-recommend-section');
  var list = document.getElementById('route-list');
  if (!section || !list) return;

  var result = await fetchRouteRecommend(stationId, hour, weekday, dest);

  if (!result || !result.routes || result.routes.length === 0) {
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');
  list.innerHTML = result.routes.map(function(r) {
    var c = r.congestion;
    var lvl = c.level;
    var color = (CONGESTION[lvl] && CONGESTION[lvl].color) ? CONGESTION[lvl].color : '#9E9E9E';
    var labelText = (CONGESTION[lvl] && CONGESTION[lvl].label) ? CONGESTION[lvl].label : '알 수 없음';
    var recBadge = r.recommended ? '<span class="rec-badge">추천</span>' : '';
    return '<div class="route-card' + (r.recommended ? ' recommended' : '') + '">' +
      '<div class="route-header">' +
        '<span class="route-no">' + r.route_name + '</span>' + recBadge +
      '</div>' +
      '<div class="route-dest">→ ' + r.end_stations.join(', ') + '</div>' +
      '<div class="congestion-badge" style="background:' + color + '">' + labelText + '</div>' +
    '</div>';
  }).join('');
}

// 광주 BIS 실시간 도착 정보 로드 + 30초 자동 갱신
async function loadBusArrival() {
  var stationId = stationSelect ? stationSelect.value : '';
  var busstopId = STATION_BUSSTOP_MAP[stationId];
  var section = document.getElementById('arrival-section');
  var list = document.getElementById('arrival-list');
  if (!section || !list) return;

  if (!busstopId) {
    section.classList.add('hidden');
    stopArrivalTimers();
    return;
  }

  var data = await fetchBusArrival(busstopId);
  var items = data && data.items ? data.items : [];

  section.classList.remove('hidden');

  if (!items.length) {
    list.innerHTML = '<div class="arrival-empty">현재 도착 예정 버스가 없습니다.</div>';
  } else {
    items.sort(function (a, b) {
      return (parseInt(a.REMAIN_MIN) || 999) - (parseInt(b.REMAIN_MIN) || 999);
    });
    list.innerHTML = items.slice(0, 6).map(function (it) {
      var min = parseInt(it.REMAIN_MIN) || 0;
      var stop = parseInt(it.REMAIN_STOP) || 0;
      var imminent = it.ARRIVE_FLAG == 1;
      var low = it.LOW_BUS == 1;
      var minCls = min <= 3 ? 'soon' : (min <= 10 ? 'mid' : 'far');
      var dirEnd = it.DIR_END || '';
      var lineName = it.SHORT_LINE_NAME || it.LINE_NAME || '?';
      return '<div class="arrival-card">' +
        '<div class="arrival-head">' +
          '<span class="arrival-line">' + lineName + '</span>' +
          (low ? '<span class="arrival-tag">저상</span>' : '') +
          (imminent ? '<span class="arrival-tag imminent">곧 도착</span>' : '') +
        '</div>' +
        '<div class="arrival-meta">→ ' + dirEnd + '</div>' +
        '<div class="arrival-eta">' +
          '<span class="arrival-min ' + minCls + '">' + min + '분</span>' +
          '<span class="arrival-stop">' + stop + '정류장 전</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  startArrivalTimers();
}

function startArrivalTimers() {
  stopArrivalTimers();
  arrivalCountdown = ARRIVAL_REFRESH_MS / 1000;
  updateArrivalCountdownUI();
  arrivalCountdownTimer = setInterval(function () {
    arrivalCountdown--;
    updateArrivalCountdownUI();
    if (arrivalCountdown <= 0) arrivalCountdown = ARRIVAL_REFRESH_MS / 1000;
  }, 1000);
  arrivalTimer = setTimeout(function () { loadBusArrival(); }, ARRIVAL_REFRESH_MS);
}

function stopArrivalTimers() {
  if (arrivalTimer) { clearTimeout(arrivalTimer); arrivalTimer = null; }
  if (arrivalCountdownTimer) { clearInterval(arrivalCountdownTimer); arrivalCountdownTimer = null; }
}

function updateArrivalCountdownUI() {
  var el = document.getElementById('arrival-countdown');
  if (el) el.textContent = arrivalCountdown;
}

// Update recommendation card
function updateRecommendation(level, apiMessage, nextHour) {
  var shouldBoard = level <= 1;
  var card = recommendationContent.querySelector('.recommendation-card');
  var icon = card.querySelector('.recommendation-icon');
  var text = card.querySelector('.recommendation-text');

  card.className = 'recommendation-card ' + (shouldBoard ? 'board' : 'wait');
  icon.textContent = shouldBoard ? '\u2705' : '\u23F3';

  if (apiMessage) {
    text.textContent = apiMessage;
  } else {
    text.textContent = shouldBoard
      ? '지금 탑승하세요!'
      : '다음 시간대를 추천합니다';
  }

  recommendation.classList.remove('hidden');
}
