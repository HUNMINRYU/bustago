# YOLO11 데이터 학습/평가 트랙 설계 — 2026-05-16

> 상태: 설계 확정 (사용자 승인 대기)
> 작성: 2026-05-16
> 작성자: 류훈민
> 근거: `docs/회의내용_프로젝트_반영방안_2026-05-14.md`, `프로젝트_종합진단_2026-05-16.md`, 2026-05-16 브레인스토밍 세션
> 마일스톤: 5/21 1차 시연 + 6/4 경진대회

---

## 1. 컨텍스트

BUSTAGO 시스템의 AI 카운팅(YOLO11 + DeepSORT + Line Crossing) 트랙은 다음 상태다.

- `hardware/counter.py` (13147B) — YOLO11 + DeepSORT 추론 파이프라인 완성, 2026-05-16 Jetson Orin Nano에서 35 FPS standalone / 8.2 FPS debug 검증
- `hardware/train_yolo.py` — 학습 entrypoint 존재하나 데이터셋 0건, 평가 0건
- `hardware/configs/bustago_person.yaml` — 데이터셋 yaml 스켈레톤 존재
- 5/14 회의에서 "YOLO 학습/평가 산출물 부족"이 P0 지목
- 5/16 결정: 박건우의 실시간 수동 카운팅을 평가에 사용하지 않고, **데이터 기반 평가**로 전환

본 문서는 5/21 시연과 6/4 경진대회에 들어갈 학습/평가 산출물의 설계를 확정한다.

## 2. 목표

| 마일스톤 | 결과물 |
|---|---|
| 2026-05-21 (1차 시연) | baseline `yolo11n.pt`의 공개 데이터 기준 Detection 수치 1세트, 시연 통과, 동의받은 시연 영상 raw 확보 |
| 2026-06-04 (경진대회) | baseline / fine-tune1 / fine-tune2 비교표 (Detection mAP + Counting 오차율 + Runtime), 환경별 성능 분석, 발표용 표 |

## 3. 핵심 결정 사항

브레인스토밍 Q1~Q5의 답변과 접근 B 채택을 통해 다음을 확정한다.

| 항목 | 결정 |
|---|---|
| 마일스톤 | 5/21 시연 + 6/4 대회 둘 다 충족 |
| 데이터 소스 | 공개 데이터셋(baseline 평가용) + 광주대 자체촬영(fine-tune용) |
| 학습 환경 | 로컬 RTX 3080 우선, Colab(T4) fallback |
| 라벨링 방식 | `yolo11x` auto-label + 사람 검수 |
| 평가 축 | Detection mAP/Precision/Recall **+** Counting 영상 사후 라벨 기반 IN/BOARD 오차율 |
| 타임라인 접근 | 접근 B — 시연을 데이터 수집 기회로 활용 |
| 사전모델·배포 통일 | `yolo11n` (Jetson 8GB 안전, `counter.py` 기본값과 일치) |

## 4. 아키텍처

```
[5/16~5/20] baseline 트랙
  공개 데이터셋(Roboflow Pedestrian 1택) → val split → yolo11n.pt 평가
                                                  ↓
                                  mAP50/Precision/Recall 1세트 → 리포트 §4.1 baseline 행

[5/21] 시연 (baseline 사용) + 동의받은 시연 영상 녹화

[5/22~5/24] 자체 데이터 가공
  시연 영상 → 프레임 샘플링 → yolo11x auto-label → 사람 검수 → train/val 8:2 split

[5/25~5/29] fine-tune 1차
  yolo11n.pt + self_v1 train → best.pt → self_v1 val 평가 → 리포트 §4.1 fine-tune1 행

[5/30~6/1] 증강 fine-tune 2차
  + Ultralytics 기본 증강 hyperparam → best.pt → val 재평가 → 리포트 §4.1 fine-tune2 행

[6/2~6/3] Counting 평가
  eval_videos 1~3개 → 사후 라벨 groundtruth.json → 3 모델 × N 영상 IN/BOARD 비교

[6/4] 발표용 표 + 리포트 §5~§8 작성
```

**핵심 불변식**

