# BUSTAGO QA 통합 정합성 검증 리포트

**검증일**: 2026-03-30
**검증자**: QA Inspector
**검증 범위**: ML <-> Backend <-> Frontend 전 계층 교차 검증

---

## 1. 요약

| 구분 | PASS | FAIL | WARN | 합계 |
|------|------|------|------|------|
| Checkpoint 1: ML 코드 vs 계약서 | 7 | 0 | 0 | 7 |
| Checkpoint 2: ML <-> Backend | 7 | 0 | 1 | 8 |
| Checkpoint 3: Backend <-> Frontend | 9 | 0 | 0 | 9 |
| Checkpoint 4: E2E 데이터 흐름 | 3 | 0 | 0 | 3 |
| **합계** | **26** | **0** | **1** | **27** |

**최종 판정: PASS** -- FAIL 항목 없음. WARN 1건(weather=1 미도달)은 기능 제한이나 런타임 에러 아님.

---

## 2. Checkpoint 1: ML 코드 vs 계약서

대상 파일: `_workspace/01_ml_model_contract.json` vs `ml/models/predict.py`, `ml/models/train_rf.py`, `ml/preprocessing/build_features.py`

| # | 검증 항목 | 결과 | 비고 |
|---|----------|------|------|
| 1.1 | Feature 컬럼 순서 (build_features / train_rf / predict) | PASS | 10개 컬럼 동일 순서 |
| 1.2 | Label map 일관성 | PASS | {0:여유, 1:보통, 2:혼잡, 3:매우혼잡} |
| 1.3 | predict_congestion 시그니처 | PASS | (features: dict, model_path: str) -> dict |
| 1.4 | predict_batch 시그니처 | PASS | (features_list: list, model_path: str) -> list |
| 1.5 | 출력 스키마 (level/label/probabilities) | PASS | 계약서와 완전 일치 |
| 1.6 | 모델 경로 | PASS | ml/models/rf_model.pkl |
| 1.7 | 하이퍼파라미터 | PASS | n_estimators=100, random_state=42 |

---

## 3. Checkpoint 2: ML <-> Backend

대상 파일: `ml/models/predict.py` vs `backend/routes/predict.py`, `backend/config.py`, `backend/models/db.py`, `backend/schema.sql`

| # | 검증 항목 | 결과 | 비고 |
|---|----------|------|------|
| 2.1 | ML input params vs API features dict | PASS | 10개 feature 모두 정확히 구성 |
| 2.2 | ML return shape vs API jsonify | PASS | data.prediction에 올바르게 중첩 |
| 2.3 | Feature column order 안전성 | PASS | ML이 FEATURE_COLS로 순서 보장 |
| 2.4 | Model path (config.py -> predict) | PASS | MODEL_PATH 일관 |
| 2.5 | Label map 일관성 | PASS | RECOMMENDATIONS 키와 일치 |
| 2.6 | DB schema vs API INSERT | PASS | predictions 테이블 필드 일치 |
| 2.7 | SQL placeholder 호환성 | PASS | _adapt_sql()로 ? -> %s 자동 변환 (수정 완료) |
| 2.8 | Weather code 매핑 | WARN | weather=1(흐림) 생성 경로 없음 |

### 수정 완료: SQL placeholder 불일치 (2.7)

- **발견**: 모든 라우트에서 SQLite 스타일 `?` placeholder 사용, PyMySQL은 `%s` 필요
- **수정**: backend/models/db.py:107-111에 `_adapt_sql()` 함수 추가. MySQL 모드에서 자동 변환.
- **재검증**: fetchall(:123), fetchone(:136), execute(:148) 모두 `_adapt_sql(sql)` 호출 확인. PASS.

### WARN 상세: weather=1 미도달 (2.8)

- **위치**: backend/routes/stations.py:100-126 `_parse_kma_items()`
- **원인**: 기상청 PTY(강수형태)만 파싱하여 SKY(하늘상태) 미반영. weather=1(흐림)은 SKY 카테고리로만 판단 가능.
- **영향**: 모델에 weather=1이 전달되지 않아 흐린 날씨 예측 정확도 저하 가능. 런타임 에러는 아님.
- **수정 방법**: SKY 카테고리 파싱 추가 (SKY=3,4 -> weather=1)

---

## 4. Checkpoint 3: Backend <-> Frontend

대상 파일: `backend/routes/*.py`, `_workspace/02_api_contract.json` vs `frontend/shared/api.js`, `frontend/student/app.js`, `frontend/admin/dashboard.js`

| # | 검증 항목 | 결과 | 비고 |
|---|----------|------|------|
| 3.1 | API URL 경로 일치 | PASS | /predict, /stats, /stations, /weather/current |
| 3.2 | API 쿼리 파라미터명 | PASS | station_id, hour, weekday, period |
| 3.3 | API 응답 JSON 키 접근 | PASS | prediction.level, recommendation 등 |
| 3.4 | 혼잡도 레벨/라벨 매핑 | PASS | {0:여유, 1:보통, 2:혼잡, 3:매우혼잡} |
| 3.5 | CORS 설정 | PASS | CORS(app) 전체 허용 |
| 3.6 | 요일 변환 (JS -> Python) | PASS | getDay(0=Sun) -> weekday(0=Mon) 정확 |
| 3.7 | 에러 핸들링 & 폴백 | PASS | status!="ok" -> demo fallback |
| 3.8 | Stats 응답 구조 접근 | PASS | hourly_stats[].hour, avg_level |
| 3.9 | 정류장 데이터 동기화 | PASS | /api/stations 동적 로드 (수정 완료) |

