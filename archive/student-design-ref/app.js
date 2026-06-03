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

// 바텀시트의 시간대별 막대 그래프 데이터로 사용됨
// (실제 API 연동 시 fetchPredict() 결과로 대체할 것)
const FORECAST_HOURS   = [8, 9, 10, 11, 12, 13];
const FORECAST_LEVELS  = [1, 3, 2, 0, 0, 1];
const CURRENT_HOUR_IDX = 3;

// 노선 목록 더미 데이터 — API 미연동 상태의 화면 확인용으로 사용됨
// 실제 운영 시 광주 BIS API 응답으로 교체할 것
const MOCK_ROUTES = [
  { id: 'songjeong-51', name: '송정51', from: '송정역',   to: '광주역',     level: 0, type: 'low',
    stops: ['송정역','공항','운남','월곡','광주역','동구청'], currentStopIndex: 3, etaMin: 3, etaStops: 2 },
  { id: 'first-18',     name: '첨단18', from: '첨단',     to: '전남대',     level: 2, type: 'normal',
    stops: ['첨단','첨단2','신용','운암','전남대','후문'],     currentStopIndex: 2, etaMin: 7, etaStops: 4 },
  { id: 'seat02',       name: '좌석02', from: '광주역',   to: '터미널',     level: 1, type: 'express',
    stops: ['광주역','충장로','금남로','터미널'],              currentStopIndex: 1, etaMin: 5, etaStops: 3 },
  { id: 'suwan27',      name: '수완27', from: '수완지구', to: '광천터미널', level: 3, type: 'low',
    stops: ['수완지구','운남','광천터미널'],                   currentStopIndex: 0, etaMin: 12, etaStops: 6 },
  { id: 'no160',        name: '160',    from: '송원대',   to: '조선대',     level: 0, type: 'normal',
    stops: ['송원대','양림','충장로','조선대'],                currentStopIndex: 2, etaMin: 2, etaStops: 1 },
];

// 바텀시트 닫힘 애니메이션(transform 0.37s)과 동기화 — 재오픈 가드로 사용됨
const SHEET_ANIM_MS = 370;

// =============================================================
// 상태
// =============================================================

// 앱 전역 상태 — 탭/검색어/즐겨찾기/시트/테마 추적용으로 사용됨
const state = {
  tab: 'fav',                                                                  // 활성 탭 ID
  query: '',                                                                   // 검색어
  favIds: new Set(JSON.parse(localStorage.getItem('bustago_favs') || '[]')),   // 즐겨찾기 id 집합 (localStorage 영속)
  sheetRoute: null,                                                            // 바텀시트에 표시 중인 노선
  sheetOpen: false,                                                            // 바텀시트 열림 여부
  closing: false,                                                              // 닫힘 애니메이션 진행 중 플래그 — 재오픈 가드용
  reopenTimer: null,                                                           // 닫힘 직후 재오픈 예약 타이머
  theme: localStorage.getItem('bustago_theme') || 'light',                     // 'light' | 'dark'
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
renderFavs();
renderRouteList();

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

// 입력 이벤트 → state.query 갱신 후 노선 목록 재렌더링
searchInput.addEventListener('input', (e) => {
  state.query = e.target.value;
  renderRouteList();
});

// 노선 이름/출발지/도착지를 부분 일치로 필터링하는 데 사용됨
function filterRoutes() {
  const q = state.query.trim().toLowerCase();
  if (!q) return MOCK_ROUTES;
  return MOCK_ROUTES.filter((r) =>
    r.name.toLowerCase().includes(q) ||
    r.from.toLowerCase().includes(q) ||
    r.to.toLowerCase().includes(q)
  );
}

// =============================================================
// 카드 렌더링
// =============================================================

// 노선 검색 결과를 다시 그릴 때 사용됨
function renderRouteList() {
  const routes = filterRoutes();
  searchCountEl.textContent = routes.length;
  routeListEl.innerHTML = routes.map(routeCardHTML).join('');
  bindRouteCards(routeListEl);
}

// 즐겨찾기 탭의 노선 목록을 그릴 때 사용됨 (비어 있으면 empty-state 표시)
function renderFavs() {
  const favs = MOCK_ROUTES.filter((r) => state.favIds.has(r.id));
  favEmptyEl.classList.toggle('show', favs.length === 0);
  favListEl.innerHTML = favs.map((r) => routeCardHTML(r)).join('');
  bindRouteCards(favListEl);
}

// 단일 노선 카드의 HTML 문자열을 만드는 데 사용됨
// 주의: route-card는 div + role="button"으로 사용 — 내부에 별(span) 버튼을 둘 수 있도록 함
//       (button 중첩 시 브라우저가 안쪽 버튼을 밖으로 빼내는 문제 회피)
function routeCardHTML(r) {
  const c = CONGESTION[r.level];
  const t = BUS_TYPE[r.type];
  const isFav = state.favIds.has(r.id);
  return `
    <div class="route-card" role="button" tabindex="0" data-id="${r.id}">
      <div class="rc-left">
        <div class="rc-icon" style="background:${t.color}26;color:${t.color}">🚌</div>
        <div>
          <div class="rc-name-row">
            <span class="rc-name">${r.name}</span>
            <span class="bus-badge" style="background:${t.color}">${t.label}</span>
          </div>
          <div class="rc-dir">${r.from} → ${r.to}</div>
        </div>
      </div>
      <div class="rc-right">
        <span class="cong-badge" style="background:${c.color}">${c.label}</span>
        <span class="rc-fav ${isFav ? 'on' : 'off'}" data-fav="${r.id}" role="button" aria-label="즐겨찾기">${isFav ? '★' : '☆'}</span>
      </div>
    </div>
  `;
}

// innerHTML 갱신 후 카드/별 클릭 이벤트를 다시 연결하는 데 사용됨
function bindRouteCards(root) {
  root.querySelectorAll('.route-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      // 별을 눌렀을 때는 시트가 열리지 않도록 무시
      if (e.target.closest('.rc-fav')) return;
      const r = MOCK_ROUTES.find((x) => x.id === card.dataset.id);
      if (r) openRoute(r);
    });
  });
  root.querySelectorAll('.rc-fav').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();   // 카드 클릭으로 시트가 열리는 것을 방지
      toggleFav(btn.dataset.fav);
    });
  });
}

