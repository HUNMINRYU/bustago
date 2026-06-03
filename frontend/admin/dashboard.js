// BUSTAGO Admin Dashboard - Logic

var CONGESTION = {
  0: { label: '여유', color: '#4CAF50' },
  1: { label: '보통', color: '#FFC107' },
  2: { label: '혼잡', color: '#FF9800' },
  3: { label: '매우혼잡', color: '#F44336' }
};

// Loaded dynamically from /api/stations
var STATIONS = {};

// Demo fallback data
var DEMO_HOURLY = [0, 0, 0, 0, 0, 0, 1, 2, 3, 2, 1, 1, 1, 1, 1, 1, 2, 3, 3, 2, 1, 1, 0, 0];
var DEMO_STATS = [
  { id: 'GATE01', name: '광주대 정문 (시내버스)', avgCongestion: 2.1, fullCount: 7, peakHour: '08시', currentLevel: 2 },
  { id: 'INS01', name: '광주대 인성관 (셔틀)', avgCongestion: 1.6, fullCount: 4, peakHour: '17시', currentLevel: 1 }
];

var congestionChart = null;
var doughnutChart = null;
var stationMap = null;
var pendingMapStats = null;
var refreshInterval = null;
var REFRESH_MS = 60000; // 60 seconds
var CROWD_REFRESH_MS = 2000;
var JETSON_STALE_MS = 60000;

// DEMO01 옵션 누락 시 강제 추가 (마크업/loadStations에 이미 있으면 noop)
function ensureDemoOption(stationFilter) {
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
}

// DOM elements
var stationFilter = document.getElementById('station-filter');
var periodFilter = document.getElementById('period-filter');

// Loading overlay helpers
function showLoading() {
  var overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.add('active');
}

function hideLoading() {
  var overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.remove('active');
}

function updateTimestamp() {
  var el = document.getElementById('last-updated');
  if (!el) return;
  var now = new Date();
  var hh = String(now.getHours()).padStart(2, '0');
  var mm = String(now.getMinutes()).padStart(2, '0');
  var ss = String(now.getSeconds()).padStart(2, '0');
  el.textContent = '마지막 업데이트: ' + hh + ':' + mm + ':' + ss;
}

// Initialize
document.addEventListener('DOMContentLoaded', async function () {
  showLoading();
  await loadStations();
  initChart();
  initDoughnutChart();
  initMap();
  await loadDashboardData();
  hideLoading();
  ensureDemoOption(stationFilter);
  applyDemoVisibility();
  loadCrowdCount();
  loadEvents();
  setInterval(function() {
    loadCrowdCount();
    loadEvents();
  }, CROWD_REFRESH_MS);

  stationFilter.addEventListener('change', loadDashboardData);
  stationFilter.addEventListener('change', function() {
    applyDemoVisibility();
    loadCrowdCount();
    loadEvents();
  });
  periodFilter.addEventListener('change', loadDashboardData);

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

  // Auto-refresh every 60 seconds
  refreshInterval = setInterval(function () {
    loadDashboardData();
  }, REFRESH_MS);
});

// Load stations from API and populate STATIONS + filter dropdown
async function loadStations() {
  var data = await fetchStations();
  if (data && Array.isArray(data)) {
    data.forEach(function (s) {
      STATIONS[s.ars_no] = {
        name: s.station_name,
        lat: s.latitude,
        lng: s.longitude
      };
      var opt = document.createElement('option');
      opt.value = s.ars_no;
      opt.textContent = s.station_name;
      stationFilter.appendChild(opt);
    });
  }
  // If API failed, keep STATIONS empty -- demo fallback will handle display
}

// ==================== Data Loading ====================

async function loadDashboardData() {
  showLoading();
  var stationId = stationFilter.value;
  var period = periodFilter.value;

  try {
    if (stationId === 'all') {
      await loadAllStationsData(period);
    } else {
      await loadSingleStationData(stationId, period);
    }
  } finally {
    updateTimestamp();
    hideLoading();
  }
}

async function loadAllStationsData(period) {
  var stationIds = Object.keys(STATIONS);
  var statsResults = [];
  var hourlyData = null;

  // Fetch stats for all stations
  var promises = stationIds.map(function (id) {
    return fetchStats(id, period);
  });
  var results = await Promise.all(promises);

  var usedDemo = false;
  stationIds.forEach(function (id, idx) {
    var data = results[idx];
    if (data && data.hourly_stats) {
      if (!hourlyData) {
        hourlyData = extractHourlyLevels(data.hourly_stats);
      }
      statsResults.push(buildStatRow(id, data));
    } else {
      usedDemo = true;
      var demo = DEMO_STATS.find(function (s) { return s.id === id; });
      if (demo) statsResults.push(demo);
    }
  });

  if (!hourlyData) {
    hourlyData = DEMO_HOURLY;
    usedDemo = true;
  }

  updateChart(hourlyData);
  updateDoughnutChart(hourlyData);
  updateMap(statsResults);
  fillStatsTable(statsResults);
  updateSummary(statsResults);
}