1. baseline용 공개 데이터셋은 5/17~5/20 사이에 1개 선택해 fix(변경 불가) — 이후 비교 일관성
2. baseline / fine-tune1 / fine-tune2 모두 **동일한 self_v1 val split**으로 평가 (공식 비교)
3. Counting 평가 영상(`eval_videos/*.mp4`)은 train/val 어디에도 포함되지 않음 (영상 단위 grouping으로 leak 방지)

## 5. 구성요소

### 5.1 디렉토리 구조

```
bustago/
├── datasets/                              # 전체 .gitignore (디렉토리만 .gitkeep로 트래킹)
│   └── bustago_person/
│       ├── README.md                      # 데이터 출처·라이선스·라벨링 규칙 (Git)
│       ├── public_baseline/{images,labels}/{train,val}/
│       ├── self_v1/
│       │   ├── raw_videos/                # 로컬 디스크 보관 (.gitignore)
│       │   ├── frames/
│       │   └── {images,labels}/{train,val}/
│       └── eval_videos/
│           ├── video01.mp4                # ignore
│           └── video01_groundtruth.json   # Git 포함
│
├── hardware/
│   ├── configs/
│   │   ├── bustago_person.yaml            # 기존 — public_baseline 경로 적용
│   │   └── bustago_person_self.yaml       # 신규 — self_v1 경로
│   ├── train_yolo.py                      # 수정 — --data, --model, --name 인자 추가
│   ├── counter.py                         # 기존 — 변경 없음
│   ├── sample_frames.py                   # 신규
│   ├── autolabel.py                       # 신규
│   └── eval_counting.py                   # 신규
│
├── runs/                                  # 전체 .gitignore
│   └── bustago/{baseline_val, self_v1_finetune, self_v1_augmented}/
│
└── docs/
    ├── 03_구축/촬영_동의_및_삭제_절차.md  # 신규 (P0)
    ├── 04_테스트/AI_카운팅_정확도_리포트_템플릿.md  # v2.0 재작성
    └── superpowers/specs/2026-05-16-yolo-data-track-design.md  # 본 문서
```

### 5.2 신규 스크립트

| 파일 | 책임 | 입력 | 출력 |
|---|---|---|---|
| `hardware/sample_frames.py` | 영상에서 n초 간격 프레임 추출 | `raw_videos/*.mp4`, `--interval 2` | `frames/*.jpg` |
| `hardware/autolabel.py` | yolo11x로 person bbox 자동 라벨 | `frames/*.jpg` | `labels/*.txt` (YOLO format) |
| `hardware/eval_counting.py` | 한 영상 × 여러 모델 IN/BOARD 비교 | `eval_videos/*.mp4`, `--models a.pt b.pt`, `--groundtruth ....json` | 비교 CSV |

### 5.3 코드 수정

#### `hardware/train_yolo.py`

```diff
 def parse_args():
     parser = argparse.ArgumentParser(description="Train YOLO11 for BUSTAGO person detection")
     parser.add_argument("--epochs", type=int, default=100)
     parser.add_argument("--imgsz", type=int, default=960)
     parser.add_argument("--batch", type=int, default=16)
     parser.add_argument("--device", default=0)
+    parser.add_argument("--data", default="hardware/configs/bustago_person.yaml")
+    parser.add_argument("--model", default="yolo11n.pt")
+    parser.add_argument("--name", default="yolo11-person")
     return parser.parse_args()

 def main():
     args = parse_args()
     from ultralytics import YOLO
-    model = YOLO("yolo11s.pt")
+    model = YOLO(args.model)
     model.train(
-        data="hardware/configs/bustago_person.yaml",
+        data=args.data,
         ...
         project="runs/bustago",
-        name="yolo11-person",
+        name=args.name,
     )
```

#### `.gitignore`

```diff
 *.pt
 *.pth
+*.engine
+*.onnx

+# YOLO 학습/평가 산출물
+datasets/
+runs/
```

`datasets/.gitkeep`, `runs/.gitkeep`로 디렉토리 구조만 트래킹.

## 6. 단계별 실행 명세

### Phase 0 (5/16) — 인프라 + 정책

| Step | 산출 | 검증 |
|---|---|---|
| 0-1 | `docs/03_구축/촬영_동의_및_삭제_절차.md` 신규 | 안내문·거부·삭제절차·보관기간·비식별·책임자 7개 포함 |
| 0-2 | 리포트 템플릿 v2.0 | 수동 실시간 카운팅 행 0개, Detection/Counting/Runtime 3축 |
| 0-3 | `train_yolo.py`, `.gitignore` 수정 | git diff 검토 |
| 0-4 | `datasets/.gitkeep`, `runs/.gitkeep` | 디렉토리 존재, 내용물은 ignore |

