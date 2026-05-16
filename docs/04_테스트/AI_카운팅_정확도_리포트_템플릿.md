# AI 카운팅 정확도 리포트 (데이터 기반 평가)

> 버전: v2.0
> 작성일: [실측 완료 후 기입]
> 평가 방식: 실시간 수동 카운팅 비교를 사용하지 않고, 라벨링된 데이터셋과 녹화 영상의 사후 라벨 기준으로 평가
> 근거 spec: `docs/superpowers/specs/2026-05-16-yolo-data-track-design.md`

---

## 1. 평가 개요

| 항목 | 내용 |
|---|---|
| AI 시스템 | Jetson Orin Nano + YOLO11n + DeepSORT + Line Crossing |
| 카메라 | Pi Camera v2 (CSI) 또는 USB 웹캠 |
| 평가 환경 | 데이터셋 self_v1 val split + 사후 라벨링된 eval_videos |
| 평가 책임 | 류훈민 |
| Ground Truth | 사람이 라벨링한 bbox / 영상 사후 검토 라인 통과 횟수 |

---

## 2. 평가 지표 정의

### 2.1 Detection 단계 (val split 기반)

| 지표 | 의미 | 측정 방법 |
|---|---|---|
| Precision | TP / (TP+FP) | Ultralytics `yolo val` |
| Recall | TP / (TP+FN) | Ultralytics `yolo val` |
| mAP50 | IoU 0.5 기준 평균 정밀도 | Ultralytics `yolo val` (주 지표) |
| mAP50-95 | IoU 0.5~0.95 평균 | Ultralytics `yolo val` (부 지표) |

### 2.2 Counting 단계 (녹화 영상 사후 라벨 기반)

| 지표 | 의미 | 측정 방법 |
|---|---|---|
| IN 오차율 | AI count_in vs 영상 사후 라벨 라인 통과 횟수 | `hardware/eval_counting.py` |
| BOARD 오차율 | AI count_board vs 사후 라벨 탑승 횟수 | 동일 |
| Track ID 분기 횟수 (부지표) | 한 사람이 여러 ID로 추적된 횟수 | DeepSORT 로그 |

> 주의: 실시간 현장 수동 카운팅은 본 리포트에서 사용하지 않음 (2026-05-16 결정).

### 2.3 Runtime

| 지표 | 측정 방법 |
|---|---|
| FPS | `counter.py --debug` 콘솔 출력 |
| 추론 latency (ms/frame) | YOLO predict 자체 시간 |
| End-to-end latency (선택) | 프레임 캡처 → POST 완료 |

수식:
- IN 오차율 (%) = |AI IN - GT IN| / GT IN × 100
- BOARD 오차율 (%) = |AI BOARD - GT BOARD| / GT BOARD × 100
- 평균 오차율 = (IN + BOARD) / 2

---

## 3. 평가 데이터

### 3.1 Detection val split

| Split | 출처 | 매수 | 라벨링 담당 |
|---|---|---|---|
| public train | [Phase 1-1에서 선택된 Roboflow 데이터셋] | [기입] | 외부 |
| public val | 동일 | [기입] | 외부 |
| self_v1 train | 광주대 INS01 자체촬영 (5/21 이후) | [기입] | 류훈민 (auto-label + 검수) |
| self_v1 val | 동일 | [기입] | 동일 |

### 3.2 Counting 평가 영상 (eval_videos)

| 영상 | 길이 | 환경 | GT IN | GT BOARD |
|---|---|---|---|---|
| video01 | [기입] 분 | 밝은 실내 | [기입] | [기입] |
| video02 | [기입] 분 | 어두움/역광 | [기입] | [기입] |
| video03 | [기입] 분 | 다중 동시 통과 | [기입] | [기입] |

---

## 4. 결과

### 4.1 Detection 결과 (self_v1 val 기준)