async function loadSingleStationData(stationId, period) {
  var data = await fetchStats(stationId, period);

  if (data && data.hourly_stats) {
    var hourlyData = extractHourlyLevels(data.hourly_stats);
    var statRow = buildStatRow(stationId, data);
    updateChart(hourlyData);
    updateDoughnutChart(hourlyData);
    updateMap([statRow]);
    fillStatsTable([statRow]);
    updateSummary([statRow]);
  } else {
    // Fallback to demo
    var demo = DEMO_STATS.filter(function (s) { return s.id === stationId; });
    updateChart(DEMO_HOURLY);
    updateDoughnutChart(DEMO_HOURLY);
    updateMap(demo);
    fillStatsTable(demo);
    updateSummary(demo);
  }
}

function extractHourlyLevels(hourlyStats) {
  var levels = [];
  for (var h = 0; h < 24; h++) {
    var entry = hourlyStats.find(function (s) { return s.hour === h; });
    if (entry && entry.avg_level !== null) {
      levels.push(Math.round(entry.avg_level));
    } else {
      levels.push(0);
    }
  }
  return levels;
}

function buildStatRow(stationId, data) {
  var hourlyStats = data.hourly_stats || [];
  var levels = [];
  var peakHour = 0;
  var peakLevel = 0;
  var fullCount = 0;

  hourlyStats.forEach(function (s) {
    if (s.avg_level !== null) {
      levels.push(s.avg_level);
      if (s.avg_level > peakLevel) {
        peakLevel = s.avg_level;
        peakHour = s.hour;
      }
      if (s.avg_level >= 3) fullCount++;
    }
  });

  var avg = levels.length > 0
    ? levels.reduce(function (a, b) { return a + b; }, 0) / levels.length
    : 0;

  return {
    id: stationId,
    name: STATIONS[stationId] ? STATIONS[stationId].name : stationId,
    avgCongestion: avg,
    fullCount: fullCount,
    peakHour: peakHour + '시',
    currentLevel: Math.round(avg)
  };
}

function updateSummary(statsRows) {
  var totalAvg = 0;
  var totalFull = 0;
  var peakH = '—';

  if (statsRows.length > 0) {
    var sumAvg = statsRows.reduce(function (a, s) { return a + s.avgCongestion; }, 0);
    totalAvg = sumAvg / statsRows.length;
    totalFull = statsRows.reduce(function (a, s) { return a + s.fullCount; }, 0);
    // Find station with highest avg
    var peak = statsRows.reduce(function (a, s) { return s.avgCongestion > a.avgCongestion ? s : a; });
    peakH = peak.peakHour;
  }

  document.getElementById('avg-congestion').textContent = totalAvg.toFixed(1);
  document.getElementById('full-count').textContent = totalFull;
  document.getElementById('peak-hour').textContent = peakH;
  document.getElementById('station-count').textContent = statsRows.length;
}

// ==================== Chart.js ====================

function initChart() {
  var ctx = document.getElementById('congestion-chart');
  if (!ctx || typeof Chart === 'undefined') {
    if (ctx) {
      ctx.parentElement.innerHTML += '<p class="loading-overlay">Chart.js 로드 실패</p>';
    }
    return;
  }

  congestionChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Array.from({ length: 24 }, function (_, i) { return i + '시'; }),
      datasets: [{
        label: '혼잡도 등급',
        data: DEMO_HOURLY,
        backgroundColor: DEMO_HOURLY.map(function (v) { return CONGESTION[v].color + '80'; }),
        borderColor: DEMO_HOURLY.map(function (v) { return CONGESTION[v].color; }),
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0, max: 3,
          ticks: {
            stepSize: 1,
            callback: function (value) {
              return ['여유', '보통', '혼잡', '매우혼잡'][value] || '';
            }
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              var lvl = Math.min(3, Math.max(0, Math.round(context.raw)));
              return CONGESTION[lvl].label;
            }
          }
        }
      }
    }
  });
}

function updateChart(hourlyData) {
  if (!congestionChart) return;
  congestionChart.data.datasets[0].data = hourlyData;
  congestionChart.data.datasets[0].backgroundColor = hourlyData.map(function (v) {
    var lvl = Math.min(3, Math.max(0, v));
    return CONGESTION[lvl].color + '80';
  });
  congestionChart.data.datasets[0].borderColor = hourlyData.map(function (v) {
    var lvl = Math.min(3, Math.max(0, v));
    return CONGESTION[lvl].color;
  });
  congestionChart.update();
}

// ==================== Doughnut Chart ====================