### Phase 1 (5/17~5/20) — baseline + 시연 준비

| Step | 산출 |
|---|---|
| 1-1 | 공개 데이터셋 후보 3개 비교 → 1개 선택, URL/라이선스 기록 |
| 1-2 | `public_baseline/{images,labels}/{train,val}/` (val ≥ 500장) |
| 1-3 | `runs/bustago/baseline_val/` (yolo val 결과) |
| 1-4 | 리포트 §4.1 baseline 행 채움 |
| 1-5 | `sample_frames.py`, `autolabel.py` 신규 + dry-run 통과 |
| 1-6 | 시연 안내문 A4 출력본 |

### Phase 2 (5/21 시연 당일)

| Step | 산출 |
|---|---|
| 2-1 | 시연 통과 + 디버그 영상 |
| 2-2 | 동의 시간대 raw mp4 (`datasets/bustago_person/self_v1/raw_videos/`, 30분~1시간) |
| 2-3 | raw 영상 이중 백업 (Jetson SSD + 류훈민 PC) |

### Phase 3 (5/22~5/24) — 자체 데이터 가공

| Step | 산출 | 검증 |
|---|---|---|
| 3-1 | `frames/*.jpg` (2초 간격) | 매수 ≥ 600 |
| 3-2 | `labels/*.txt` (auto-label) | 매수 = frames와 1:1 |
| 3-3 | 검수된 라벨 | 검수율 100% |
| 3-4 | `self_v1/images/{train,val}` (8:2 split, 영상 단위 grouping) | val ≥ 100, eval_videos는 분리 보관 |
| 3-5 | `bustago_person_self.yaml` 신규 | yolo val로 yaml 로딩 테스트 통과 |

### Phase 4 (5/25~5/29) — fine-tune 1차

| Step | 산출 |
|---|---|
| 4-1 | 학습 실행 (RTX 3080 또는 Colab) |
| 4-2 | `runs/bustago/self_v1_finetune/weights/best.pt` |
| 4-3 | self_v1 val 평가 결과 → 리포트 §4.1 fine-tune1 행 |

### Phase 5 (5/30~6/1) — 증강 fine-tune 2차

| Step | 산출 |
|---|---|
| 5-1 | `runs/bustago/self_v1_augmented/weights/best.pt` (flip, HSV, mosaic 증강 hyperparam) |
| 5-2 | self_v1 val 재평가 → 리포트 §4.1 fine-tune2 행 |

### Phase 6 (6/2~6/3) — Counting 평가

| Step | 산출 |
|---|---|
| 6-1 | `eval_videos/*_groundtruth.json` ×1~3 (사후 라벨, train/val에 없는 영상) |
| 6-2 | `eval_counting.py` 출력 CSV (3 모델 × N 영상) |
| 6-3 | 리포트 §4.2 Counting 비교표 |
| 6-4 | 리포트 §4.3 Runtime (baseline 28ms/35FPS는 이미 측정, fine-tune 추가) |

### Phase 7 (6/4)

| Step | 산출 |
|---|---|
| 7-1 | 리포트 §5(환경별), §6(원인분석), §7(개선방안), §8(결론) 작성 |
| 7-2 | 발표 자료에 §4.1/§4.2 표 삽입 |
| 7-3 | (선택) TensorRT export → `*.engine` 배포 |

## 7. 평가 방법론

### 7.1 Detection 평가

- 도구: Ultralytics `yolo val`
- 메트릭: Precision, Recall, mAP50 (주 지표), mAP50-95 (부 지표)
- 비교 일관성: baseline / fine-tune1 / fine-tune2 **모두 self_v1 val로 평가**
- baseline은 추가로 public val에도 평가하여 도메인 일반화 참조값 확보 (부록)

명령 예시:
```bash
yolo val model=yolo11n.pt data=hardware/configs/bustago_person_self.yaml
yolo val model=runs/bustago/self_v1_finetune/weights/best.pt data=hardware/configs/bustago_person_self.yaml
```

### 7.2 Counting 평가 (영상 사후 라벨)

