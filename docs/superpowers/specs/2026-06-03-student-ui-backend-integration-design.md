# 학생용 새 UI ⇄ 실제 백엔드 연결 설계

- 작성일: 2026-06-03
- 작성자: HUNMINRYU (같이타요 / 광주대 캡스톤디자인 RISE)
- 상태: 설계 확정 (구현 계획 대기)

## 1. 배경 / 문제

루트 `student/` 폴더에 새로 만든 학생용 PWA는 디자인이 완성되어 있으나
**100% 가짜 데이터(`MOCK_ROUTES`)**로만 동작하며 백엔드에 연결되어 있지 않다.

한편 기존 운영 버전 `frontend/student/`는 실제 백엔드(`frontend/shared/api.js`)에
연결되어 있으나 화면이 단순하다(정류장 드롭다운 1개 중심).

**목표:** 새 디자인을 운영 폴더에 이식하고 실제 백엔드 데이터에 연결한다.

### 핵심 긴장점
- 새 UI는 **노선 중심**(노선 카드 목록, 정류장 선택 UI 없음)
- 백엔드 혼잡도 모델은 **정류장 중심**(`/predict?station_id&hour`)
- 광주 BIS 도착정보는 **정류장(버스정류소) 단위**

이 차이를 어떻게 연결하느냐가 설계의 본질이다.

## 2. 확정된 의사결정

| 항목 | 결정 |
|---|---|
| 옛 `frontend/student` 처리 | **교체**(retire). 새 디자인으로 덮어씀 |
| 데이터 연결 모델 | **즐겨찾기 = (정류장 + 노선) 쌍** 단위로 바인딩 |
| 노선 검색 흐름 | **정류장 먼저 선택 → 그 정류장의 노선 목록** (실제 데이터 100%) |
| 정류장 진행 트랙 | **A안**: 출발→도착 2점 트랙 + "🚌 운행 중 N대" 라이브 표시 (`bus_location` 대수 활용) |
| 날씨 카드 | **제거** (`/weather/current` 엔드포인트 없음) |
| 구현 접근 | **Approach A**: 새 UI = 뷰 계층, `data.js` 어댑터 1개 추가, `shared/api.js` 재사용 |

## 3. 아키텍처

작업 위치: `frontend/student/` (옛 버전 교체). 백엔드·nginx·admin 미변경.

```
frontend/student/
  index.html        ← 새 탭형 마크업 (날씨 카드 제거; script 순서: api.js → data.js → app.js)
  style.css         ← 새 폴리시드 스타일 (루트 student/에서 1:1)
  app.js            ← 새 UI 로직 + 실데이터 연결 + 정류장-우선 검색 + (정류장,노선) 즐겨찾기
  data.js           ← [신규] 어댑터: 백엔드 응답 → UI 뷰모델 (API를 아는 유일한 곳)
  service-worker.js ← 캐시 목록 갱신(+data.js, +../shared/api.js), CACHE 'bustago-v2'로 bump
  manifest.json     ← 새 것
frontend/shared/api.js   ← 그대로 재사용 (필요한 엔드포인트 모두 보유)
```

### 관심사 분리 (핵심 원칙)
- `app.js`(뷰)는 **절대 `fetch`를 직접 호출하지 않는다.** `data.js`만 호출한다.
- `data.js`(어댑터)가 `shared/api.js`를 호출하고 뷰모델을 반환한다.
- BIS 등 위험 요소가 `data.js` 한 곳에 격리 → 테스트/교체 용이.

## 4. 뷰모델 (data.js ↔ app.js 계약)

`data.js`는 기존 `MOCK_ROUTES`와 동일한 모양의 노선 객체를 생성해
기존 렌더 코드를 거의 그대로 재사용한다.

```js
{
  id: `${stationId}::${routeName}`,   // 즐겨찾기 키 = 정류장+노선 쌍
  stationId, stationName,
  name: routeName, routeNo,
  from: stationName,
  to: end_stations.join('/'),
  level,                  // 0–3, route-recommend congestion.level
  type: 'normal',         // 기본값; BIS 도착의 LOW_BUS면 '저상', 이름에 좌석/급행이면 그에 맞게
  recommended,            // route-recommend
  // 상세 필드 — 시트 열릴 때 지연 로딩:
  stops, currentStopIndex, forecast, arrivals
}
```

### 버스 유형(type) 결정 규칙
- 카드 목록 단계: 백엔드 노선 데이터에 유형 정보 없음 → 기본 `'normal'`(일반).
- 상세 시트 단계: BIS 도착 항목의 `LOW_BUS == 1`이면 `'low'`(저상)로 승격.
- 노선명에 `좌석`/`급행` 포함 시 `'express'`.

## 5. 데이터 흐름 / 내비게이션 (정류장 우선)

**앱 초기화:** `/stations` 1회 fetch → 캐시. 광주 정류장(INS/GATE/GJ) 우선 정렬.
기본 `activeStation = INS01`(인성관 셔틀, 시연 메인).

### 🔍 노선 검색 탭 = 정류장 검색 → 노선 목록
1. `searchInput` → **정류장** 이름 부분 일치 필터 → 정류장 결과 목록.
2. 정류장 선택 → `state.activeStation` 설정 → `/route-recommend(station, nowHour, weekday)` → **노선 카드** 렌더.
3. 브레드크럼 칩 `← 정류장 변경 · INS01 인성관` 으로 정류장 재선택. (새 UI의 칩/카드 시각 언어 내에서 처리)

