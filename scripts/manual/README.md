# Manual scripts

수동 호출용 ad-hoc 스크립트 모음. pytest 자동 수집 대상이 아니며, 개발 중 외부 API
동작 확인용으로만 사용.

## 파일

| 파일 | 용도 |
|---|---|
| `api_smoke_test.py` | 서울 열린데이터광장 API 1회 호출 smoke test (`SEOUL_OPENDATA_API_KEY` 필요) |
| `api_smoke_test_v2.py` | 공공데이터포털 API v2 호출 smoke test (`DATA_GO_KR_API_KEY` 필요) |

## 실행

```bash
# 프로젝트 루트에서
.venv/bin/python scripts/manual/api_smoke_test.py
.venv/bin/python scripts/manual/api_smoke_test_v2.py
```

## 이동 이력

원래 `ml/data_collection/test_*.py`에 있었으나 *pytest 형식이 아닌 ad-hoc 스크립트*라 혼란을 막기 위해 2026-05-17에 `scripts/manual/`로 이동. 파일명도 `api_smoke_test.py`로 변경 (`test_*` 접두사 제거).

원본 위치의 진짜 pytest는 `ml/data_collection/test_collect_congestion.py`에 그대로 유지됨.
