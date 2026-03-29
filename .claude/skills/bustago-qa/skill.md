---
name: bustago-qa
description: "BUSTAGO 통합 정합성 QA 스킬. ML 모델 출력 → Backend API → Frontend 간의 데이터 흐름 교차 검증. 필드명 불일치, 타입 불일치, 누락된 연결 탐지. QA 검증, 통합 테스트, 경계면 점검, 데이터 흐름 추적 시 반드시 이 스킬을 사용."
---

# BUSTAGO QA

## 검증 순서 (점진적 QA)

### Checkpoint 1: ML 완성 직후
검증 대상: predict.py ↔ _workspace/01_ml_model_contract.json
- predict_congestion() 함수 시그니처가 계약서와 일치하는가
- Feature 이름/순서가 build_features.py의 feature_cols와 일치하는가
- 반환값 shape(level, label, probabilities)이 계약서의 output과 일치하는가
- 모델 파일 경로가 계약서의 model_path와 일치하는가
- LABEL_MAP이 계약서의 label_map과 일치하는가

### Checkpoint 2: Backend API 구현 직후
검증 대상: routes/predict.py ↔ ml/models/predict.py ↔ 01_model_contract.json
- API 쿼리 파라미터(station_id, hour, weekday)가 predict_congestion() 입력으로 올바르게 변환되는가
- API 응답의 prediction.level이 predict_congestion()의 level과 같은 타입(int)인가
- label_map이 ML(여유/보통/혼잡/매우혼잡)과 Backend에서 동일한가
- 모델 import 경로가 올바른가 (sys.path 조작 확인)
- 에러 응답 형식이 { "status": "error", "message": "...", "code": N } 을 따르는가

### Checkpoint 3: Frontend 연동 직후
검증 대상: frontend/shared/api.js ↔ 02_api_contract.json ↔ backend routes
- fetch URL(/api/predict 등)이 Backend 라우트와 일치하는가
- 응답 JSON 접근 키(data.prediction.level 등)가 실제 API 응답과 일치하는가
- CONGESTION 객체의 키(0,1,2,3)가 API의 level 범위(0-3)와 일치하는가
- STATIONS 객체의 ARS번호가 Backend의 stations 테이블과 일치하는가
- API_BASE URL이 Backend 서버 주소(localhost:5000)와 일치하는가

### Checkpoint 4: 전체 E2E 데이터 흐름
- ARS번호 형식이 전 계층에서 문자열 5자리로 일관되는가
- 시간 형식(hour 0-23 int)이 전 계층에서 일관되는가
- 날씨 코드(weather 0-3)가 ML의 weather와 Frontend 표시에서 같은 의미인가
- 혼잡도 색상 코드가 Frontend에서 올바르게 매핑되는가

## 검증 리포트 형식 (_workspace/04_qa_report.md)

```markdown
# BUSTAGO QA Report
생성일: YYYY-MM-DD

## Checkpoint 1: ML ↔ Contract
| 항목 | 상태 | 상세 |
|------|------|------|
| Feature 이름 일치 | PASS/FAIL | [상세] |
| 반환값 shape 일치 | PASS/FAIL | [상세] |
| 모델 경로 일치 | PASS/FAIL | [상세] |
| Label map 일치 | PASS/FAIL | [상세] |

## Checkpoint 2: Backend ↔ ML
| 항목 | 상태 | 상세 |
|------|------|------|
| ...  | ...  | ...  |

## Checkpoint 3: Frontend ↔ Backend
| 항목 | 상태 | 상세 |
|------|------|------|
| ...  | ...  | ...  |

## Checkpoint 4: E2E
| 항목 | 상태 | 상세 |
|------|------|------|
| ...  | ...  | ...  |

## 요약
- 총 검증 항목: N개
- PASS: N개
- FAIL: N개
- 미검증: N개

## 미해결 이슈
1. [이슈 설명 + 영향받는 파일 + 수정 제안]
```
