// BUSTAGO Student PWA - App Logic
// 탭 전환, 노선 검색/즐겨찾기, 바텀시트 렌더링, 테마 토글, SW 등록을 담당함

// =============================================================
// 상수
// =============================================================

// 혼잡도 단계 → 라벨/색상/안내 문구 매핑으로 사용됨
const CONGESTION = {
  0: { label: '여유', color: '#22c55e', msg: '대기 인원 적음 · 탑승 가능성 높음', title: '지금 탑승하세요!' },
  1: { label: '보통', color: '#eab308', msg: '평균적인 혼잡도입니다',           title: '지금 탑승하세요!' },
  2: { label: '혼잡', color: '#f97316', msg: '혼잡이 예상됩니다',                title: '다음 시간대를 추천합니다' },
  3: { label: '매우혼잡', color: '#ef4444', msg: '매우 혼잡합니다',              title: '다음 시간대를 추천합니다' },
};

// 버스 유형 → 배지 라벨/색상 매핑으로 사용됨 (저상/고속/일반)
const BUS_TYPE = {
  low:     { label: '저상', color: '#0ea5e9' },
  express: { label: '고속', color: '#a855f7' },
  normal:  { label: '일반', color: '#64748b' },
};

// 바텀시트 닫힘 애니메이션(transform 0.37s)과 동기화 — 재오픈 가드로 사용됨
const SHEET_ANIM_MS = 370;
const STATUS_REFRESH_MS = 10000;

// =============================================================
// 상태
// =============================================================

// 앱 전역 상태 — 탭/검색어/즐겨찾기/시트/테마 추적용으로 사용됨
const state = {
  tab: 'fav',
  query: '',
  stations: [],            // 정렬된 정류장 목록
  busstopMap: {},          // ars_no → gj_busstop_id
  activeStation: null,     // { ars_no, station_name }
  routeCards: [],          // 현재 activeStation의 노선 카드 (검색 탭)
  favCards: [],            // 즐겨찾기 탭에 표시 중인 라이브 카드 (시트 진입용)
  favs: new Map(JSON.parse(localStorage.getItem('bustago_favs_v2') || '[]')), // id → fav객체
  sheetRoute: null,
  sheetOpen: false,
  closing: false,
  reopenTimer: null,
  arrivalTimer: null,      // 시트 도착 30초 갱신
  statusTimer: null,       // 홈 정류장 현황 10초 갱신
  theme: localStorage.getItem('bustago_theme') || 'light',
};

// =============================================================
// DOM 캐시
// =============================================================

const $ = (id) => document.getElementById(id);

// 탭/패널 — 최상단 네비게이션 전환에 사용됨
const tabsEl       = $('tabs');
const panels       = document.querySelectorAll('.tab-panel');

// 즐겨찾기 패널 요소 — 노선 카드 목록과 빈 상태 토글에 사용됨
const favListEl    = $('favList');
const favEmptyEl   = $('favEmpty');

// 노선 검색 패널 요소 — 검색 입력/결과 카운트/카드 목록 렌더링에 사용됨
const routeListEl   = $('routeList');
const searchInput   = $('searchInput');
const searchCountEl = $('searchCount');
const stationListEl  = $('stationList');
const stationCtxEl    = $('stationCtx');
const stationCtxBtn   = $('stationCtxBtn');
const stationCtxName  = $('stationCtxName');
const stationStatusCard = $('stationStatusCard');
const stationStatusName = $('stationStatusName');
const stationStatusDot  = $('stationStatusDot');
const statusWaitingEl   = $('statusWaiting');
const statusInEl        = $('statusIn');
const statusBoardEl     = $('statusBoard');
const stationStatusMeta = $('stationStatusMeta');

// 노선 상세 바텀시트 요소 — 노선 클릭 시 표시되는 패널/배경/핸들/즐겨찾기 버튼
const sheetEl         = $('routeSheet');
const sheetBackdropEl = $('sheetBackdrop');
const sheetHandleEl   = $('sheetHandle');
const sheetFavBtn     = $('sheetFavBtn');

// 서비스 정보 바텀시트 요소 — '더보기 → 서비스 정보' 클릭 시 표시됨
const infoSheetEl    = $('infoSheet');
const infoBackdropEl = $('infoBackdrop');
const infoHandleEl   = $('infoHandle');

// =============================================================
// 부트스트랩
// =============================================================

// 저장된 테마를 즉시 적용하고 초기 화면(즐겨찾기/노선 목록)을 그림
document.body.setAttribute('data-theme', state.theme);
updateThemeUI();

