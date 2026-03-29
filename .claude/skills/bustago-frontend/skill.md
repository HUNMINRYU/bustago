---
name: bustago-frontend
description: "BUSTAGO Frontend 구현 스킬. 학생용 모바일 PWA(혼잡도 실시간 표시, 탑승 추천)와 운영자용 PC 대시보드(Chart.js 시간대별 통계, Leaflet.js 정류장 지도). Vanilla HTML/CSS/JS, Chart.js, Leaflet.js, PWA manifest, Service Worker 구현 시 반드시 이 스킬을 사용."
---

# BUSTAGO Frontend

## 디렉토리 구조

```
frontend/
├── student/
│   ├── index.html      # 메인 PWA 화면
│   ├── style.css       # 모바일 우선 스타일
│   ├── app.js          # 정류장 선택, 예측 호출, UI 업데이트
│   ├── manifest.json   # PWA 매니페스트
│   └── service-worker.js
├── admin/
│   ├── index.html      # 대시보드
│   ├── style.css       # PC 우선 스타일
│   └── dashboard.js    # Chart.js + Leaflet.js + API 호출
└── shared/
    └── api.js          # API 호출 래퍼
```

## CDN 의존성
```html
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<!-- Leaflet.js -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js"></script>
```

## 혼잡도 색상 매핑
```javascript
const CONGESTION = {
  0: { label: '여유', color: '#4CAF50', icon: '🟢', bg: '#E8F5E9',
       message: '여유로운 시간대입니다. 탑승을 추천합니다.' },
  1: { label: '보통', color: '#FFC107', icon: '🟡', bg: '#FFF8E1',
       message: '평균적인 혼잡도입니다.' },
  2: { label: '혼잡', color: '#FF9800', icon: '🟠', bg: '#FFF3E0',
       message: '혼잡이 예상됩니다. 다음 시간대를 추천합니다.' },
  3: { label: '매우혼잡', color: '#F44336', icon: '🔴', bg: '#FFEBEE',
       message: '매우 혼잡합니다. 대안 교통을 고려하세요.' }
};
```

## 정류장 좌표 (Leaflet.js용)
```javascript
const STATIONS = {
  '02142': { name: '명동.롯데영프라자', lat: 37.5636, lng: 126.9850 },
  '22011': { name: '지하철2호선강남역', lat: 37.4979, lng: 127.0276 },
  '22009': { name: '신분당선강남역', lat: 37.4988, lng: 127.0286 },
  '22012': { name: '지하철2호선강남역(반대편)', lat: 37.4975, lng: 127.0270 }
};
```

## shared/api.js 패턴
```javascript
const API_BASE = 'http://localhost:5000/api';

async function fetchAPI(endpoint, params = {}) {
  const url = new URL(`${API_BASE}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (data.status !== 'ok') throw new Error(data.message);
    return data.data;
  } catch (e) {
    console.error(`API Error: ${endpoint}`, e);
    return null;
  }
}
```

## 학생 PWA 핵심 화면
1. **정류장 선택** -- 드롭다운 또는 지도 탭
2. **혼잡도 표시** -- 큰 원형 인디케이터 (색상 + 레이블 + 아이콘)
3. **탑승 추천** -- "지금 탑승" / "다음 시간대 추천" 카드
4. **시간대별 예측** -- 간단한 바 차트 (향후 6시간)

## 운영자 대시보드 핵심 화면
1. **시간대별 혼잡도 추이** -- Chart.js line chart (24시간)
2. **정류장 지도** -- Leaflet.js 마커 (혼잡도 색상)
3. **노선별 통계** -- HTML 테이블 (평균 혼잡도, 만차 횟수)
