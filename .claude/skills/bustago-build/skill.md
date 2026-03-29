---
name: bustago-build
description: "BUSTAGO 프로젝트 전체 빌드를 오케스트레이션하는 통합 스킬. ML 파이프라인 완성, Flask Backend 구축, Frontend PWA/Dashboard 구축, 통합 QA를 순차+병렬로 조율. 'BUSTAGO 빌드', '프로젝트 빌드', '전체 구현', '하네스 실행', '에이전트 팀 실행' 요청 시 반드시 이 스킬을 사용."
---

# BUSTAGO Build Orchestrator

BUSTAGO 프로젝트의 에이전트 팀을 조율하여 ML → Backend → Frontend 전체 파이프라인을 빌드하는 통합 스킬.

## 실행 모드: 에이전트 팀

## 에이전트 구성

| 팀원 | 에이전트 파일 | 역할 | 스킬 | 주요 산출물 |
|------|-------------|------|------|-----------|
| ml-engineer | .claude/agents/ml-engineer.md | ML 파이프라인 | bustago-ml | 모델 + 계약서 |
| backend-engineer | .claude/agents/backend-engineer.md | Flask API | bustago-backend | API + 계약서 |
| frontend-engineer | .claude/agents/frontend-engineer.md | PWA/Dashboard | bustago-frontend | 화면 코드 |
| qa-inspector | .claude/agents/qa-inspector.md | 통합 QA | bustago-qa | QA 리포트 |

## 워크플로우

### Phase 1: 준비
1. 프로젝트 루트에 `_workspace/` 디렉토리 생성
2. 기존 코드 상태 확인:
   - ml/data_collection/collect_boarding.py 존재 및 완성도 확인
   - ml/data_collection/collect_weather.py 존재 및 완성도 확인
   - ml/preprocessing/build_features.py 존재 및 완성도 확인
3. `_workspace/00_input/`에 현재 Feature 스키마 저장

### Phase 2: ML 파이프라인 빌드 (Team 1 -- ML 단독)

1. 팀 생성:
   ```
   TeamCreate(
     team_name: "bustago-ml-team",
     members: [
       { name: "ml-engineer", agent_type: "ml-engineer", model: "opus",
         prompt: "BUSTAGO ML 파이프라인을 완성하라.
         Skill 도구로 bustago-ml 스킬을 로드하여 참조하라.
         1) collect_congestion.py 구현
         2) pipeline.py 구현
         3) train_rf.py 구현
         4) predict.py 구현
         5) _workspace/01_ml_model_contract.json에 모델 계약서 저장
         기존 코드 패턴(collect_boarding.py, build_features.py)을 반드시 참조하라." }
     ]
   )
   ```

2. 작업 등록:
   ```
   TaskCreate(tasks: [
     { title: "collect_congestion.py 구현", assignee: "ml-engineer" },
     { title: "pipeline.py 구현", assignee: "ml-engineer",
       depends_on: ["collect_congestion.py 구현"] },
     { title: "train_rf.py 구현", assignee: "ml-engineer" },
     { title: "predict.py 구현", assignee: "ml-engineer",
       depends_on: ["train_rf.py 구현"] },
     { title: "모델 계약서 작성", assignee: "ml-engineer",
       depends_on: ["predict.py 구현"] }
   ])
   ```

3. ML 엔지니어가 5개 작업을 수행
4. 완료 대기 후 `_workspace/01_ml_model_contract.json` 존재 확인
5. Team 1 정리

### Phase 3: Backend + Frontend + QA 병렬 빌드 (Team 2)

> Phase 2 팀을 정리한 후 새 팀을 구성한다. _workspace/의 ML 산출물은 보존되어 새 팀이 Read로 접근 가능.

1. 팀 생성:
   ```
   TeamCreate(
     team_name: "bustago-app-team",
     members: [
       { name: "backend-engineer", agent_type: "backend-engineer", model: "opus",
         prompt: "BUSTAGO Flask Backend를 구축하라.
         Skill 도구로 bustago-backend 스킬을 로드하여 참조하라.
         1) _workspace/01_ml_model_contract.json을 먼저 읽어 모델 계약을 확인.
         2) backend/ 하위에 Flask 앱 구조 생성.
         3) schema.sql, REST API 4개 엔드포인트 구현.
         4) requirements.txt 작성.
         5) _workspace/02_api_contract.json에 API 계약서 저장.
         6) API 계약서 완성 시 frontend-engineer에게 SendMessage로 알림." },
       { name: "frontend-engineer", agent_type: "frontend-engineer", model: "opus",
         prompt: "BUSTAGO Frontend를 구축하라.
         Skill 도구로 bustago-frontend 스킬을 로드하여 참조하라.
         1) 정적 UI 구조(HTML/CSS)를 먼저 구현.
         2) backend-engineer가 _workspace/02_api_contract.json을 완성하면 API 연동 구현.
         3) student PWA + admin Dashboard + shared/api.js.
         4) manifest.json + service-worker.js.
         5) _workspace/03_frontend_routes.json에 화면 목록 저장." },
       { name: "qa-inspector", agent_type: "qa-inspector", model: "opus",
         prompt: "BUSTAGO 통합 정합성을 검증하라.
         Skill 도구로 bustago-qa 스킬을 로드하여 참조하라.
         1) _workspace/01_ml_model_contract.json을 읽고 ML 코드와 대조.
         2) backend-engineer가 API 구현 완료 시 ML↔Backend 교차 검증.
         3) frontend-engineer가 화면 구현 완료 시 Backend↔Frontend 교차 검증.
         4) 불일치 발견 시 해당 에이전트에게 SendMessage로 구체적 수정 요청.
         5) _workspace/04_qa_report.md에 검증 결과 저장." }
     ]
   )
   ```

