# API 키 rotate 가이드 — 졸업작품 평가 후 진행

> 작성일: 2026-05-16 (v1.0) / 2026-05-17 (v1.1 정책 결정 반영)
> 상태: **졸업작품 평가 후 실행** (2026-05-17 결정으로 시점 확정 — 시연/대회 직전 X)
> 사유: 진단 §6 / §8 P0 — git history에 광주 BIS API 키 노출
> 작성: 류훈민

---

## 0. 2026-05-17 정책 결정 — 새 키 발급 보류

5/18에 새 키 발급·교체를 진행하려 했으나 **시연·대회 안정성 우선**으로 일정 변경.

**결정 근거:**

| 요인 | 평가 |
|---|---|
| 광주 BIS API 권한 범위 | read-only 공공 OpenAPI — 키 노출되어도 권한 확장·DB 변조 불가 |
| 노출 시 최대 피해 | 일일 쿼터 소모 (낮음, 회복 가능) |
| 새 키 발급 시 위험 | 활성화 1~2시간 대기, 시연 직전 키 교체 시 인증 실패 위험 |
| 작업 트리 노출 | **이미 제거 완료** (5/16 `6e65d37` + 5/17 `82df0ec`) |
| git history 잔존 | 그대로 — 평가위원이 `git log -p`로 발견 가능 |

**결론**: rotate는 졸업작품 평가 종료 후 (예: 2026-06-10 이후) git history 정리와 함께 묶어서 일괄 처리.

> 본 결정은 risk-managed 선택이며, 책임은 류훈민(팀장)에게 있음.
> 발표 Q&A 모범답안은 본 문서 §5에 추가.

---

## 1. 배경

2026-05-13 광주 BIS API를 통합하는 과정에서 `backend/config.py`에 광주 BIS API 키가
하드코딩 fallback으로 들어갔다. 진단 §6 보고서에서 🔴 Critical로 지목되었고,
시연 직전 키 교체는 시연 망 위험이 있어 다음 절차로 분할 처리한다.

**2026-05-16 처리 완료**: 코드 하드코딩 제거 + `.env`로 이동 + 빈 키 경고 (커밋 본 PR).
**시연 후 필요**: 실제 키 rotate (공공데이터포털 새 키 발급) + git history 정리(선택).

git history에 남은 이전 키는 코드만 바꿔서는 사라지지 않는다. 본 가이드는 시연 후
키 교체 + 적용 절차를 단계별로 설명한다.

---

## 2. 위험 분석

| 위험 | 확률 | 영향 |
|---|---|---|
| 누군가 GitHub 공개 저장소에서 키 발견 → 무단 사용 | 중 | 광주 BIS 호출 쿼터 소모, 본인 계정 차단 가능 |
| 키 자체로 추가 권한 획득 | 낮 | 광주 BIS는 read-only OpenAPI라 권한 확장 위험 적음 |
| 정상 사용량 초과로 일시 차단 | 낮 | 키가 알려져 있더라도 광주 BIS는 일일 쿼터 있음 |

→ **시급도 중**. 시연 후 1주일 내 처리.

---

## 3. Rotate 절차 (시연 후 5/22~)

### 3.1 새 키 발급

1. https://www.data.go.kr 로그인 (기존 발급자 계정)
2. 마이페이지 → 데이터 활용 → 활용 신청 현황
3. **"광주광역시_버스정보시스템 OpenAPI"** 항목 선택
4. **인증키 재발급** 버튼 클릭
5. 새 인증키 (Encoding key) 복사

> 광주광역시 데이터: https://www.data.go.kr/data/15043867/openapi.do

### 3.2 키 교체

1. 새 키를 `.env`에 저장:
   ```
   GJ_BIS_API_KEY=새_키_값
   ```
2. 변경 후 backend 재시작:
   ```bash
   pkill -f "flask run" || pkill -f gunicorn
   cd backend && PYTHONPATH=.. python -m flask --app app run
   ```