**원칙**: 영상을 일시정지·되감기 가능한 상태에서 사람이 라인 통과 인스턴스 식별 → 5/14 회의 "수동 실시간 카운팅"과 구별되는 결정론적·재현 가능 평가.

`<영상>_groundtruth.json` 스키마:
```json
{
  "video": "video01.mp4",
  "duration_sec": 600,
  "camera_position": "INS01_north_2.2m_45deg",
  "lighting": "낮_실내_밝음",
  "in_line": [[100, 350], [540, 350]],
  "board_line": [[100, 200], [540, 200]],
  "ground_truth": {
    "count_in": 47,
    "count_board": 33,
    "crossings_in":  [{"timestamp_sec": 12.3, "person_id": "GT01", "direction": "in"}],
    "crossings_board": []
  },
  "labeled_by": "류훈민",
  "labeled_at": "2026-06-02"
}
```

합계(`count_in`, `count_board`)만으로 오차율 산출 가능. `crossings_*` 배열은 디버깅용으로 시간 부족 시 비워도 평가 진행.

오차율:
```
IN 오차율 (%) = |AI_count_in - GT_count_in| / GT_count_in × 100
BOARD 오차율 (%) = |AI_count_board - GT_count_board| / GT_count_board × 100
```

### 7.3 Runtime 평가

| 항목 | 방법 |
|---|---|
| 추론 latency (ms/frame) | `counter.py --debug` 콘솔 출력 |
| FPS | 1000 / latency 또는 counter.py debug FPS |
| End-to-end latency (선택) | 프레임 캡처 시각 → POST 응답 시각 차이 |

baseline은 2026-05-16에 이미 측정됨(28ms / 35 FPS standalone). fine-tune은 Phase 6에서 Jetson에 weight 이식 후 측정.

### 7.4 환경별 분석

`eval_videos/`를 환경 조건별로 1개씩 확보:

| 영상 | 조건 | 관찰 목표 |
|---|---|---|
| video01 | 밝은 실내, 1~2명 통과 | baseline 기본 성능 |
| video02 | 역광 또는 어두운 시간 | fine-tune이 baseline을 가장 크게 이기는 조건 |
| video03 | 2명 이상 동시 통과 | DeepSORT track ID 분기 관찰 |

### 7.5 목표 기준

- Detection mAP50 ≥ 0.50 (fine-tune이 baseline 대비 +0.05 이상)
- Counting IN 오차율 ≤ 15%, BOARD 오차율 ≤ 20%
- Runtime FPS ≥ 25 (Jetson 배포 기준)

## 8. 리스크 + 폴백

| ID | 리스크 | 감지 기준 | 폴백 |
|---|---|---|---|
| R1 | 자체 데이터 수집 부족 | 5/22 동의 시간대 ≤ 15분 또는 통과 ≤ 30건 | 추가 촬영 → 팀원 시뮬레이션 |
| R2 | 라벨링 지연 | 5/23 EOD 검수율 < 50% | 검수 스킵·val만 검수·매수 축소 |
| R3 | fine-tune ≤ baseline | mAP50(ft1) < mAP50(baseline) - 0.02 | hyperparam 조정 → 데이터 추가 → baseline 채택 + 원인 분석 |
| R4 | RTX 3080 학습 불가 | 30분 안에 학습 시작 못함 | Colab 즉시 전환 (사전 노트북 준비) |
| R5 | Counting 평가 영상 부재 | raw 길이 합 ≤ 30분 | 시연 외 추가 촬영 1회 (5/22~5/24 일정 압축). 같은 영상을 train+eval로 쪼개는 폴백은 §4 불변식 3(영상 단위 grouping) 위반이므로 금지 |
| R6 | TensorRT export 실패 | `yolo export` 에러 | `.pt` 그대로 Jetson 추론 (35 FPS 검증됨) |
| R7a | 동의 거부자 영상 포함 | 거부 발생 | 시간대 영상 폐기 또는 얼굴 마스킹 |
| R7b | 라벨링 단계 식별 누락 | 학습 데이터 비식별 미흡 | 학습용만, 발표 자료는 bbox만 |
| R8 | 일정 압박 | 5/27 EOD Phase 4 미완료 | Phase 5 스킵 → Phase 6-4 스킵 → R3 폴백으로 6/3 마감 |

