# BUSTAGO_유스케이스정의서.docx 정오표

> **작성일**: 2026-04-22
> **대상 문서**: [BUSTAGO_유스케이스정의서.docx](BUSTAGO_유스케이스정의서.docx)
> **사유**: 하드웨어 아키텍처 v2.0 전환(2026-04-10)에 따라 유스케이스 "비고" 항목의 Raspberry Pi 단독 기술 재해석 필요.

---

## 갱신 대상 유스케이스

원문 "비고" 항목에 기술된 **Raspberry Pi 기반으로 동작** 문구는 아래와 같이 재해석한다.

| 원문 비고 | 최신 설계 (v2.0) |
|-----------|-----------------|
| Raspberry Pi 기반으로 동작하며, YOLOv8 감지 결과와 예측 결과를 모두 표시 | **Jetson Orin Nano(YOLOv8+DeepSORT AI 추론) + Raspberry Pi 4(Kiosk 디스플레이)** 2보드 구조로 동작. 카운팅 결과는 Jetson→Backend→Pi Kiosk 순으로 전파 |

## 데이터 흐름 재정의

```
[카메라 1대] → [Jetson Orin Nano]
                    │
                    ├─ YOLOv8 (사람 감지)
                    ├─ DeepSORT (Track ID 할당)
                    └─ Line Crossing (IN/BOARD 카운팅)
                    │
                    ▼ POST /api/crowd-count (10초 간격)
              [Backend (Flask)]
                    │
                    ▼
              [Raspberry Pi 4 (Chromium Kiosk)]
                    │
                    └─ 학생 PWA (예측 혼잡도 + 실시간 카운팅)
```

## 참조 문서 (최신)

- [하드웨어 연동 설계서 v2.0](../03_구축/하드웨어_연동_설계.md)
- [요구사항정의서 정오표](BUSTAGO_요구사항정의서_정오표.md)
- [시스템 플로우차트 v2](BUSTAGO_시스템플로우차트_v2.md)

## 구현 참조 코드

- `hardware/counter.py` — Jetson측 AI 카운팅 스크립트
- `backend/routes/crowd.py` — `/api/crowd-count` 엔드포인트
- `frontend/student/` — Pi Kiosk에서 띄울 PWA