(async function init() {
  var r = await Data.loadStations();
  state.stations = r.stations;
  state.busstopMap = r.busstopMap;
  // 기본 정류장: INS01 → 첫 광주 → 첫 번째
  state.activeStation =
    state.stations.find(function (s) { return s.ars_no === 'INS01'; }) ||
    state.stations.find(function (s) { return /^GJ/.test(s.ars_no); }) ||
    state.stations[0] || null;
  if (state.activeStation) {
    state.routeCards = await Data.loadRoutesForStation(
      state.activeStation.ars_no, state.activeStation.station_name);
  }
  renderFavs();
  renderStationContext();
  refreshStationStatus();
  renderSearchResults();
})();

// =============================================================
// 탭 전환
// =============================================================

// 탭 클릭 시 active 클래스 토글 — 패널 표시 전환에 사용됨
tabsEl.addEventListener('click', (e) => {
  const btn = e.target.closest('.tab');
  if (!btn) return;
  state.tab = btn.dataset.tab;
  tabsEl.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b === btn));
  panels.forEach((p) => p.classList.toggle('active', p.dataset.panel === state.tab));
});

// =============================================================
// 검색
// =============================================================

// =============================================================
// 카드 렌더링
// =============================================================

// 검색 input: 정류장 검색 (activeStation 미선택 상태에서) 또는 노선 필터
searchInput.addEventListener('input', (e) => {
  state.query = e.target.value;
  renderSearchResults();
});

// 정류장 변경 버튼: 노선 목록 → 정류장 검색 모드로
stationCtxBtn.addEventListener('click', () => {
  state.activeStation = null;
  state.routeCards = [];
  state.query = '';
  searchInput.value = '';
  renderStationContext();
  refreshStationStatus();
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

function refreshStationStatus() {
  if (state.statusTimer) { clearTimeout(state.statusTimer); state.statusTimer = null; }

  const s = state.activeStation;
  if (!s) {
    stationStatusCard.hidden = true;
    return;
  }

  stationStatusCard.hidden = false;
  stationStatusName.textContent = s.station_name;
  stationStatusDot.className = 'live-dot';
  stationStatusMeta.textContent = '데이터 확인 중';

  Data.loadStationStatus(s.ars_no).then((status) => {
    if (!state.activeStation || state.activeStation.ars_no !== s.ars_no) return;
    renderStationStatus(status, s);
    state.statusTimer = setTimeout(refreshStationStatus, STATUS_REFRESH_MS);
  }).catch(() => {
    if (!state.activeStation || state.activeStation.ars_no !== s.ars_no) return;
    renderStationStatus(null, s);
    state.statusTimer = setTimeout(refreshStationStatus, STATUS_REFRESH_MS);
  });
}

function renderStationStatus(status, station) {
  stationStatusCard.hidden = false;
  stationStatusName.textContent = station.station_name;

  if (!status) {
    stationStatusDot.className = 'live-dot';
    statusWaitingEl.textContent = '—';
    statusInEl.textContent = '—';
    statusBoardEl.textContent = '—';
    stationStatusMeta.textContent = '카운팅 데이터 없음';
    return;
  }

  stationStatusDot.className = 'live-dot ' + (status.stale ? 'stale' : 'online');
  statusWaitingEl.textContent = status.waiting;
  statusInEl.textContent = status.countIn;
  statusBoardEl.textContent = status.countBoard;
  if (status.ageSec == null) {
    stationStatusMeta.textContent = '수신 시각 확인 불가';
  } else if (status.ageSec < 5) {
    stationStatusMeta.textContent = '방금 업데이트';
  } else {
    stationStatusMeta.textContent = status.ageSec + '초 전 수신';
  }
}

// 정류장 한 줄 HTML
function stationItemHTML(s) {
  return '<div class="station-item card" role="button" tabindex="0" data-ars="' + esc(s.ars_no) + '">' +
    '<span class="si-name">' + esc(s.station_name) + '</span>' +
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
      renderStationContext();
      refreshStationStatus();
      const cards = await Data.loadRoutesForStation(s.ars_no, s.station_name);
      if (!state.activeStation || state.activeStation.ars_no !== s.ars_no) return; // 경쟁 가드
      state.routeCards = cards;
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
  state.favCards = cards;
  favListEl.innerHTML = cards.map(routeCardHTML).join('');
  bindRouteCards(favListEl);
}

// innerHTML 삽입 전 텍스트/속성 값 이스케이프 (XSS 방지)
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// 단일 노선 카드의 HTML 문자열을 만드는 데 사용됨
// 주의: route-card는 div + role="button"으로 사용 — 내부에 별(span) 버튼을 둘 수 있도록 함
//       (button 중첩 시 브라우저가 안쪽 버튼을 밖으로 빼내는 문제 회피)
function routeCardHTML(r) {
  const c = CONGESTION[r.level] || CONGESTION[0];
  const t = BUS_TYPE[r.type];
  const isFav = state.favs.has(r.id);
  return `
    <div class="route-card" role="button" tabindex="0" data-id="${esc(r.id)}">
      <div class="rc-left">
        <div class="rc-icon" style="background:${t.color}26;color:${t.color}">🚌</div>
        <div>
          <div class="rc-name-row">
            <span class="rc-name">${esc(r.name)}</span>
            <span class="bus-badge" style="background:${t.color}">${t.label}</span>
          </div>
          <div class="rc-dir">${esc(r.from)} → ${esc(r.to)}</div>
        </div>
      </div>
      <div class="rc-right">
        <span class="cong-badge" style="background:${c.color}">${c.label}</span>
        <span class="rc-fav ${isFav ? 'on' : 'off'}" data-fav="${esc(r.id)}" role="button" aria-label="즐겨찾기">${isFav ? '★' : '☆'}</span>
      </div>
    </div>
  `;
}

// innerHTML 갱신 후 카드/별 클릭 이벤트를 다시 연결하는 데 사용됨
function bindRouteCards(root) {
  root.querySelectorAll('.route-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      if (e.target.closest('.rc-fav')) return;
      const r = findCardById(card.dataset.id);
      if (r) openRoute(r);
    });
  });
  root.querySelectorAll('.rc-fav').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const r = findCardById(btn.dataset.fav);
      if (r) toggleFav(r);
    });
  });
}

