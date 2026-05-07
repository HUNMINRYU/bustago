# BUSTAGO 프로젝트 진행 현황

> **최종 업데이트 일시:** 2026-05-07 (KST)
> 1차 시연: 5.21 (D-14) | 최종 보고서: 6.4

---

## 🚀 전체 진행도: **97%**

```text
전체 ███████████████████░  97%
SW   ████████████████████ 100%
HW   ██████████░░░░░░░░░░  50%  ← 부품 미수령 블로킹 (5/6 현재)
문서 ████████████████████ 100%  ← 교수 피드백 7항목 전부 반영 완료
```

---

## 📊 영역별 진행도 상세

### 1. ML 파이프라인 — 100%
```text
ML 전체   ████████████████████ 100%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| 승하차 데이터 수집 (`collect_boarding.py`) | 100% | ✅ 완료 | 서울 API 연동, 페이징, 필터링 구현 |
| 기상 데이터 수집 (`collect_weather.py`) | 100% | ✅ 완료 | 기상청 API 연동, 카테고리 필터링 구현 |
| 혼잡도 데이터 수집 (`collect_congestion.py`) | 100% | ✅ 완료 | **[26.03.30]** Mock API 테스트(`test_collect_congestion.py`) 통과 및 구현 검증 완료 |
| 통합 파이프라인 (`pipeline.py`) | 100% | ✅ 완료 | 기능 구현 완료 |
| 전처리/Feature 결합 (`build_features.py`) | 100% | ✅ 완료 | 4단계 라벨링, Feature 병합 구현 |
| 모델 학습 (`train_rf.py`) | 100% | ✅ 완료 | **[26.03.31]** Autoresearch 12회 반복 → 최적 하이퍼파라미터 확정 (n=10, depth=10, 7 features) |
| LightGBM 모델 (`train_lgbm.py`) | 100% | ✅ 완료 | **[26.05.07]** RF 대비 Accuracy +4.0%p, F1 +4.69%p 우세 확인 → LightGBM 전환 결정 |
| 예측 API (`predict.py`) | 100% | ✅ 완료 | **[26.05.07]** lgbm_model.pkl 우선 로드, rf_model.pkl fallback 추가 |
| API 단위 테스트 | 100% | ✅ 완료 | `pytest` 기반 ML 전체 수집기 테스트 완료 |

### 2. Backend (Flask API) — 100%
```text
Backend   ████████████████████ 100%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| Flask 앱 (`app.py`) | 100% | ✅ 완료 | 블루프린트 라우팅 구현 및 구동 확인 |
| DB 스키마 (`schema.sql`) | 100% | ✅ 완료 | **[26.03.30]** `db.py` fallback 버그수정(SQLite `INSERT OR IGNORE`) 완료 |
| REST API 엔드포인트 | 100% | ✅ 완료 | `/api/health`, `/api/predict`, `/api/stats`, `/api/stations`, `/api/crowd-count`, `/api/route-recommend` — `test_app.py` 7/7 PASS |
| Prediction Cache | 100% | ✅ 완료 | **[26.04.01]** LRU TTL Cache 적용, 응답 800ms→23ms (35x 개선) |
| 입력 검증 / 보안 | 100% | ✅ 완료 | **[26.04.01]** station_id regex, hour/weekday isdigit 검증 + Flask-Limiter Rate Limiting 전 엔드포인트 적용 |
| Stats Cache | 100% | ✅ 완료 | **[26.04.01]** /api/stats 60초 TTL Cache (Codex 구현) |
| `requirements.txt` | 100% | ✅ 완료 | 명세 완료 및 패키지 환경 셋업 |

