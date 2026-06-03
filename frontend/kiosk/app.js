// BUSTAGO Kiosk - 현장 정류장 상태 보드 (대기/진입/탑승/혼잡도). 지도 없음.
(function () {
  var CONGESTION = {
    0: { label: '여유', color: '#22c55e' },
    1: { label: '보통', color: '#eab308' },
    2: { label: '혼잡', color: '#f97316' },
    3: { label: '매우혼잡', color: '#ef4444' },
  };
  var REFRESH_MS = 5000;

  var state = {
    stations: [],
    activeId: 'INS01',
    timer: null,
  };

  function $(id) { return document.getElementById(id); }

  function demoLevel(hour) {
    if ((hour >= 7 && hour <= 9) || (hour >= 17 && hour <= 19)) return 3;
    if (hour >= 10 && hour <= 16) return 1;
    return 0;
  }

  function activeStation() {
    return state.stations.find(function (s) { return s.ars_no === state.activeId; }) ||
      state.stations[0] || null;
  }

  function renderStations() {
    var root = $('stationSwitcher');
    root.innerHTML = state.stations.map(function (s) {
      return '<button class="station-btn' + (s.ars_no === state.activeId ? ' active' : '') +
        '" data-id="' + s.ars_no + '">' + s.station_name + '</button>';
    }).join('');
    root.querySelectorAll('.station-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.activeId = btn.dataset.id;
        renderStations();
        refreshNow();
      });
    });
  }

  function setStatus(count) {
    if (!count) {
      $('waitingCount').textContent = '—';
      $('inCount').textContent = '—';
      $('boardCount').textContent = '—';
      $('statusMeta').textContent = '카운팅 데이터 없음';
      return;
    }
    $('waitingCount').textContent = count.current_waiting;
    $('inCount').textContent = count.count_in;
    $('boardCount').textContent = count.count_board;
    $('statusMeta').textContent = '기준: ' + count.created_at;
  }

  function setPrediction(data) {
    var hour = new Date().getHours();
    var level = data && data.prediction ? data.prediction.level : demoLevel(hour);
    var info = CONGESTION[level] || CONGESTION[0];
    $('congestionLabel').textContent = info.label;
    $('congestionLabel').style.color = info.color;
  }

  async function refreshNow() {
    var station = activeStation();
    if (!station) return;
    $('activeStationName').textContent = station.station_name;
    if (state.timer) clearTimeout(state.timer);

    var now = new Date();
    var jsDay = now.getDay();
    var weekday = jsDay === 0 ? 6 : jsDay - 1;
    var count = await fetchCrowdCount(station.ars_no);
    setStatus(count);
    var prediction = await fetchPredict(station.ars_no, now.getHours(), weekday);
    setPrediction(prediction);
    state.timer = setTimeout(refreshNow, REFRESH_MS);
  }

  async function init() {
    var stations = await fetchStations();
    state.stations = Array.isArray(stations) ? stations : [];
    if (!state.stations.find(function (s) { return s.ars_no === state.activeId; }) && state.stations.length) {
      state.activeId = state.stations[0].ars_no;
    }
    renderStations();
    refreshNow();
  }

  init();
})();