### ⭐ 즐겨찾기 탭 (홈)
- 즐겨찾기한 (정류장, 노선) 쌍 렌더.
- 즐겨찾기를 **정류장별로 그룹핑** → 정류장당 `/route-recommend` 1회 호출(호출 최소화) → 각 즐겨찾기 `routeName` 매칭으로 실시간 level/recommended.
- 빈 상태(empty-state) 유지. **날씨 카드 제거.**
- 즐겨찾기 저장 형식: `localStorage['bustago_favs']` = `[{stationId, stationName, routeName, routeNo}, ...]`
  (기존은 단순 id 배열 — 마이그레이션 시 형식 변경, 구버전 값은 무시하고 빈 배열로 시작).

### 📋 노선 상세 바텀시트 (카드 탭 시 지연 로딩)
- 헤더: 노선명 + 유형 배지 + ★ 토글(→ `(station,route)` localStorage 기록).
- 출발→도착: `stationName` → `end_stations`.
- 혼잡도 원: route-recommend `level`.
- 시간대별 막대그래프: `/predict` 다음 6시간 — **정류장 단위**. 라벨 "이 정류장 시간대별 혼잡도"로 정직하게 표기.
- 실시간 도착: `/arrive/{gj_busstop_id}` → 이 노선의 line으로 필터, ETA 분/정류장, **30초 자동 갱신**(기존 타이머 로직 재사용).
- 정류장 트랙: §6.

## 6. 정류장 진행 트랙 전략 (A안 확정)

정밀 위치 표시는 불가능: 정류장 순서(ordered stop sequence) 엔드포인트 미노출,
`bus_location`은 차량 GPS 좌표만 반환(정류장 인덱스 아님).

**A안 (확정):** `bus_location`을 활용하되 실시간 "운행 대수"로 표현.
- 트랙 = **출발 → 도착 2점**(`end_stations` 기반).
- 오버레이 라이브 칩 **"🚌 운행 중 N대"**, N = `bus_location/{LINE_ID}` 차량 수.
- `LINE_ID` 해석: 해당 노선의 BIS 도착 항목에서 추출 → 실패 시 `/api/lines` 이름 매칭 → 캐시.
- `bus_location` 실패 시 → 칩만 숨김, 2점 트랙 유지(화면 안 깨짐).

실제 데이터로 실시간 느낌 제공, 없는 정보는 지어내지 않음.
**향후 확장:** 진짜 다중 정류장 애니메이션 트랙은 백엔드에 노선-정류장 순서 엔드포인트 추가 필요 → 본 설계 범위 외.

## 7. 에러 / 폴백 처리 (시연 안정성)

`shared/api.js`는 실패 시 `null` 반환. 각 로더는 조용히 폴백(기존 앱의 데모-견고성 유지).

| 실패 소스 | 폴백 |
|---|---|
| `/stations` | 캐시 목록, 없으면 데모 정류장 셋 |
| `/route-recommend` | `getDemoLevel(hour)`로 카드 렌더 유지 |
| `/predict`(forecast) | 시간 기반 데모 막대 |
| `/arrive` | "현재 도착 예정 버스가 없습니다" |
| `/bus_location` | 운행 대수 칩 숨김 |

실패는 `console.warn` 로깅, 절대 깨진 UI로 노출하지 않음.

## 8. 테스트 / 검증

- 백엔드 `pytest`(기존 26 PASS 하네스) 그린 유지 — 백엔드 무변경, 회귀 확인용 실행.
- `data.js` 매퍼 함수는 **순수 함수**(입력 JSON → 뷰모델)로 작성 → 추후 단위 테스트 가능.
  현재 JS 러너 미설치이므로 지금은 순수성만 유지, 러너 도입은 사용자 요청 시.
- 수동 스모크 체크리스트 (`docker-compose up`, nginx+backend):
  - INS01 기본 로딩
  - 정류장 검색 → 노선 목록 표시
  - 즐겨찾기 추가/해제 후 새로고침해도 유지
  - 다크모드 토글 유지
  - 시트 열기/드래그 닫기
  - 30초 도착 자동 갱신
  - 오프라인(SW) 셸 로딩

## 9. 마이그레이션 / 파일 변경

1. `frontend/student/{index.html,style.css,app.js,manifest.json,service-worker.js}` 새 버전으로 덮어씀.
2. `frontend/student/data.js` 신규 추가.
3. 루트 `student/` → `archive/student-design-ref/`로 이동(디자인 참고 보관).
4. 옛 버전은 git 히스토리에 보존.

## 10. 미해결 / 가정

- 가정: nginx `/`가 `frontend/student/index.html`을 서빙하고 `/shared/`가 노출됨(현재 nginx.conf 확인됨).
- 가정: Docker 이미지가 `frontend/student`, `frontend/shared`를 포함(Dockerfile 검증은 구현 단계에서).
- `route_no` ≠ BIS `LINE_ID`일 수 있음 → `/api/lines` 이름 매칭으로 해소, 결과 캐시.
- 즐겨찾기 localStorage 형식 변경으로 구버전 사용자 즐겨찾기는 초기화됨(시연 환경상 영향 없음).
