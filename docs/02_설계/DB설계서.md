# BUSTAGO 데이터베이스 설계서

> **버전:** 1.0  
> **작성일:** 2026-05-13  
> **DBMS:** MySQL 8.x (운영) / SQLite 3 (폴백·개발)  
> **소스:** `backend/schema.sql` (자동 적용)

---

## 1. 개요

5개 테이블로 구성:
- `stations` — 정류장 마스터 (서울 5 + 광주 5 = 10개)
- `predictions` — ML 예측 결과 로그
- `weather_cache` — 기상청 API 응답 캐시 (시간당)
- `crowd_counts` — Jetson 카메라가 10초마다 POST한 인원 카운트
- `routes` — 대체 노선 추천에 사용되는 노선 마스터

MySQL 미가용 시 `db.py`가 자동으로 SQLite 폴백. 같은 SQL 스크립트로 양쪽 호환 (`AUTO_INCREMENT` ↔ `INTEGER PRIMARY KEY`, `INSERT IGNORE` ↔ `INSERT OR IGNORE` 호환 처리).

---

## 2. ERD (논리)

```
┌──────────────┐
│  stations    │◀────────┐
│  ──────────  │         │ FK station_ars_no
│  id (PK)     │         │
│  ars_no (UK) │    ┌────┴──────────┐
│  station_name│    │  predictions  │
│  latitude    │    │  ───────────  │
│  longitude   │    │  id (PK)      │
│  gj_busstop  │    │  station_ars  │
│  _id         │    │  hour         │
└──────────────┘    │  weekday      │
                    │  predicted_lvl│
┌──────────────┐    │  predicted_lbl│
│ crowd_counts │    │  probabilities│
│  ──────────  │    │  created_at   │
│  id (PK)     │    └───────────────┘
│  station_id  │    
│  count_in    │    ┌───────────────┐
│  count_board │    │ weather_cache │
│  current_wait│    │  ───────────  │
│  source      │    │  id (PK)      │
│  created_at  │    │  location     │
└──────────────┘    │  hour         │
                    │  weather      │
┌──────────────┐    │  temperature  │
│   routes     │    │  rain         │
│  ──────────  │    │  humidity     │
│  id (PK)     │    │  wind_speed   │
│  route_no    │    │  fetched_at   │
│  route_name  │    └───────────────┘
│  start_stn_id│
│  end_stations│ (JSON 배열 문자열)
│  route_count │
│  is_shuttle  │
└──────────────┘
```

> 참고: `predictions.station_ars_no` 외에는 외래키 제약 미설정 (SQLite 폴백 호환성 위해).

---

## 3. 테이블 상세

### 3.1 `stations`

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INT | PK AUTO_INCREMENT | 내부 식별자 |
| `ars_no` | VARCHAR(10) | UK NOT NULL | 정류장 코드 (예: `GJ3230`, `INS01`) |
| `station_name` | VARCHAR(100) | NOT NULL | 표시 이름 |
| `latitude` | DECIMAL(10,7) | | 위도 |
| `longitude` | DECIMAL(10,7) | | 경도 |
| `gj_busstop_id` | INT | NULL 허용 | 광주 BIS API 정류소 번호 (NULL=서울/셔틀) |

**시드 데이터 (10건):**
- 서울 5: `22011·22012·23115·21148·22341` (ML 학습 기준)
- 광주 셔틀: `INS01` (인성관), `GATE01` (정문)
- 광주 BIS 실제: `GJ3230 → 1981`, `GJ3229 → 80`, `GJ3228 → 3219`

### 3.2 `predictions`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INT PK | |
| `station_ars_no` | VARCHAR(10) NOT NULL | FK → stations.ars_no |
| `hour` | TINYINT | 0~23 |
| `weekday` | TINYINT | 0=월 ~ 6=일 |
| `predicted_level` | TINYINT | 0=여유, 1=보통, 2=혼잡, 3=매우혼잡 |
| `predicted_label` | VARCHAR(20) | 라벨 텍스트 |
| `probabilities` | JSON | [p0, p1, p2, p3] |
| `created_at` | TIMESTAMP | 자동 |