| 모델 / 조건 | Precision | Recall | mAP50 | mAP50-95 | 판단 |
|---|---|---|---|---|---|
| YOLO11n baseline (yolo11n.pt) | [기입] | [기입] | [기입] | [기입] | 기준선 |
| Fine-tuned 1차 (자체 데이터) | [기입] | [기입] | [기입] | [기입] | 개선 여부 |
| Fine-tuned 2차 (+ 증강) | [기입] | [기입] | [기입] | [기입] | 최종 후보 |

부록: baseline의 public val 성능 (도메인 일반화 참조)

| 모델 / val | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| YOLO11n baseline / public val | [기입] | [기입] | [기입] | [기입] |

### 4.2 Counting 결과

| 모델 / 영상 | AI IN | GT IN | IN 오차율 | AI BOARD | GT BOARD | BOARD 오차율 |
|---|---|---|---|---|---|---|
| baseline / video01 | [기입] | [기입] | [기입] | [기입] | [기입] | [기입] |
| baseline / video02 | [기입] | [기입] | [기입] | [기입] | [기입] | [기입] |
| baseline / video03 | [기입] | [기입] | [기입] | [기입] | [기입] | [기입] |
| fine-tune1 / video01 | [기입] | [기입] | [기입] | [기입] | [기입] | [기입] |
| ... | | | | | | |

### 4.3 Runtime 결과

| 모델 / 입력 | FPS | 추론 ms/frame | End-to-end ms | 디바이스 |
|---|---|---|---|---|
| baseline / USB웹캠 640x480 | 35 | 28 | [기입] | Jetson Orin Nano (2026-05-16 측정) |
| fine-tune1 / [동일] | [기입] | [기입] | [기입] | [기입] |
| fine-tune2 / [동일] | [기입] | [기입] | [기입] | [기입] |
| TensorRT engine / [기입] | [기입] | [기입] | [기입] | [기입] (선택) |

---

## 5. 환경별 오차 분석

| 환경 조건 | 영상 | 모델 | mAP50 | IN 오차율 | 비고 |
|---|---|---|---|---|---|
| 밝은 실내 | video01 | baseline | [기입] | [기입] | |
| 밝은 실내 | video01 | fine-tune2 | [기입] | [기입] | |
| 어두움/역광 | video02 | baseline | [기입] | [기입] | |
| 어두움/역광 | video02 | fine-tune2 | [기입] | [기입] | |
| 다중 동시 통과 | video03 | baseline | [기입] | [기입] | |
| 다중 동시 통과 | video03 | fine-tune2 | [기입] | [기입] | |

---

## 6. 오차 원인 분석

> [측정 완료 후 기입]

추정 원인 후보:
- 검출 누락 (Recall 부족)
- 검출 오류 (Precision 부족)
- DeepSORT ID 분기 (한 사람 → 여러 카운트)
- DeepSORT ID 결합 (여러 사람 → 한 카운트)
- 라인 좌표 부적합 (`--in-line`, `--board-line`)
- 카메라 각도/높이/FOV
- 조명 조건

---

## 7. 개선 방안

> [측정 완료 후 기입]

---

## 8. 결론

> [측정 완료 후 기입]

평균 mAP50 (self_v1 val): [기입]
평균 IN 오차율 (eval_videos): [기입] %
목표 달성 여부: [기입]

**목표 기준 (수정안 2026-05-16):**
- Detection mAP50 ≥ 0.50 (baseline 대비 +0.05 이상)
- Counting IN 오차율 ≤ 15%, BOARD 오차율 ≤ 20%
- Runtime FPS ≥ 25 (Jetson 배포)

---

## 9. 변경 이력

| 버전 | 날짜 | 변경 사항 | 작성자 |
|---|---|---|---|
| v1.0 | [최초] | 실시간 AI vs 수동 카운팅 비교 템플릿 | 박건우 |
| v2.0 | 2026-05-16 | 수동 실시간 카운팅 제외, 데이터 기반 평가로 전환. Detection/Counting/Runtime 3축 재구성. spec 근거 추가. | 류훈민 |