### 3. Frontend (Student PWA & Admin) — 100%
```text
Frontend  ████████████████████ 100%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| 학생 PWA (`app.js`, `index.html`) | 100% | ✅ 완료 | **[26.04.28]** 출발지/목적지 드롭다운 + 노선별 혼잡도 추천 카드 UI 추가 |
| 운영자 대시보드 (`admin/`) | 100% | ✅ 완료 | **[26.04.28]** 실시간 카운팅 패널(대기/IN/BOARD + Jetson 연결 상태) 추가 |
| 시각화 및 지도 (Chart/Leaflet) | 100% | ✅ 완료 | **[26.04.01]** 바 차트 + 도넛 차트(혼잡도 분포) + Leaflet 지도 완성 |
| PWA manifest/SW | 100% | ✅ 완료 | Service Worker 및 manifest 설정 완료 |

### 4. Hardware (Jetson Orin Nano + Raspberry Pi 4) — 50%
```text
Hardware  ██████████░░░░░░░░░░ 50%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| 하드웨어 설계서 v2.0 | 100% | ✅ 완료 | **[26.04.10]** Jetson+Pi 역할 분리, DeepSORT 파이프라인, BOM 792K |
| 구매검토 보고서 v5 | 100% | ✅ 완료 | **[26.04.15]** 1차 실내 시연 우선, 외부 설치 부품 분리, 총 913,300원 |
| `counter.py` (AI 카운팅 스크립트) | 100% | ✅ 완료 | **[26.04.15]** YOLOv8+DeepSORT+Line Crossing, PC 웹캠/Jetson TensorRT 지원 |
| `/api/crowd-count` 엔드포인트 | 100% | ✅ 완료 | **[26.04.15]** POST/GET/history, crowd_counts 테이블, 7/7 테스트 PASS |
| 부품 구매 | 0% | ⬜ 대기 | 목표: 4/18 수령 |
| JetPack + YOLOv8 TensorRT 설치 | 0% | ⬜ 대기 | 1주차 작업 (부품 수령 후) |
| Pi Kiosk + Backend 연동 | 0% | ⬜ 대기 | 2주차 작업 |
| 현장 설치 + 안정성 테스트 | 0% | ⬜ 대기 | 3~4주차 작업 |

---

## 📝 최근 작업 내역

### 2026-05-01~05-06: 4/30 교수 피드백 반영 + 문서 체계 완성
1. **하드웨어 시스템 개념도 작성** ()
   * Mermaid 전체 구조도 (정류장→서버→Admin 3-tier)
   * Pi→Jetson 전환 근거 상세 (FPS 2~5→25~40, Track ID 중복 방지, 카메라 3→1대)
   * 보드별 역할 분리표 + 데이터 흐름 3경로
2. **물리 설치 설계도 작성** ()
   * 2.5m 기둥 마운트 + IP54 방수 박스 + 카메라 45° 하향 배치
   * IN/BOARD 라인 기준 좌표 + 설치 9단계 절차표
3. **화면설계서 터치포인트 작성** ()
   * Student PWA 5화면 + Admin 4섹션 전체 UI 명세
4. **시연 계획서 작성** ()
   * 5/21 시연 시나리오·성공 기준·장비 배치·비상 대응 6종
5. **HW 설치 가이드 작성** (2-Part)
   * Part 1 (): JetPack→TensorRT→counter.py→라인 튜닝→Watchdog
   * Part 2 (): Pi OS→Kiosk 서비스→E2E 통합 테스트→비상 대응
6. **광주·서울 API 혼잡도 비교 문서** ()
   * 광주 BIS API 혼잡도 필드 없음 — API 명세 기반 사실 확인 (추정 아님)
   * 국토부 표준 4단계 분류 체계 동일성 근거
7. **뻐정 유사프로젝트 사례분석** ()
   * SSD→YOLOv8 교체 근거, DeepSORT 유무 비교, TensorRT 속도 24배 향상 사례
8. **AI 카운팅 정확도 리포트 템플릿** ()
   * IN/BOARD 오차율 계산 공식, 목표 기준(IN ≤10%, BOARD ≤15%), 일별 측정표
9. **발표 슬라이드 구조** ()
   * 15슬라이드 구조 + 시간 배분표 + Q&A 예상 질문 3개
10. **Watchdog 스크립트 구현** (2026-05-06 18:55:15 [JETSON] counter.py 정상 동작 중, 2026-05-06 18:55:15 [PI] Kiosk 미실행 — 재시작
2026-05-06 18:55:15 [PI] bustago-kiosk.service restart 완료)
    * Jetson: pgrep 기반 counter.py 모니터링, 미실행 시 nohup 자동 재시작
    * Pi: Chromium Kiosk 감시, 미실행 시 systemctl restart

### 2026-05-07: 회의 결과 반영 — YOLOv11 전환 + LightGBM 도입
1. **`hardware/counter.py` — YOLOv8 → YOLOv11 업그레이드**
   * 모델 기본값: `yolov8n.pt` → `yolo11n.pt` / `.engine`
   * 회의 결정: 최신 버전으로 교체 + 실제 정류장 환경 데이터로 파인튜닝 예정