// 현재 화면에 존재하는 카드 객체를 id로 찾음 (검색 결과 또는 즐겨찾기)
function findCardById(id) {
  return state.routeCards.find((c) => c.id === id)
      || state.favCards.find((c) => c.id === id)
      || [...state.favs.values()].map(favToCardStub).find((c) => c.id === id);
}
function favToCardStub(f) {
  return { id: f.id, stationId: f.stationId, stationName: f.stationName,
           name: f.routeName, routeNo: f.routeNo, from: f.stationName, to: '-',
           level: 0, type: 'normal', recommended: false };
}

// 즐겨찾기 상태를 토글하고 localStorage에 영속화하는 데 사용됨
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

// =============================================================
// 노선 상세 바텀시트
// =============================================================

// 노선 카드 클릭 진입점 — 시트의 열림/닫힘 상태에 따라 분기됨
// 1) 시트가 이미 열려 있으면 콘텐츠만 교체 (애니메이션 재실행 없음)
// 2) 닫히는 중이면 애니메이션 종료 후 열림
// 3) 그 외에는 즉시 열림
function openRoute(r) {
  if (state.reopenTimer) { clearTimeout(state.reopenTimer); state.reopenTimer = null; }
  if (state.sheetOpen) {
    state.sheetRoute = r;
    renderSheet();
    return;
  }
  if (state.closing) {
    state.reopenTimer = setTimeout(() => {
      state.sheetRoute = r;
      renderSheet();
      showSheet();
    }, SHEET_ANIM_MS);
    return;
  }
  state.sheetRoute = r;
  renderSheet();
  showSheet();
}

// 시트 표시 — open 클래스 부착으로 transform 애니메이션을 트리거하는 데 사용됨
function showSheet() {
  state.sheetOpen = true;
  sheetEl.classList.add('open');
  sheetBackdropEl.classList.add('open');
  sheetEl.setAttribute('aria-hidden', 'false');
}

// 시트 닫기 — closing 플래그로 SHEET_ANIM_MS 동안 재오픈 가드를 거는 데 사용됨
function closeSheet() {
  state.sheetOpen = false;
  sheetEl.classList.remove('open');
  sheetBackdropEl.classList.remove('open');
  sheetEl.setAttribute('aria-hidden', 'true');
  if (state.arrivalTimer) { clearTimeout(state.arrivalTimer); state.arrivalTimer = null; }
  state.closing = true;
  setTimeout(() => { state.closing = false; }, SHEET_ANIM_MS);
}

// 배경을 누르면 시트가 닫히도록 연결
sheetBackdropEl.addEventListener('click', closeSheet);

// 핸들 드래그(아래로 80px 이상)로 시트를 닫는 데 사용됨
attachDragClose(sheetEl, sheetHandleEl, closeSheet);