2. 작업 등록:
   ```
   TaskCreate(tasks: [
     { title: "Flask 앱 구조 생성", assignee: "backend-engineer" },
     { title: "MySQL 스키마 작성", assignee: "backend-engineer" },
     { title: "REST API 엔드포인트 구현", assignee: "backend-engineer",
       depends_on: ["Flask 앱 구조 생성"] },
     { title: "API 계약서 작성", assignee: "backend-engineer",
       depends_on: ["REST API 엔드포인트 구현"] },
     { title: "학생 PWA 정적 UI", assignee: "frontend-engineer" },
     { title: "운영자 대시보드 정적 UI", assignee: "frontend-engineer" },
     { title: "API 연동 구현", assignee: "frontend-engineer",
       depends_on: ["API 계약서 작성"] },
     { title: "PWA manifest/SW", assignee: "frontend-engineer",
       depends_on: ["학생 PWA 정적 UI"] },
     { title: "QA: ML↔Backend 검증", assignee: "qa-inspector",
       depends_on: ["REST API 엔드포인트 구현"] },
     { title: "QA: Backend↔Frontend 검증", assignee: "qa-inspector",
       depends_on: ["API 연동 구현"] },
     { title: "QA: 전체 데이터 흐름 검증", assignee: "qa-inspector",
       depends_on: ["QA: ML↔Backend 검증", "QA: Backend↔Frontend 검증"] }
   ])
   ```

**팀원 간 통신 규칙:**
- backend-engineer는 API 계약서 완성 시 frontend-engineer에게 SendMessage
- frontend-engineer는 API 응답 형식 변경 필요 시 backend-engineer에게 SendMessage
- qa-inspector는 불일치 발견 시 해당 에이전트(들)에게 SendMessage
- 각 팀원은 작업 완료 시 TaskUpdate로 상태 갱신

**산출물 저장:**

| 팀원 | 출력 경로 |
|------|----------|
| backend-engineer | backend/ + _workspace/02_api_contract.json |
| frontend-engineer | frontend/ + _workspace/03_frontend_routes.json |
| qa-inspector | _workspace/04_qa_report.md |

### Phase 4: 통합 검증
1. 모든 팀원 작업 완료 대기
2. `_workspace/04_qa_report.md` Read하여 미해결 이슈 확인
3. 미해결 이슈가 있으면 해당 팀원에게 수정 요청
4. requirements.txt가 backend/에 존재하는지 확인

### Phase 5: 정리
1. 팀원들에게 종료 요청 (SendMessage)
2. 팀 정리
3. `_workspace/` 보존 (사후 검증/감사 추적용)
4. 사용자에게 결과 요약:
   - ML: 구현된 파일 목록, 모델 accuracy
   - Backend: 엔드포인트 목록, 스키마 테이블 수
   - Frontend: 화면 목록, PWA 상태
   - QA: 통과/실패 항목 수

## 데이터 흐름

```
[리더] → Phase 2: TeamCreate(ml-team)
              │
         [ml-engineer] → collect_congestion.py
                       → pipeline.py
                       → train_rf.py + predict.py
                       → _workspace/01_ml_model_contract.json
              │
         TeamDelete(ml-team)
              │
         Phase 3: TeamCreate(app-team)
              │
         [backend-engineer] ←Read── 01_model_contract.json
              │                     │
              │              ──SendMessage──→ [frontend-engineer]
              │                                    │
              ↓                                    ↓
         backend/ + 02_api_contract.json    frontend/ + 03_frontend_routes.json
              │                                    │
              └────────── [qa-inspector] ──────────┘
                               │
                     04_qa_report.md
```

## 에러 핸들링

| 상황 | 전략 |
|------|------|
| ML 팀 실패 | 1회 재시도. 재실패 시 기존 build_features.py 출력만으로 Backend 진행 (모델은 더미) |
| Backend 구현 실패 | Frontend는 목업 API(하드코딩 응답)로 진행 |
| Frontend 구현 실패 | Backend + ML만으로 curl 테스트 가능한 상태로 마무리 |
| QA 불일치 다수 발견 | 리더가 우선순위 정하여 크래시 유발 항목만 수정 요청 |
| 팀원 간 데이터 충돌 | 출처 명시 후 병기, 삭제하지 않음 |

## 테스트 시나리오

### 정상 흐름
1. Phase 1에서 기존 ML 코드 상태 확인
2. Phase 2에서 ml-engineer가 4개 파일 + 계약서 생성
3. Phase 3에서 3명이 병렬 작업, backend→frontend 순 계약서 전달
4. Phase 4에서 QA 리포트 확인, 전체 통과
5. 예상 결과: ml/ 4개 파일, backend/ 8+ 파일, frontend/ 10+ 파일 생성

### 에러 흐름
1. Phase 3에서 qa-inspector가 API 응답 필드명 불일치 발견
2. qa-inspector가 backend-engineer와 frontend-engineer 모두에게 SendMessage
3. backend-engineer가 API 응답 수정
4. frontend-engineer가 fetch 파싱 수정
5. qa-inspector가 재검증 후 통과 보고