2. **`ml/models/train_lgbm.py` — LightGBM 학습 스크립트 신규 생성**
   * RF 대비 학습 속도 15배 향상·오차 감소 효과 확인 (회의 조사 결과)
   * `python train_lgbm.py --compare` 로 RF vs LightGBM 성능 비교표 출력 가능
3. **`ml/models/predict.py` — lgbm_model.pkl 우선 로드 + rf fallback**
   * `lgbm_model.pkl` 존재 시 우선 사용, 없으면 `rf_model.pkl` 자동 폴백

**회의 주요 결정 사항 (2026-05-07)**
- 카메라: 기둥 측면 1.5~2m 높이, 45도 경사 촬영 (인식률 우선)
- 시연 시 삼각대(2~3m) 활용 검토
- 광주 버스 API: 실시간 위치·정류장·노선 제공 확인, 혼잡도는 미제공 → 서울 API 유지
- LightGBM 전환 검토 (건영 AI 파트 담당)
- 혼잡도 기준 객관적 근거 조사 필요
- 운영자 대시보드 타깃 사용자 재정의 필요 (광주시 대중교통 운영 부서)

**액션 아이템 진행 현황**
- [x] LightGBM vs RF 성능 비교 실행 → **LightGBM 전환 확정** (Acc +4.0%p, F1 +4.69%p, CV 0.934)
- [ ] YOLOv11 파인튜닝 — 실제 정류장 환경 영상·이미지 수집 후 추가 학습
- [ ] 광주 버스 API 연동 정리 및 공유 (건우 담당)
- [ ] 운영자 대시보드 타깃 사용자 확정 + 유즈케이스 재정의
- [ ] 혼잡도 색상 기준 객관적 근거 자료 조사 (국토부 기준 등)
- [ ] 카메라 삼각대·폴대 설치 방법 사전 검토
- [ ] 유사 사례 추가 조사 (건영 담당)

**LightGBM 벤치마크 결과 (2026-05-07, 합성 데이터 500행)**

| 모델 | Accuracy | F1 (macro) | 학습시간 |
|------|:--------:|:----------:|:--------:|
| RandomForest | 0.9000 | 0.8850 | 0.01s |
| LightGBM | 0.9400 | 0.9319 | 0.15s |

5-Fold CV: 0.9340 ± 0.0215 / 클래스별 F1: 여유 0.97, 보통 0.94, 혼잡 0.92, 매우혼잡 0.90

### 2026-04-28: 대체노선 추천 API + Admin 카운팅 패널 + 광주 정류장 데이터
1. **`/api/route-recommend` 엔드포인트 (신규)**
   * `backend/routes/recommend.py` 신규 구현
   * `GET /api/route-recommend?station_id=&hour=&weekday=&dest=`
   * STATIC_ROUTES(GATE01: 419번·518번, INS01: 셔틀1·2·5·6호차) + DB routes 테이블 폴백
   * ML 모델로 노선별 혼잡도 예측 → level 낮은 순 정렬, `recommended=True` 1개 자동 마킹
   * 피크타임 fallback (hour 8·9·17·18 → level=2) 포함
2. **`backend/schema.sql` — 광주 정류장 + routes 테이블 추가**
   * INS01(인성관), GATE01(정문) 2개 정류장 INSERT
   * routes 테이블 신규 생성 (419번, 518번, 셔틀 1~6호차)
3. **Admin 실시간 카운팅 패널**
   * `frontend/admin/index.html` — 카운팅 패널 섹션 추가
   * `frontend/admin/dashboard.js` — `loadCrowdCount()` 10초 폴링 + Jetson staleness 판정
   * `frontend/admin/style.css` — `.counting-panel`, `.status-dot.online/stale/offline` 추가
4. **Student PWA 출발지/목적지 + 노선 추천 UI**
   * `frontend/student/index.html` — `#dest-select` 드롭다운 + `#route-recommend-section` 추가
   * `frontend/student/app.js` — `loadRouteRecommend()` 구현, destSelect change 이벤트 연결
   * `frontend/student/style.css` — 노선 카드 CSS 추가
5. **문서 & 계약서 정합성 수정**
   * `_workspace/01_ml_model_contract.json` v1.0→v2.0: 7 feature / n_estimators=10 동기화
   * `frontend/shared/api.js` API_BASE 하드코딩 → `window.location.origin + '/api'`
   * 프로젝트 루트 잔여 파일 `=3.5` 삭제