// 즐겨찾기 상태를 토글하고 localStorage에 영속화하는 데 사용됨
function toggleFav(id) {
  if (state.favIds.has(id)) state.favIds.delete(id);
  else state.favIds.add(id);
  localStorage.setItem('bustago_favs', JSON.stringify([...state.favIds]));
  renderFavs();
  renderRouteList();
  if (state.sheetRoute && state.sheetRoute.id === id) updateSheetFavBtn();
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

// 시트 내부의 모든 동적 영역을 현재 state.sheetRoute 기준으로 다시 채우는 데 사용됨
function renderSheet() {
  const r = state.sheetRoute;
  if (!r) return;
  const c = CONGESTION[r.level];
  const t = BUS_TYPE[r.type];

  // 헤더: 노선명 + 버스 유형 배지
  $('sheetRouteName').textContent = r.name;
  const tb = $('sheetBusType');
  tb.textContent = t.label;
  tb.style.background = t.color;

  // 출발 → 도착 부 라벨
  $('sheetRouteDir').textContent = `${r.from} → ${r.to}`;

  // 정류장 진행 트랙 — past/current/future 클래스로 시각 상태 구분
  $('sheetStops').innerHTML = r.stops.map((s, idx) => {
    const cls = idx < r.currentStopIndex ? 'past' : (idx === r.currentStopIndex ? 'current' : 'future');
    return `
      <div class="stop-item">
        <div class="stop-dot ${cls}"></div>
        <span class="stop-name ${cls}">${s}</span>
      </div>
    `;
  }).join('');

  // 현재 혼잡도 원 + 안내 문구
  const cc = $('sheetCongCircle');
  cc.textContent = c.label;
  cc.style.background = c.color;
  $('sheetCongTitle').textContent = c.title;
  $('sheetCongMsg').textContent   = c.msg;

  // 시간대별 수직 막대 그래프 — 현재 시간(CURRENT_HOUR_IDX)은 흰 outline + 글로우로 강조됨
  $('sheetForecast').innerHTML = FORECAST_LEVELS.map((lvl, i) => {
    const info  = CONGESTION[lvl];
    const h     = ((lvl + 1) / 4) * 100;  // 레벨(0~3) → 높이 비율(25~100%)
    const isNow = i === CURRENT_HOUR_IDX;
    return `<div class="fc-col">
      <div class="fc-bar ${isNow ? 'current' : ''}" style="height:${h}%;background:${info.color};${isNow ? `box-shadow:0 0 12px ${info.color}80;` : ''}"></div>
    </div>`;
  }).join('');
  $('sheetForecastLabels').innerHTML = FORECAST_HOURS.map((h, i) =>
    `<span class="fc-label ${i === CURRENT_HOUR_IDX ? 'current' : ''}">${h}시${i === CURRENT_HOUR_IDX ? ' ←' : ''}</span>`
  ).join('');

  // 실시간 도착 행 — 추후 광주 BIS API 연동 시 다중 행으로 확장 예정
  $('sheetArrName').textContent = r.name;
  $('sheetArrDest').textContent = `→ ${r.to}`;
  $('sheetArrMin').textContent  = `${r.etaMin}분`;
  $('sheetArrStop').textContent = `${r.etaStops}정류장`;

  updateSheetFavBtn();
}

// 시트 헤더의 즐겨찾기 버튼(★ / ☆) 시각 상태를 동기화하는 데 사용됨
function updateSheetFavBtn() {
  const r = state.sheetRoute;
  if (!r) return;
  const on = state.favIds.has(r.id);
  sheetFavBtn.classList.toggle('on', on);
  sheetFavBtn.querySelector('.fav-star').textContent = on ? '★' : '☆';
  sheetFavBtn.querySelector('.fav-text').textContent = on ? '즐겨찾기' : '추가';
}
sheetFavBtn.addEventListener('click', () => {
  if (state.sheetRoute) toggleFav(state.sheetRoute.id);
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
