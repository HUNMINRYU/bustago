# BUSTAGO_업무흐름도.docx (v1) 정오표

> **작성일**: 2026-04-22
> **대상 문서**: [BUSTAGO_업무흐름도.docx](BUSTAGO_업무흐름도.docx) (v1)
> **상태**: 🟡 **구버전** — v2가 최신본입니다

---

## 최신본 안내

이 `.docx` 문서는 **v1 초안**이며, 1차 피드백 반영으로 v2가 발행되었습니다.

**👉 최신본**: [BUSTAGO_업무흐름도_v2.md](BUSTAGO_업무흐름도_v2.md)

## v1 대비 v2 주요 변경점

| 항목 | v1 (.docx) | v2 (.md) |
|------|-----------|----------|
| 사용자 여정 | System Lane만 | System Lane + User Lane 2레인 병행 |
| 하드웨어 | Raspberry Pi + Camera (CPU 추론) | **Jetson Orin Nano(AI) + Pi 4(Kiosk)** 역할 분리 |
| 카메라 | 다중 앵글 | **1대** (Jetson GPU로 25~40 FPS 확보) |
| 카운팅 로직 | YOLOv8만 | YOLOv8 + **DeepSORT + Line Crossing** (중복 방지) |
| 데이터 소스 | 일반 API 명시 | 광주 BIS API, 승하차 XLSX 구체화 |

## 후속 조치

v1을 현재 시점에 읽는 독자는 반드시 **[v2 본문](BUSTAGO_업무흐름도_v2.md)**을 참조할 것.