폴백 발동 권한: 류훈민 자체 판단 (R2, R4, R6, R8) / 팀 협의 (R1, R3, R5, R7).

## 9. Git 추적 매트릭스

| 자산 | Git | 위치 |
|---|---|---|
| 신규 스크립트, 수정 코드, 신규/수정 문서 | ✅ | 원위치 |
| `datasets/.gitkeep`, `runs/.gitkeep` | ✅ | 디렉토리 보존 |
| `datasets/bustago_person/README.md` | ✅ | 데이터 메타 |
| `eval_videos/*_groundtruth.json` | ✅ | 라벨 자산 |
| `datasets/bustago_person/**/{images,labels}/`, `raw_videos/*.mp4` | ❌ | 로컬 디스크 (.gitignore) |
| `runs/**`, `*.pt`, `*.engine`, `*.onnx` | ❌ | 학습 머신 로컬 (선택적으로 외장 디스크 백업) |

## 10. 로컬 보관 구조 (Git 외)

데이터는 프로젝트 디렉토리 내부에 두되 `.gitignore`로 커밋 제외. 외장 SSD는 필수 아님 —
디스크 여유가 충분하면 내장 디스크만으로 진행 가능.

```
<프로젝트 루트>/datasets/bustago_person/
├── public_baseline/        # CrowdHuman 등 공개 데이터 (1.3GB)
├── self_v1/
│   └── raw_videos/2026-05-21_demo_INS01.mp4
└── eval_videos/video01.mp4

<프로젝트 루트>/runs/bustago/  # ultralytics 학습/평가 산출물
~/bustago_backup/raw_videos/   # 선택: 2차 백업 (record_demo.sh 자동 rsync)
```

**SSD를 쓰고 싶을 때**: `record_demo.sh --output /media/.../file.mp4`로 출력 경로만 바꾸면 됨.
`hardware/configs/bustago_person.yaml`의 `path:`도 절대경로로 바꾸거나 심볼릭 링크 사용.

폐기 시점: 2026-12-31 (촬영_동의_및_삭제_절차.md §6과 일치).

## 11. 발표 자료 매핑

| 슬라이드 | 본 문서 산출물 |
|---|---|
| AI 카운팅 정확도 | 리포트 §4.1 mAP 비교표 |
| 환경별 성능 | 리포트 §5 표 |
| 실시간성 | 리포트 §4.3 FPS/latency |
| 개인정보 처리 | 촬영_동의_및_삭제_절차.md 핵심 5줄 |
| 향후 계획 | TensorRT export, 데이터 확장 |

## 12. 범위 외 (Out of Scope)

- 박건우 실시간 수동 카운팅 (2026-05-16 결정으로 제외)
- LightGBM 학습 (혼잡도 예측 ML — 별도 트랙)
- MQTT 전환 (회의 §4.4 — 발표 후 확장안)
- 광주 BIS 데이터 확장 (별도 백엔드 트랙)

## 13. 사전 조건

- RTX 3080 PC의 CUDA/PyTorch 환경 (Phase 4 전까지 검증)
- 디스크 여유 ≥ 10GB (raw 영상 + 데이터셋 + 모델). 부족 시 외장 디스크 별도 마련.
- 시연 안내문 부착 권한 (광주대 인성관 정류장 INS01)
- Roboflow 또는 LabelImg 계정 (Phase 3-3 라벨 검수용)

## 14. 검증 기준 (본 spec의 성공)

본 spec은 다음을 만족하면 성공:

1. 6/4 발표에 §4.1 비교표 3행 + §4.2 Counting 표가 실측치로 채워짐
2. 발표 Q&A에서 "수동 카운팅과 비교했나"에 "데이터 기반 평가로 전환했고, 그 이유는 ___" 답변 가능
3. 개인정보 질문에 촬영_동의_및_삭제_절차.md 1쪽으로 답변 가능
4. fine-tune이 baseline보다 나쁘더라도 (R3) 원인 분석이 리포트에 있어서 발표 신뢰도 유지

## 15. 변경 이력

| 버전 | 날짜 | 변경 사항 | 작성자 |
|---|---|---|---|
| v1.0 | 2026-05-16 | 초안 작성 — 브레인스토밍 Q1~Q5 + 접근 B 채택 결과 반영 | 류훈민 |