### 수정 완료: Admin 정류장 하드코딩 불일치 (3.9)

- **발견**: dashboard.js의 STATIONS 하드코딩이 DB seed와 불일치
- **수정**:
  - admin/dashboard.js: STATIONS를 빈 객체로 초기화, `loadStations()` 함수 추가. DOMContentLoaded에서 `fetchStations()` 호출하여 동적 로드.
  - student/app.js: `loadStationOptions()` IIFE 추가. `/api/stations`에서 정류장 목록 동적 로드.
  - 양쪽 HTML의 하드코딩된 option 제거.
- **재검증**: dashboard.js:11 `STATIONS = {}`, :31-32 `await loadStations()`, :42-57 fetchStations() -> STATIONS 객체 + 드롭다운 동적 구성 확인. student/app.js:35-45 동일 구조 확인. PASS.

---

## 5. Checkpoint 4: E2E 데이터 흐름

| # | 검증 항목 | 결과 | 비고 |
|---|----------|------|------|
| 4.1 | ARS 번호 형식 | PASS | 전 계층 문자열(VARCHAR/string) 일관 |
| 4.2 | 시간대(hour) 형식 | PASS | 전 계층 정수 0-23 일관 |
| 4.3 | 날씨 코드(weather) 의미 | PASS | 전 계층 {0:맑음, 1:흐림, 2:비, 3:눈} 일관 |

### 전체 데이터 흐름 추적

```
[ML 학습]
build_features.py -> train_features.csv (10 features + label)
train_rf.py -> rf_model.pkl (FEATURE_COLS 순서 학습)

[예측 요청 흐름]
Frontend: fetchPredict(stationId, hour, weekday)
  -> GET /api/predict?station_id=22011&hour=8&weekday=1
  -> Backend routes/predict.py: features dict 10개 구성 (weather/boarding 기본값)
  -> ml.models.predict.predict_congestion(features, model_path=MODEL_PATH)
  -> ML: FEATURE_COLS 순서로 배열 생성 -> model.predict() + predict_proba()
  -> {level: int(0-3), label: str, probabilities: list[float]}
  -> Backend: jsonify({status, data: {prediction, recommendation, next_hour_prediction}})
  -> Frontend api.js: data.data 추출 -> app.js: data.prediction.level -> CONGESTION[level] 표시

[통계 조회 흐름]
Frontend: fetchStats(stationId, period)
  -> GET /api/stats?station_id=22011&period=today
  -> Backend routes/stats.py: predictions 테이블 시간대별 평균 집계
  -> jsonify({status, data: {station_id, period, hourly_stats: [{hour, avg_level}], total_predictions}})
  -> Frontend dashboard.js: hourly_stats -> extractHourlyLevels() -> Chart.js 바 그래프

[정류장 목록 흐름]
Frontend: fetchStations()
  -> GET /api/stations
  -> Backend routes/stations.py: DB stations 테이블 전체 조회
  -> jsonify({status, data: [{ars_no, station_name, latitude, longitude}]})
  -> Frontend: 드롭다운 동적 구성 (student + admin 양쪽)

[날씨 조회 흐름]
Frontend: fetchWeather()
  -> GET /api/weather/current
  -> Backend routes/stations.py: 캐시 확인 -> 기상청 API -> 폴백
  -> jsonify({status, data: {weather(0-3), temperature, rain, humidity, wind_speed}})
```

---

## 6. 조치 현황

| # | 항목 | 심각도 | 상태 | 조치 내용 |
|---|------|--------|------|----------|
| 1 | SQL placeholder 불일치 | FAIL | **수정 완료** | db.py에 _adapt_sql() 추가 |
| 2 | Admin 정류장 하드코딩 | WARN | **수정 완료** | fetchStations() 동적 로드로 변경 |
| 3 | weather=1(흐림) 미도달 | WARN | 미수정 (낮은 우선순위) | SKY 카테고리 파싱 추가 필요 |

---

## 7. 검증 파일 목록

| 파일 | 역할 | 검증 대상 |
|------|------|----------|
| _workspace/01_ml_model_contract.json | ML 모델 계약서 | CP1 |
| _workspace/02_api_contract.json | API 계약서 | CP2, CP3 |
| ml/models/predict.py | ML 예측 인터페이스 | CP1, CP2 |
| ml/models/train_rf.py | ML 모델 학습 | CP1 |
| ml/preprocessing/build_features.py | Feature 구축 | CP1 |
| backend/config.py | Backend 설정 | CP2 |
| backend/models/db.py | DB 헬퍼 (SQL 변환 포함) | CP2 |
| backend/routes/predict.py | 예측 API | CP2, CP3 |
| backend/routes/stats.py | 통계 API | CP2, CP3 |
| backend/routes/stations.py | 정류장/날씨 API | CP2, CP3 |
| backend/schema.sql | DB 스키마 | CP2, CP4 |
| backend/app.py | Flask 앱 | CP2 |
| frontend/shared/api.js | API 래퍼 | CP3 |
| frontend/student/app.js | 학생 PWA | CP3, CP4 |
| frontend/admin/dashboard.js | 운영자 대시보드 | CP3, CP4 |