3. 응답 확인:
   ```bash
   curl "http://localhost:5000/api/arrive/1981" | head
   ```
   → 정상 응답이면 OK. `serviceKey 등록되지 않은` 또는 `INVALID_REQUEST_PARAMETER`
   에러면 키 발급 후 1~2시간 활성화 대기 필요.

### 3.3 이전 키 폐기 확인

공공데이터포털에서 재발급하면 이전 키는 자동 폐기됨 (보통). 확인:
- 마이페이지에서 "이전 키" 표기가 사라졌는지 확인.

---

## 4. git history 정리 (선택, 권장도 낮음)

이전 키가 git history의 `backend/config.py:38-40`에 남아있다. 완전 제거하려면
`git filter-branch` 또는 `git filter-repo`로 history 재작성이 필요하다.

**권장 안 함 — 이유**:
1. force-push 필요 → 협업 브랜치 위험 (다른 사람 clone과 SHA 불일치)
2. 키는 이미 3.1~3.3으로 무효화됨 → history에 남아도 실제 권한 없음
3. 캡스톤 졸업작품 평가 후 저장소 정리 단계에서 처리 가능

**그래도 정리하려면 (시연·평가 완료 후)**:
```bash
# git-filter-repo 설치
pip install git-filter-repo

# config.py에서 키 라인을 마스킹된 텍스트로 교체
git filter-repo --replace-text <(echo 'bN25YqJDY0QChe...==' )

# 모든 클론자에게 재클론 통보 후 force-push
git push origin --force --all
git push origin --force --tags
```

→ 본 캡스톤은 졸업작품 평가 후 처리 권장.

---

## 5. 향후 예방

- `.env`는 절대 커밋하지 않음 (`.gitignore`의 `*.env` 패턴으로 보호 중 ✅)
- 새 키 추가 시 `.env.example`에 자리만 잡고 실제 값은 .env에만
- pre-commit hook으로 키 패턴 차단 가능 (예: `gitleaks` 또는 `detect-secrets`)
- PR 리뷰 시 `git diff`로 base64 패턴 / 키 형식 확인

---

## 5.5 발표 Q&A 모범답안 (2026-05-17 추가)

**Q. "git history에 광주 BIS API 키가 노출되어 있는데, 왜 시연·대회 전에 안 바꾸시나요?"**

A: 의도된 risk-managed 결정입니다. 세 가지 근거:
1. 광주 BIS는 **read-only 공공 OpenAPI**라 키 노출되어도 권한 확장이나 데이터 변조가 불가능합니다.
   최대 피해는 일일 쿼터 소모 정도이고 회복 가능합니다.
2. 새 키 발급은 활성화에 1~2시간 대기가 필요한데, **시연 직전 키 교체는 인증 실패 위험**이
   더 큽니다.
3. **작업 트리의 키 노출은 이미 제거**(`6e65d37` + `82df0ec`)했고, git history 정리는
   `git filter-repo`로 평가 종료 후 일괄 처리할 계획입니다 (가이드 §4).

본 결정은 진단 §8 P0의 deferred 트랙에 포함되어 있고, 책임 소재는 팀장(류훈민)에게
있음을 명문화했습니다.

---

## 6. 체크리스트

- [ ] 새 키 발급 (data.go.kr 마이페이지)
- [ ] `.env`의 GJ_BIS_API_KEY 갱신
- [ ] backend 재시작 + `/api/arrive/<busstop_id>` 응답 정상 확인
- [ ] 시연 영상 / 발표 자료에 API 키가 화면에 노출되지 않았는지 재확인
- [ ] (선택) 졸업작품 평가 후 git history 정리

---

## 7. 변경 이력

| 버전 | 날짜 | 변경 사항 | 작성자 |
|---|---|---|---|
| v1.0 | 2026-05-16 | 최초 작성 (코드 하드코딩 제거 + rotate 절차 안내) | 류훈민 |
