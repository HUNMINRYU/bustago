# 학생앱 Kakao형 정류장 보드 + 노선 상세 + 현재 버스위치 설계

- 작성일: 2026-06-04
- 작성자: HUNMINRYU (같이타요 / 광주대 캡스톤디자인 RISE)
- 상태: 설계 확정 (구현 계획 대기)

## 1. 목표 / 범위

학생앱(`frontend/student/`)에 **광주 BIS 기반 Kakao형 버스 정보**를 넣어 사용성을 끌어올린다.
캠퍼스 집중 — 실시간 BIS는 **GJ3229(busstop 80)·GJ3230(busstop 1981)** 두 정류장만 대상.

3단계(한 spec에 전부):
- **P1 정류장 보드:** 정류장 탭 → 경유 노선 목록(종류 배지·방면) + 실시간 도착 ETA / "정보없음", 30초 갱신.
- **P2 노선 상세:** 노선 탭 → 경유 정류소 순서 + 노선 메타(첫차/막차/배차/방향) + 광주대 정류장 하이라이트.
- **P3 현재 버스위치:** 노선 상세 위에 운행 차량 위치 표시(운행 시). 없으면 "현재 운행중인 버스 없음".

INS01(인성관 셔틀)·DEMO01(시연용)은 BIS busstop이 없어 보드 대신 셔틀/데모 안내.

## 2. BIS 가용성 (실측 확인 2026-06-04)

| 데이터 | BIS 엔드포인트 | 핵심 필드 |
|---|---|---|
| 노선 메타·종류 | `lineInfo` (120개 노선) | LINE_ID, LINE_NAME, **LINE_KIND**(종류), DIR_UP_NAME/DIR_DOWN_NAME, FIRST_RUN_TIME, LAST_RUN_TIME, RUN_INTERVAL |
| 노선 경유정류소 순서 | `lineStationInfo(LINE_ID)` → BUSSTOP_LIST | SEQ, BUSSTOP_ID, ARS_ID, BUSSTOP_NAME, LAT/LON, RETURN_FLAG |
| 실시간 도착 | `arriveInfo(BUSSTOP_ID)` → ARRIVE_LIST | LINE_ID, SHORT_LINE_NAME, REMAIN_MIN, REMAIN_STOP, LOW_BUS, ARRIVE_FLAG, DIR_END |
| 현재 차량 위치 | `busLocationInfo(LINE_ID)` → BUSLOCATION_LIST | (조용한 시간 0대 — **차량 있을 때 필드 확정 필요**) |

**BIS에 없는 것:** "정류소 → 경유 노선" 직접 엔드포인트. → `lineStationInfo`를 120개 노선에 돌려 **역산**(busstop을 지나는 노선)으로 해결, 결과 캐시.

## 3. 아키텍처

```
backend/
  seeds/derive_station_routes.py   ← [신규] 120개 lineStationInfo 역산 → 정류소별 경유노선 캐시 생성
  seeds/station_routes_cache.json  ← [신규·커밋] {busstop_id: [{line_id,line_name,line_kind,dir_name}]}
  routes/stations.py               ← [수정] 신규 엔드포인트 3종
frontend/student/
  data.js     ← [수정] 보드/노선상세/위치 매퍼 + 페처
  app.js      ← [수정] 정류장 보드 뷰 + 노선 상세 뷰 + 30초 갱신
  index.html  ← [수정] 보드/상세 마크업
  style.css   ← [수정] 배지·정류소 타임라인·차량 위치 스타일
  shared/api.js ← [수정] 신규 엔드포인트 래퍼
```

### 관심사 분리
- `data.js`만 `shared/api.js`를 호출(뷰는 fetch 직접 호출 금지). BIS 위험은 `data.js`에 격리.
- 정류소→노선 역산은 **빌드 타임 시드**(런타임 120콜 금지). 보드의 노선 목록은 로컬 캐시 → BIS 느려도 목록은 즉시, ETA만 실시간.

## 4. 백엔드 엔드포인트 (신규 3종)

### 4.1 `GET /api/station-board/<int:busstop_id>` (P1)
정류소 경유노선(캐시) + 실시간 도착(arriveInfo) 병합.
```json
{ "status":"ok", "data": { "busstop_id":80,
  "routes": [
    { "line_id":24, "line_name":"송암47", "line_kind":"간선", "dir_name":"구암 방향",
      "arrival": { "min":3, "stops":2, "low":false, "imminent":false } },   // 없으면 arrival:null
    ... ] } }
```
- 캐시(`station_routes_cache.json`)에서 busstop_id의 노선 목록 로드.
- `arriveInfo(busstop_id)` 호출 → LINE_ID로 매칭해 arrival 부착. 매칭 없으면 `arrival:null`(=정보없음).
- arriveInfo 실패 시 → 전체 `arrival:null`로 목록만 반환(보드는 뜸).
- 캐시에 없는 busstop(INS01/DEMO01 등) → `routes:[]`.

### 4.2 `GET /api/line-stations/<int:line_id>` (P2)
노선 메타 + 경유 정류소 순서.
```json
{ "status":"ok", "data": {
  "line_id":24, "line_name":"송암47", "line_kind":"간선",
  "dir_up":"덕남마을 입구", "dir_down":"장등동",
  "first_run":"05:40", "last_run":"22:30", "interval":"15",
  "stops": [ { "seq":1, "busstop_id":1165, "ars_id":"4311", "name":"장등동", "lat":35.200203, "lng":126.933688 }, ... ] } }
```
- `lineStationInfo(line_id)` → BUSSTOP_LIST 정규화(SEQ 정렬).
- 메타는 `lineInfo`(앱 시작 시 1회 로드→메모리 캐시)에서 line_id 조회.