function initDoughnutChart() {
  var ctx = document.getElementById('congestion-doughnut');
  if (!ctx || typeof Chart === 'undefined') return;

  doughnutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['여유', '보통', '혼잡', '매우혼잡'],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: [
          CONGESTION[0].color,
          CONGESTION[1].color,
          CONGESTION[2].color,
          CONGESTION[3].color
        ],
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '55%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            padding: 16,
            usePointStyle: true,
            pointStyleWidth: 12,
            font: { size: 13 }
          }
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              var total = context.dataset.data.reduce(function (a, b) { return a + b; }, 0);
              var pct = total > 0 ? Math.round(context.raw / total * 100) : 0;
              return context.label + ': ' + context.raw + '시간 (' + pct + '%)';
            }
          }
        }
      }
    }
  });
}

function updateDoughnutChart(hourlyData) {
  if (!doughnutChart) return;

  var counts = [0, 0, 0, 0]; // level 0-3
  hourlyData.forEach(function (v) {
    var lvl = Math.min(3, Math.max(0, Math.round(v)));
    counts[lvl]++;
  });

  doughnutChart.data.datasets[0].data = counts;
  doughnutChart.update();
}

// ==================== Kakao Map ====================

function initMap() {
  var mapEl = document.getElementById('station-map');
  if (!mapEl) return;

  pendingMapStats = DEMO_STATS;
  if (!window.BustagoKakaoMap) {
    mapEl.innerHTML = '<div class="btg-map-message">지도 모듈 로드 실패</div>';
    return;
  }

  // 카카오 키는 .env(KAKAO_MAP_APP_KEY) → /api/public-config 로 받아 주입.
  // 실패/빈 키면 어댑터가 안내 박스로 폴백 (화면 안 깨짐).
  fetchAPI('/public-config').then(function (cfg) {
    if (cfg && cfg.kakao_map_app_key) {
      window.BUSTAGO_KAKAO_APP_KEY = cfg.kakao_map_app_key;
    }
    return window.BustagoKakaoMap.create('station-map', { variant: 'dashboard' });
  }).then(function (map) {
    stationMap = map;
    updateMap(pendingMapStats || DEMO_STATS);
    pendingMapStats = null;
  });
}

function updateMap(statsRows) {
  if (!stationMap) {
    pendingMapStats = statsRows;
    return;
  }

  var markers = [];
  statsRows.forEach(function (stat) {
    var station = STATIONS[stat.id];
    if (!station) return;

    var lvl = Math.min(3, Math.max(0, stat.currentLevel));
    markers.push({
      id: stat.id,
      name: station.name,
      lat: station.lat,
      lng: station.lng,
      level: lvl,
      color: CONGESTION[lvl].color,
      meta: '혼잡도: ' + CONGESTION[lvl].label + ' · 평균 ' + stat.avgCongestion.toFixed(1),
    });
  });

  stationMap.setMarkers(markers);
}

// ==================== Stats Table ====================

function fillStatsTable(statsRows) {
  var tbody = document.getElementById('stats-tbody');
  if (!tbody) return;

  tbody.innerHTML = '';

  statsRows.forEach(function (stat) {
    var lvl = Math.min(3, Math.max(0, stat.currentLevel));
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + stat.name + '</td>' +
      '<td>' + stat.avgCongestion.toFixed(1) + '</td>' +
      '<td>' + stat.fullCount + '회</td>' +
      '<td>' + stat.peakHour + '</td>' +
      '<td><span class="status-badge level-' + lvl + '">' +
      CONGESTION[lvl].label + '</span></td>';
    tbody.appendChild(tr);
  });
}

function setCardValue(id, newVal) {
  var el = document.getElementById(id);
  if (!el) return;
  var current = el.textContent;
  if (current !== String(newVal)) {
    el.classList.remove('flash');   // 재시작 위해
    void el.offsetWidth;             // 강제 reflow → animation restart
    el.classList.add('flash');
    setTimeout(function() { el.classList.remove('flash'); }, 600);
  }
  el.textContent = newVal;
}

async function loadCrowdCount() {
  var sid = stationFilter.value === 'all' ? 'INS01' : stationFilter.value;
  var data = await fetchCrowdCount(sid);
  var dot = document.getElementById('jetson-dot');
  var statusEl = document.getElementById('jetson-status');

  if (data) {
    setCardValue('cnt-waiting', data.current_waiting);
    setCardValue('cnt-in', data.count_in);
    setCardValue('cnt-board', data.count_board);
    document.getElementById('counting-ts').textContent = '기준: ' + data.created_at;

    var diff = Date.now() - new Date(data.created_at).getTime();
    if (diff < JETSON_STALE_MS) {
      dot.className = 'status-dot online';
      statusEl.textContent = 'Jetson 연결됨 (' + sid + ')';
    } else {
      dot.className = 'status-dot stale';
      statusEl.textContent = Math.floor(diff / 1000) + '초 전 수신';
    }
  } else {
    ['cnt-waiting', 'cnt-in', 'cnt-board'].forEach(function(id) {
      document.getElementById(id).textContent = '—';
    });
    dot.className = 'status-dot offline';
    statusEl.textContent = 'Jetson 미연결';
    document.getElementById('counting-ts').textContent = '';
  }
}

async function loadEvents() {
  var sid = stationFilter.value;
  if (sid !== 'DEMO01') return;

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
