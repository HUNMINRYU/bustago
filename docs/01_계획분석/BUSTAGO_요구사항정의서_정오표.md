# BUSTAGO_요구사항정의서.docx 정오표

> **작성일**: 2026-04-22
> **대상 문서**: [BUSTAGO_요구사항정의서.docx](BUSTAGO_요구사항정의서.docx)
> **사유**: 하드웨어 아키텍처 v2.0 전환(2026-04-10)으로 원문의 Raspberry Pi 단독 구조 기술이 최신 Jetson+Pi 2보드 역할 분리 구조와 불일치함.

---

## 갱신 대상 요구사항

원문에서 "**Raspberry Pi 기반**"으로 기술된 모든 항목은 아래와 같이 재해석한다.

| 원문 표현 | 최신 설계 (v2.0) |
|-----------|-----------------|
| Raspberry Pi 기반 현장 디스플레이 프로토타입 | **Jetson Orin Nano(AI 추론) + Raspberry Pi 4(Kiosk 디스플레이)** 2보드 역할 분리 프로토타입 |
| YOLOv8 기반 실시간 인원 카운팅 (Pi CPU) | **YOLOv8 + DeepSORT + Line Crossing** (Jetson GPU, 25~40 FPS) |
| Raspberry Pi + Camera 캠퍼스 내 시범 정류장 | Jetson Orin Nano + Pi Camera v2 **카메라 1대** (고 FPS로 1대 충분, 하향 45°) |

## 갱신 사유

- **Pi 4 CPU 한계**: YOLOv8 추론 2~5 FPS → DeepSORT 트래킹 불가 → 중복 카운팅 발생
- **Jetson Orin Nano GPU (40 TOPS)**: YOLOv8-nano TensorRT FP16에서 25~40 FPS 안정 확보 → DeepSORT 적용 가능
- **역할 분리 구조**: Jetson(AI 전용) + Pi(Kiosk 전용)으로 각 보드 부하 최소화

## 참조 문서 (최신)

- [하드웨어 연동 설계서 v2.0](../03_구축/하드웨어_연동_설계.md)
- [하드웨어 구매검토 보고서 v3](../05_배포/BUSTAGO_하드웨어_구매검토_보고서_v3.md)
- [시스템 플로우차트 v2](BUSTAGO_시스템플로우차트_v2.md)
- [업무 흐름도 v2](BUSTAGO_업무흐름도_v2.md)

## 구현 현황 (2026-04-22 기준)

- ✅ `hardware/counter.py`: YOLOv8 + DeepSORT + Line Crossing 구현 완료
- ✅ `/api/crowd-count`: POST/GET/history 엔드포인트 구현 완료 (7/7 테스트 PASS)
- ⬜ Jetson + Pi 현물 구매 및 현장 설치 (4/18~)