### 2026-04-15: AI 카운팅 파이프라인 구현 + 문서 정합성 갱신
1. **`hardware/counter.py` 구현**
   * YOLOv8 + DeepSORT + Line Crossing 기반 인원 카운팅 스크립트
   * PC 웹캠 `--debug` 모드 + Jetson TensorRT `.engine` 배포 지원
   * 10초 간격 자동 POST `/api/crowd-count`
2. **`/api/crowd-count` 백엔드 엔드포인트**
   * POST (Jetson→Backend), GET (최신 조회), GET /history (이력)
   * `crowd_counts` DB 테이블 추가, 입력 검증, Rate Limiting
   * `test_app.py` 4개 테스트 추가 → 전체 7/7 PASS
3. **문서-코드 정합성 전면 갱신**
   * PROGRESS.md: Hardware 30%→50%, counter.py/crowd-count 완료 반영
   * 루트 README.md: hardware/ 설명, 배지, 폴더 구조, 실행 가이드 갱신
   * docs/README.md: 설계서 설명 Jetson+Pi 반영
   * 설계서 v2.0: 신규 개발 항목 완료 상태 갱신

### 2026-04-10: 1차 리뷰 피드백 반영 + Jetson 아키텍처 전환
1. **시스템 플로우차트 v2 작성**
   * 사용자 기준 흐름으로 전면 개편: 출발지-목적지 입력 → 노선별 혼잡도 비교 → 대체노선 추천
   * 구체적 버스번호(419번, 518번, 셔틀3호 등) 포함 시나리오 2건 작성
   * 4단계 혼잡도(여유/보통/혼잡/매우혼잡) 구현과 일치시킴
2. **업무 흐름도 v2 작성**
   * System Lane + User Lane 2레인 구조로 사용자 여정 병행 표현
   * 각 Phase별 사용자 터치포인트 명시
   * 광주 데이터 소스 구체화 (BIS API, 승하차 XLSX)
3. **하드웨어 설계서 v2.0 전면 개정 (Jetson 전환)**
   * Pi 4 CPU 한계 분석 (2~5 FPS, DeepSORT 불가) → Jetson Orin Nano GPU 전환
   * **Jetson(AI 추론) + Pi 4(키오스크)** 역할 분리 2보드 구조
   * 카메라 3대→1대 전환 (고 FPS에서 1대로 충분)
   * 새 BOM: 769,000원/세트, 5주 마일스톤 계획
4. **구매검토 보고서 v3 작성 (Jetson 기반)**
   * v2(Pi Only 2세트 750K) → v3(Jetson+Pi 1세트 769K) 전환
   * 설계서 v2.0과 100% 정합 검증
   * 구매 링크, 실행 일정, 리스크 매트릭스 포함

### 2026-04-01: 대시보드 완성 + 비동기 파이프라인 + 문서 교차검증
1. **운영자 대시보드 100% 완성**
   * 자동 새로고침(60초), 로딩 스피너, 혼잡도 분포 도넛 차트, 지도 fitBounds 추가
2. **비동기 수집 엔진 도입 (GSTACK Agent 1)**
   * `pipeline.py`: `asyncio.gather` + `asyncio.to_thread` 병렬 수집 전환
   * boarding/weather/congestion 3개 동시 실행, features는 순차
3. **문서 교차 검증 (QA Inspector + Codex 병렬)**
   * 15건 불일치 발견 및 전체 수정 (하이퍼파라미터, 파일 링크, 디렉토리 구조 등)
4. **Flask-Limiter Rate Limiting (GSTACK CSO)**
   * `extensions.py` 모듈 분리, 전 엔드포인트 IP당 Rate Limit 적용, 429 에러 핸들러
   * predict/stats: 30/min, stations: 60/min, weather: 30/min, 전역: 200/day+60/min

### 2026-04-01: Backend 캐싱 + 보안 강화 + E2E 검증
1. **Backend 피처 계약 동기화**
   * `backend/routes/predict.py`: features dict 10개→7개 동기화 (rain/boarding/alighting 제거)
2. **E2E 통합 테스트 통과**
   * Flask→ML 모델 실제 연동 확인, 더미가 아닌 실제 예측값 반환 검증
3. **Backend Caching 구현 (GSTACK Agent 3)**
   * `/api/predict`: LRU TTL Cache (5분), 응답 800ms→23ms (**35x 개선**)
   * `/api/stats`: DB 쿼리 TTL Cache (60초) — Codex 구현