### 3.3 `weather_cache`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INT PK | |
| `location` | VARCHAR(50) | `seoul`/`gwangju` |
| `hour` | TINYINT | 0~23 |
| `weather` | TINYINT | 0=맑음, 1=흐림, 2=비, 3=눈 |
| `temperature` | DECIMAL(4,1) | °C |
| `rain` | TINYINT | 0/1 강수 |
| `humidity` | TINYINT | % |
| `wind_speed` | DECIMAL(4,1) | m/s |
| `fetched_at` | TIMESTAMP | TTL 1시간 기준 |

### 3.4 `crowd_counts`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INT PK | |
| `station_id` | VARCHAR(10) | 카메라 위치 정류장 |
| `count_in` | INT | 누적 진입 인원 |
| `count_board` | INT | 누적 탑승 인원 |
| `current_waiting` | INT | 현재 대기 인원 (in − board) |
| `source` | VARCHAR(20) | `jetson` (기본) |
| `created_at` | TIMESTAMP | 자동 |

10초 주기 POST → 약 8,640건/일/정류장.

### 3.5 `routes`

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | INTEGER PK | |
| `route_no` | VARCHAR(20) | `419`, `SHUTTLE1` 등 |
| `route_name` | VARCHAR(100) | `419번 (광주역행)` |
| `start_station_id` | VARCHAR(10) | 출발 정류장 ars_no |
| `end_stations` | TEXT | JSON 배열 문자열 `["광주역","충장로"]` |
| `route_count` | INT | 운행 대수 (혼잡도 feature 입력) |
| `is_shuttle` | TINYINT | 0=시내, 1=셔틀 |

**시드 데이터 (8건):** 시내버스 419/518, 셔틀 SHUTTLE1~6.

---

## 4. 인덱스 전략

| 테이블 | 인덱스 | 이유 |
|--------|--------|------|
| stations | UK(ars_no) | 자주 조회되는 룩업 키 |
| predictions | (station_ars_no, hour, weekday) | 시간대별 통계용 (현재는 직접 SELECT) |
| crowd_counts | (station_id, created_at DESC) | 가장 최근 1건 조회 |
| weather_cache | (location, hour, fetched_at DESC) | 캐시 룩업 |

SQLite 폴백에서는 PK·UK 외 명시적 인덱스 생략 (소규모 시연 데이터셋).

---

## 5. 데이터 수명 관리

| 테이블 | 보존 정책 |
|--------|----------|
| stations | 영구 |
| routes | 영구 (운행 개편 시 수동 갱신) |
| weather_cache | 1시간 TTL — `fetched_at` 기반 cron 정리 가능 (현재 미적용, 충분히 작음) |
| predictions | 로그성 — 시연 후 분석용. 수동 정리 |
| crowd_counts | 시연 기간 동안 보존, 이후 월별 partition 또는 export 후 삭제 권장 |

---

## 6. 마이그레이션

- `backend/models/db.py`의 `init_db()`가 Flask 시작 시 `schema.sql`을 `executescript`로 적용 → 모든 `CREATE TABLE IF NOT EXISTS`·`INSERT IGNORE`라 멱등.
- 컬럼 추가 시: `schema.sql`만 수정하면 신규 환경은 자동 적용. 기존 SQLite DB는 삭제 후 재시작 또는 `ALTER TABLE` 수동.
- 2026-05-13: `stations` 테이블에 `gj_busstop_id INT NULL` 추가됨.

---

## 7. 변경 이력

| 일자 | 변경 |
|------|------|
| 2026-03-29 | 초기 스키마 (stations, predictions, weather_cache) |
| 2026-04-15 | crowd_counts 추가 (Jetson POST 수용) |
| 2026-04-28 | routes 테이블 추가 (route-recommend API) |
| 2026-05-13 | stations에 gj_busstop_id 컬럼 + 광주 BIS 정류장 3개 시드 + 본 문서 신규 작성 |