// 공통 드래그-투-클로즈 헬퍼 — 노선 시트와 정보 시트에서 재사용됨
// touch + mouse 이벤트 모두 지원
function attachDragClose(panel, handle, onClose) {
  let startY = null;
  let dy = 0;

  const onStart = (e) => {
    startY = (e.touches ? e.touches[0].clientY : e.clientY);
    dy = 0;
    panel.style.transition = 'none';      // 드래그 중에는 transition 비활성화 (지연 방지)
  };
  const onMove = (e) => {
    if (startY === null) return;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    dy = Math.max(0, y - startY);          // 위로는 끌리지 않도록 0으로 클램프
    panel.style.transform = `translateY(${dy}px)`;
  };
  const onEnd = () => {
    if (startY === null) return;
    panel.style.transition = '';
    panel.style.transform  = '';           // 인라인 transform 제거 → CSS 기본값 복원
    if (dy > 80) onClose();                // 80px 임계값을 넘어가면 닫기
    startY = null; dy = 0;
  };

  handle.addEventListener('touchstart', onStart, { passive: true });
  handle.addEventListener('touchmove',  onMove,  { passive: true });
  handle.addEventListener('touchend',   onEnd);
  handle.addEventListener('mousedown', (e) => {
    onStart(e);
    const mm = (ev) => onMove(ev);
    const mu = () => {
      onEnd();
      window.removeEventListener('mousemove', mm);
      window.removeEventListener('mouseup',   mu);
    };
    window.addEventListener('mousemove', mm);
    window.addEventListener('mouseup',   mu);
  });
}

// 시트 기본 정보(즉시) + 라이브 데이터(비동기) 렌더
function renderSheet() {
  const r = state.sheetRoute;
  if (!r) return;
  const c = CONGESTION[r.level] || CONGESTION[0];
  const t = BUS_TYPE[r.type];

  $('sheetRouteName').textContent = r.name;
  const tb = $('sheetBusType');
  tb.textContent = t.label; tb.style.background = t.color;
  $('sheetRouteDir').textContent = `${r.from} → ${r.to}`;

  // 출발→도착 2점 트랙
  $('sheetStops').innerHTML = [r.from, r.to].map((s, idx) => {
    const cls = idx === 0 ? 'past' : 'future';
    return `<div class="stop-item"><div class="stop-dot ${cls}"></div>` +
           `<span class="stop-name ${cls}">${esc(s)}</span></div>`;
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
  if (!state.sheetOpen || !state.sheetRoute || state.sheetRoute.id !== r.id) return;
  const nowIdx = 0; // 첫 막대가 현재 시각
  $('sheetForecast').innerHTML = fc.levels.map((lvl, i) => {
    const info = CONGESTION[lvl] || CONGESTION[0];
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
  if (!state.sheetOpen || !state.sheetRoute || state.sheetRoute.id !== r.id) return;

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

// 시트 헤더의 즐겨찾기 버튼(★ / ☆) 시각 상태를 동기화하는 데 사용됨
function updateSheetFavBtn() {
  const r = state.sheetRoute;
  if (!r) return;
  const on = state.favs.has(r.id);
  sheetFavBtn.classList.toggle('on', on);
  sheetFavBtn.querySelector('.fav-star').textContent = on ? '★' : '☆';
  sheetFavBtn.querySelector('.fav-text').textContent = on ? '즐겨찾기' : '추가';
}
sheetFavBtn.addEventListener('click', () => {
  if (state.sheetRoute) toggleFav(state.sheetRoute);
});

// =============================================================
// 서비스 정보 바텀시트
// =============================================================

// '더보기 → 서비스 정보' 클릭 시 열기/닫기에 사용됨
function openInfo() {
  infoSheetEl.classList.add('open');
  infoBackdropEl.classList.add('open');
}
function closeInfo() {
  infoSheetEl.classList.remove('open');
  infoBackdropEl.classList.remove('open');
}
infoBackdropEl.addEventListener('click', closeInfo);
attachDragClose(infoSheetEl, infoHandleEl, closeInfo);

// =============================================================
// 더보기 액션
// =============================================================

// data-action 속성 기반으로 '서비스 정보' / '문의하기' 동작을 분기하는 데 사용됨
// 문의하기 → GitHub Issues 새 탭으로 안내
document.querySelectorAll('[data-action]').forEach((b) => {
  b.addEventListener('click', () => {
    const act = b.dataset.action;
    if (act === 'info')    openInfo();
    if (act === 'contact') window.open('https://github.com/HUNMINRYU/bustago/issues', '_blank', 'noopener,noreferrer');
  });
});

// =============================================================
// 테마 (라이트/다크) — body[data-theme]로 CSS 변수 토글
// =============================================================

$('themeToggle').addEventListener('click', () => {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', state.theme);
  localStorage.setItem('bustago_theme', state.theme);
  updateThemeUI();
});

// 토글 아이콘/라벨을 현재 테마에 맞게 갱신하는 데 사용됨
function updateThemeUI() {
  $('themeIcon').textContent  = state.theme === 'dark' ? '🌙' : '☀️';
  $('themeLabel').textContent = state.theme === 'dark' ? '다크 모드' : '라이트 모드';
}

// =============================================================
// Service Worker 등록
// =============================================================

// 오프라인 캐시 + 앱 설치 지원에 사용됨 — 실패해도 앱 동작에는 영향 없음
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () =>
    navigator.serviceWorker.register('service-worker.js').catch(() => {})
  );
}