4. **입력 검증 강화 (GSTACK CSO 일부)**
   * `station_id` regex 검증 (3-10자 영숫자), `hour`/`weekday` isdigit 검증 — Codex 구현
   * Flask-Limiter 적용 지점 마킹 (추후 적용)

### 2026-03-31: Autoresearch 실험 완료
1. **ML 모델 최적화 (Autoresearch 12회 반복)**
   * Baseline(n=100, 10feat, 5.1MB) → Optimized(n=10, 7feat, 0.2MB): **모델 크기 96% 감소, CV 0.9962 유지**
   * Codex 세컨드 오피니언 반영: boarding/alighting 제거(leakage 의심 확인), rain 제거(노이즈)
   * `predict.py` 피처 계약 동기화 완료
   * 실험 로그: `research_log.txt`
2. **GStack 아키텍처 리뷰 문서화**
   * `docs/GSTACK_REVIEW.md`: CEO/Eng/CSO 관점 리뷰 및 Harness 평가 지표 정의

### 2026-03-30: 하네스 빌드 완료
1. **ML 파이프라인 블로커 해소**
   * `collect_congestion.py` 코드 단위 검증 및 `test_collect_congestion.py` 100% Pass 달성.
2. **Backend 구조 정립 및 구동 보장**
   * Flask 코드 분석 및 **SQLite 호환성 버그 패치**. `pytest test_app.py` 100% Pass 달성. 

---

## 🎯 Next Steps 제안 (다음 스텝)

- [x] ~~`gstack` 프레임워크 기반 아키텍처 리뷰~~: 완료 (`docs/GSTACK_REVIEW.md`)
- [x] ~~Harness와 Autoresearch 연동~~: 완료 (12회 반복 실험, `research_log.txt`)
- [x] ~~통합 E2E 테스트 수행~~: 완료 (Flask→ML 실제 연동, 7개 피처 기반 동작 확인)
- [x] ~~Backend Caching 최적화~~ (GSTACK Agent 3): 완료 (LRU TTL Cache, 35x 개선)
- [x] ~~보안 강화~~ (GSTACK CSO 일부): 완료 (입력 검증, Flask-Limiter 마킹)
- [x] ~~비동기 수집 엔진 도입~~ (GSTACK Agent 1): 완료 (`asyncio.gather` 병렬수집, `asyncio.to_thread` 래핑)
- [x] ~~운영자 대시보드 완성~~: 완료 (도넛차트, 자동갱신, 로딩UI, fitBounds)
- [x] ~~Flask-Limiter Rate Limiting 적용~~: 완료 (predict/stats 30/min, stations 60/min, weather 30/min, 429 핸들러)
- [x] ~~Docker 배포 환경 구축~~: 완료 (Dockerfile x2, docker-compose.yml, nginx reverse proxy)
- [x] ~~Raspberry Pi 설계 문서~~: 완료 → **v2.0 Jetson+Pi 구조로 전면 개정** (2026-04-10)
- [x] ~~`counter.py` AI 카운팅 스크립트~~: 완료 (YOLOv8+DeepSORT+Line Crossing, 2026-04-15)
- [x] ~~`/api/crowd-count` 엔드포인트~~: 완료 (POST/GET/history, 7/7 PASS, 2026-04-15)
- [x] ~~`/api/route-recommend` 대체노선 추천 API~~: 완료 (2026-04-28)
- [x] ~~Admin 실시간 카운팅 패널~~: 완료 (2026-04-28)
- [x] ~~Student PWA 출발지/목적지 + 노선 추천~~: 완료 (2026-04-28)
- [x] ~~ML 계약서 동기화 (C1)~~: 완료 — v2.0으로 갱신 (2026-04-28)
- [x] ~~API_BASE 하드코딩 해소 (C2)~~: 완료 — `window.location.origin` 적용 (2026-04-28)
- [ ] 부품 구매 + JetPack 설치 (부품 수령 후)
- [ ] Pi Kiosk + Backend 현장 연동
- [x] ~~Watchdog 스크립트 구현~~ (2026-05-04): watchdog_jetson.sh / watchdog_pi.sh 완성, crontab 등록은 HW 수령 후
- [ ] 카운팅 정확도 튜닝 + 실측 데이터 수집
- [ ] 1차 시연 (5/21)
- [ ] 발표 PPT 실제 작성 () — 박건우 주담당
- [ ] 유사프로젝트 사례분석 추가 (뻐정 외 2건 이상) — 팀원 기입