### 4.3 현재 버스위치 (P3) — 기존 `GET /api/bus_location/<line_id>` 재사용
- `busLocationInfo(line_id)` → 차량 목록.
- ⚠️ **필드 미확정**(조용한 시간 0대). 구현 단계에서 운행 차량으로 확인:
  - 차량에 현재 정류소(BUSSTOP_ID/SEQ)가 있으면 그 SEQ로 타임라인에 위치 표시.
  - 없고 lat/lng만 있으면 경유정류소 좌표와 최근접 매칭으로 SEQ 추정.
  - 방어적 구현: 매핑 불가/0대 → "현재 운행중인 버스 없음".

## 5. 프론트 — 뷰 / 흐름

### 5.1 정류장 보드 (검색 탭, P1)
- 정류장 선택 → `/api/station-board/<busstop_id>` 로드 → Kakao형 리스트:
  - 행: `[종류배지] 노선명` · `방면 방향` · 우측 `N분·M정거장` 또는 `정보없음`.
  - 종류 배지 색: 간선=파랑, 지선=초록, 급행=빨강, 농어촌=주황(이미지 기준).
  - `ARRIVE_FLAG=1` → "곧 도착", `LOW_BUS=1` → `저상` 배지.
  - 상단: 정류장명·ARS·방면 헤더 + 새로고침. 주소·지도 버튼은 **제외**(사용자 요청).
  - **30초 자동 갱신**(검색 탭·정류장 선택 중에만; 이탈 시 타이머 정리, race 가드).
- busstop 없음(INS01/DEMO01) → "셔틀 정류장 · 실시간 시내버스 도착 없음" 안내.
- **기존 노선 추천(route-recommend) 카드는 정류장 뷰에서 BIS 보드로 교체.** 혼잡도는 사라지지
  않고 (a)홈 crowd-count 카드 + (b)노선 상세 하단 시간대별 예측으로 살아있음 — §7.

### 5.2 노선 상세 (P2)
- 보드의 노선 탭 → `/api/line-stations/<line_id>` 로드 → 풀스크린/바텀시트:
  - 헤더: `[배지] 노선명` · `방향 ↔` · `첫차/막차/배차간격`.
  - 경유 정류소 **세로 타임라인**(SEQ 순): 정류소명 + ARS. **광주대(busstop 80/1981) 행 하이라이트**(내 위치).
  - 닫기/뒤로 → 보드로 복귀.

### 5.3 현재 버스위치 (P3)
- 노선 상세 진입 시 `/api/bus_location/<line_id>` 로드 → 타임라인에 **차량 점**(현재 SEQ 위치).
- **20초 자동 갱신**. 0대/매핑불가 → 헤더에 "현재 운행중인 버스 없음".

## 6. 에러 / 폴백 (시연 안정성)

| 실패 | 폴백 |
|---|---|
| `/station-board` arriveInfo 실패 | 노선 목록만(전부 정보없음) |
| 캐시에 없는 busstop | 보드 대신 셔틀/데모 안내 |
| `/line-stations` 실패 | "노선 정보를 불러오지 못했습니다" + 뒤로 |
| `/bus_location` 0대/실패 | "현재 운행중인 버스 없음" |
| BIS 키 없음 | 모든 BIS 502 → 위 폴백 경로로 graceful |

모든 실패 `console.warn`, 깨진 UI 노출 금지(기존 데모-견고성 유지).

## 7. 혼잡도(USP) 공존

본 프로젝트 핵심은 혼잡도 예측. BIS 보드가 화면을 가져가도 혼잡도를 버리지 않는다:
- 홈(즐겨찾기)의 "실시간 정류장 상황" 카드(crowd-count) **유지**.
- 노선 상세 하단에 기존 **시간대별 혼잡도 예측**(`/predict` 6시간) 섹션 **유지·이전**.
- 정류장 보드 자체는 BIS 중심(도착). 혼잡도와 도착의 본격 결합 카드는 범위 밖(향후).

## 8. 테스트 / 검증

- `data.test.js`(Node 순수 매퍼): `mapStationBoard`(병합·정보없음·배지), `mapLineStations`(SEQ 정렬·하이라이트 대상), `mapBusPositions`(SEQ 매핑/0대).
- 백엔드 `pytest`: `/api/station-board`·`/api/line-stations` mock 응답 테스트(responses 라이브러리), 캐시 로딩 테스트.
- 시드 스크립트: `derive_station_routes.py` 1회 실행 후 캐시에 GJ3229/GJ3230 노선이 사용자 캡처(송암47·진월177·진월77·수완03·318·318-1)와 일치하는지 수동 대조.
- 수동 스모크: 보드 표시→ETA/정보없음, 노선 탭→경유정류소 타임라인+광주대 하이라이트, (운행 시)차량 점, 30/20초 갱신, INS01 셔틀 안내.

## 9. 범위 밖 / 가정

- 도착 알림, 즐겨찾기 카드 "다음 버스 N분", 혼잡도+도착 결합 카드, 시설 현황 — 별도.
- 주소·길찾기·로드뷰 버튼 — 제외(사용자 요청).
- 가정: 정류소 경유노선 구성은 안정적 → 캐시 정적 사용(노선 개편 시 시드 재생성).
- 가정: `busLocationInfo` 차량 필드에 현재 정류소 또는 좌표 포함(운행 차량으로 확정 필요).
- 캐시 생성은 BIS 키·네트워크 필요(빌드 타임 1회). 런타임은 캐시+arriveInfo만.
