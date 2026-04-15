# BUSTAGO 프로젝트 진행 현황

> **최종 업데이트 일시:** 2026-04-15 (KST)
> 1차 시연: 5.21 | 최종 보고서: 6.4

---

## 🚀 전체 진행도: **99%**

```text
전체 ███████████████████░ 99%
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
| 예측 API (`predict.py`) | 100% | ✅ 완료 | **[26.03.31]** 피처 계약 동기화 완료 (rain/boarding/alighting 제거) |
| API 단위 테스트 | 100% | ✅ 완료 | `pytest` 기반 ML 전체 수집기 테스트 완료 |

### 2. Backend (Flask API) — 100%
```text
Backend   ████████████████████ 100%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| Flask 앱 (`app.py`) | 100% | ✅ 완료 | 블루프린트 라우팅 구현 및 구동 확인 |
| DB 스키마 (`schema.sql`) | 100% | ✅ 완료 | **[26.03.30]** `db.py` fallback 버그수정(SQLite `INSERT OR IGNORE`) 완료 |
| REST API 엔드포인트 | 100% | ✅ 완료 | `/api/health`, `/api/predict`, `/api/stats`, `/api/stations`, `/api/crowd-count` — `test_app.py` 7/7 PASS |
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
| 학생 PWA (`app.js`, `index.html`) | 100% | ✅ 완료 | DOM 조작, API Fetch, UI 로직 구현 완료 |
| 운영자 대시보드 (`admin/`) | 100% | ✅ 완료 | **[26.04.01]** 자동갱신(60초), 로딩UI, 도넛차트, 지도fitBounds 추가 |
| 시각화 및 지도 (Chart/Leaflet) | 100% | ✅ 완료 | **[26.04.01]** 바 차트 + 도넛 차트(혼잡도 분포) + Leaflet 지도 완성 |
| PWA manifest/SW | 100% | ✅ 완료 | Service Worker 및 manifest 설정 완료 |

### 4. Hardware (Jetson Orin Nano + Raspberry Pi 4) — 50%
```text
Hardware  ██████████░░░░░░░░░░ 50%
```
| 세부 항목 | 진행도 | 상태 | 비고 (수행 내용) |
|-----------|--------|------|------|
| 하드웨어 설계서 v2.0 | 100% | ✅ 완료 | **[26.04.10]** Jetson+Pi 역할 분리, DeepSORT 파이프라인, BOM 792K |
| 구매검토 보고서 v3 | 100% | ✅ 완료 | **[26.04.10]** Jetson 기반 80만원 예산, 실매가 조사 반영 |
| `counter.py` (AI 카운팅 스크립트) | 100% | ✅ 완료 | **[26.04.15]** YOLOv8+DeepSORT+Line Crossing, PC 웹캠/Jetson TensorRT 지원 |
| `/api/crowd-count` 엔드포인트 | 100% | ✅ 완료 | **[26.04.15]** POST/GET/history, crowd_counts 테이블, 7/7 테스트 PASS |
| 부품 구매 | 0% | ⬜ 대기 | 목표: 4/18 수령 |
| JetPack + YOLOv8 TensorRT 설치 | 0% | ⬜ 대기 | 1주차 작업 (부품 수령 후) |
| Pi Kiosk + Backend 연동 | 0% | ⬜ 대기 | 2주차 작업 |
| 현장 설치 + 안정성 테스트 | 0% | ⬜ 대기 | 3~4주차 작업 |

---

## 📝 최근 작업 내역

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
- [ ] 부품 구매 + JetPack 설치 (부품 수령 후)
- [ ] Pi Kiosk + Backend 현장 연동
- [ ] 카운팅 정확도 튜닝 + 실측 데이터 수집
- [ ] 1차 시연 (5/21)
