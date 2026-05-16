# YOLO11 데이터 학습/평가 트랙 실행 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2026-05-21 1차 시연용 baseline 수치와 2026-06-04 경진대회용 fine-tune 비교 산출물을 데이터 기반(수동 실시간 카운팅 제외)으로 확보.

**Architecture:** 8 Phase 순차 진행. Phase 0~1은 코드/문서 인프라(오늘~5/20). Phase 2(5/21)는 시연 + 데이터 수집. Phase 3~7은 가공·학습·평가. baseline / fine-tune1 / fine-tune2 세 모델을 동일 self_v1 val로 평가하고, 별도 eval_videos로 Counting 오차율 측정.

**Tech Stack:** Python 3.10, Ultralytics YOLO11, PyTorch 2.5, OpenCV, DeepSORT, pytest. 학습 환경: 로컬 RTX 3080 또는 Google Colab (T4). 배포: Jetson Orin Nano (JP 6.2, nv24.08 PyTorch).

**근거 spec:** `docs/superpowers/specs/2026-05-16-yolo-data-track-design.md`

---

## 파일 변경 맵

**신규 코드 (3개)**
- `hardware/sample_frames.py` — mp4 → jpg 프레임 샘플러
- `hardware/autolabel.py` — yolo11x로 person bbox 자동 라벨
- `hardware/eval_counting.py` — 영상 1개 × 여러 모델로 IN/BOARD 비교

**신규 테스트 (3개)**
- `hardware/tests/test_sample_frames.py`
- `hardware/tests/test_autolabel.py`
- `hardware/tests/test_eval_counting.py`

**신규 config (1개)**
- `hardware/configs/bustago_person_self.yaml` — self_v1 데이터셋용

**신규 문서 (3개)**
- `docs/03_구축/촬영_동의_및_삭제_절차.md` — P0 #6
- `datasets/bustago_person/README.md` — 데이터셋 메타
- (Phase 6) `datasets/bustago_person/eval_videos/*_groundtruth.json`

**수정 코드 (2개)**
- `hardware/train_yolo.py` — `--data`, `--model`, `--name` 인자 추가 + `yolo11s` → `yolo11n` 기본값
- `.gitignore` — `datasets/`, `runs/`, `*.engine`, `*.onnx` 추가

**수정 문서 (1개)**
- `docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md` — v2.0 재작성

**신규 디렉토리 보존용 빈 파일 (2개)**
- `datasets/.gitkeep`
- `runs/.gitkeep`

---

# Phase 0 — 오늘(2026-05-16) 인프라 + 정책

## Task 0.1: 촬영 동의 및 삭제 절차 문서 작성

**Files:**
- Create: `docs/03_구축/촬영_동의_및_삭제_절차.md`

- [ ] **Step 1: 문서 신규 작성**

파일 전체 내용:

````markdown
# 촬영 동의 및 삭제 절차

> 버전: v1.0
> 작성일: 2026-05-16
> 적용 대상: BUSTAGO 카메라 카운팅 시스템 (광주대 인성관 정류장 INS01)
> 책임자: 류훈민 (팀장)
> 근거: 2026-05-14 회의 결정 (개인정보 처리 절차 P0)

---

## 1. 적용 범위

BUSTAGO 카메라(Pi Camera v2 또는 USB 웹캠)가 촬영하는 정류장 영상의 동의·거부·삭제·비식별 처리 절차를 규정한다.

대상:
- 광주대 인성관 정류장 INS01에 설치된 Jetson + 카메라
- 시연 기간 중 촬영되는 모든 영상
- 학습 데이터 후보로 사용되는 영상 프레임

## 2. 촬영 목적

| 목적 | 사용 방식 |
|---|---|
| 실시간 카운팅 | 사람을 person 클래스로 탐지 후 라인 통과만 카운트. 영상 자체는 디스크 저장하지 않음 |
| 모델 학습 데이터 | 별도 동의를 받은 시간대의 영상에 한해 프레임을 저장하고 비식별 처리 후 학습 데이터로 사용 |
| 시연 발표 자료 | 비식별 처리(얼굴 모자이크/마스킹) 후 패널/슬라이드에 사용 |

영상 원본은 다음 경우에만 디스크에 저장된다:
- "학습 데이터 수집 동의"가 명시된 시간대
- 디버그 로그 캡처가 필요할 때 (담당자 수동 트리거, 사용 후 즉시 삭제)

## 3. 안내문 (정류장 부착)

```
[BUSTAGO 카메라 카운팅 시연 안내]

본 정류장에는 광주대학교 캡스톤 졸업작품 BUSTAGO의
실시간 인원 카운팅 카메라가 설치되어 있습니다.

- 촬영 범위: 정류장 진입 라인 부근
- 카운팅 방식: 사람의 라인 통과만 숫자로 기록
- 영상 저장: 실시간 처리 후 폐기 (기본)
- 학습 데이터 수집 시간: 별도 표시
- 거부 의사 표명: 카메라 시야를 피해 이동하거나 담당자에게 알려주세요

촬영 동의 거부, 삭제 요청 연락처:
- 책임자: 류훈민 (010-XXXX-XXXX, [이메일])
- 처리 시한: 요청 접수 후 48시간 이내 처리
```

> 책임자 연락처는 시연 직전 실제 값으로 교체. 본 문서에는 마스킹된 형태로 유지.

## 4. 거부자 처리

- 안내문을 본 후 시야를 피해 이동한 사람의 영상은 별도 처리 필요 없음 (카운팅만 발생, 원본 미저장)
- 학습 데이터 수집 시간대(별도 표시)에 카메라 시야 안에 진입한 시점은 동의로 간주 (안내문에 명시)
- 명시적 거부 의사를 표명한 사람은 그 시간대 촬영분 전체에서 해당 사람이 포함된 프레임을 삭제하거나 얼굴 영역 마스킹

## 5. 삭제 요청 처리

| 단계 | 내용 | 시한 |
|---|---|---|
| 1. 접수 | 책임자 연락처로 요청 (전화/이메일/대면) | 즉시 |
| 2. 영상 검색 | 요청 일시·정류장·인상착의 기준으로 저장 영상 검색 | 24시간 이내 |
| 3. 삭제 | 해당 프레임 삭제 또는 얼굴 영역 마스킹 | 48시간 이내 |
| 4. 확인 회신 | 요청자에게 처리 완료 통보 | 48시간 이내 |

학습 데이터셋에 이미 포함된 경우:
- 해당 프레임을 데이터셋에서 제거
- 다음 학습 시점에 모델 재학습 또는 영향도 평가
- 이미 학습된 모델은 즉시 삭제하지 않으나 다음 정기 재학습 시 반영

## 6. 보관 기간

| 데이터 종류 | 보관 기간 | 보관 위치 |
|---|---|---|
| 카운팅 숫자 (count_in, count_board) | 무기한 (개인정보 미포함) | DB |
| 디버그 로그 영상 | 분석 종료 후 즉시 삭제 (최대 7일) | Jetson 로컬 SSD |
| 학습 데이터 (동의 받은 프레임) | 졸업작품 평가 종료 (2026-12-31) 후 삭제 | 외장 SSD (BUSTAGO_DATA) |
| 시연 발표 자료 (비식별 처리됨) | 졸업작품 포트폴리오 보존 기간 | 팀 공유 드라이브 |

## 7. 비식별 처리 기준 (발표/패널 자료)

- 얼굴이 식별 가능한 프레임은 발표 자료에 사용 금지
- 사용 시 다음 중 하나 적용:
  - 얼굴 영역 모자이크 (16x16 픽셀 이상)
  - 가우시안 블러 (커널 사이즈 21 이상)
  - 검은 박스 마스킹
- bbox만 보이는 검출 결과 화면(원본 영상 없음)은 비식별 처리 면제
- 팀원 본인 얼굴은 본인 동의 하에 원본 사용 가능

## 8. 책임 분담

| 역할 | 담당 |
|---|---|
| 전체 책임 | 류훈민 (팀장) |
| 시연 현장 안내문 게시 | 박건우 |
| 삭제 요청 접수 및 처리 | 류훈민 |
| 학습 데이터 비식별 처리 | 류훈민, 이건영 |
| 발표 자료 비식별 처리 확인 | 박건우 |

## 9. 참고

- 본 문서는 졸업작품 시연 환경 기준이며, 상용 서비스 전환 시 개인정보보호법 적용 범위에서 별도 검토 필요
- 광주대 측 안내사항이 있을 경우 우선 적용
- 회의 근거: `docs/회의내용정리_2026-05-14.md`, `docs/회의내용_프로젝트_반영방안_2026-05-14.md` §4.3, §5.1

## 10. 변경 이력

| 버전 | 날짜 | 변경 사항 | 작성자 |
|---|---|---|---|
| v1.0 | 2026-05-16 | 최초 작성 (5/14 회의 P0 #6 반영) | 류훈민 |
````

- [ ] **Step 2: 파일 존재 확인**

Run: `ls -la docs/03_구축/촬영_동의_및_삭제_절차.md`
Expected: 파일 존재, 0바이트 아님

- [ ] **Step 3: 항목 점검**

Run: `grep -c "^## " docs/03_구축/촬영_동의_및_삭제_절차.md`
Expected: `10` (10개 섹션)

---

## Task 0.2: 정확도 리포트 템플릿 v2.0 재작성

**Files:**
- Modify: `docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md` (전면 재작성)

- [ ] **Step 1: 파일 전체를 다음 내용으로 덮어쓰기**

````markdown
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
````

- [ ] **Step 2: 검증**

Run: `grep -c "수동 IN\|수동 BOARD\|수동 카운팅" docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md`
Expected: `0` (단, "실시간 수동 카운팅을 사용하지 않고"라는 부정 문장 1건은 의도된 잔존 — 결과 1 미만이면 OK)

실제 grep 결과:
```bash
grep -n "수동" docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
```
나오는 라인이 모두 "수동 ___을 사용하지 않는다" 류이면 OK. "AI vs 수동" 비교 컬럼이 남아있으면 NG.

---

## Task 0.3: train_yolo.py 인자 추가

**Files:**
- Modify: `hardware/train_yolo.py`

- [ ] **Step 1: 파일을 다음 내용으로 덮어쓰기**

```python
"""YOLO11 Stage 1 training entrypoint for BUSTAGO person detection."""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO11 for BUSTAGO person detection")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=960, help="Training image size (default: 960)")
    parser.add_argument("--batch", type=int, default=16, help="Training batch size (default: 16)")
    parser.add_argument("--device", default=0, help="Training device, e.g. 0, cpu, or 0,1 (default: 0)")
    parser.add_argument("--data", default="hardware/configs/bustago_person.yaml",
                        help="Dataset YAML path (default: public baseline config)")
    parser.add_argument("--model", default="yolo11n.pt",
                        help="Pretrained model file. yolo11n.pt 권장 (counter.py 배포와 일치)")
    parser.add_argument("--name", default="yolo11-person",
                        help="Run name written under runs/bustago/")
    return parser.parse_args()


def main():
    args = parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        pretrained=True,
        cos_lr=True,
        close_mosaic=10,
        project="runs/bustago",
        name=args.name,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 인자 파싱 동작 확인 (ultralytics 미설치 환경에서도 OK)**

Run: `python3 hardware/train_yolo.py --help`
Expected: `--data`, `--model`, `--name` 옵션이 출력되고 종료 코드 0.

---

## Task 0.4: .gitignore 보강

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 파일 끝에 다음 라인 추가**

기존 `.gitignore`의 마지막 라인(`=*` 또는 마지막 비주석 라인) 뒤에 추가:

```
*.engine
*.onnx

# YOLO 학습/평가 산출물
datasets/
runs/
```

- [ ] **Step 2: 검증**

Run: `grep -E "^datasets/$|^runs/$|^\*\.engine$|^\*\.onnx$" .gitignore | wc -l`
Expected: `4`

---

## Task 0.5: 디렉토리 보존용 .gitkeep 생성

**Files:**
- Create: `datasets/.gitkeep`
- Create: `runs/.gitkeep`

- [ ] **Step 1: 빈 파일 생성**

Run: `mkdir -p datasets runs && touch datasets/.gitkeep runs/.gitkeep`

- [ ] **Step 2: 검증**

Run: `ls datasets/.gitkeep runs/.gitkeep`
Expected: 두 파일 모두 존재

Run: `git check-ignore -v datasets/.gitkeep runs/.gitkeep`
Expected: ignore 안 됨 (출력 없음)

---

## Task 0.6: datasets/bustago_person/README.md 신규

**Files:**
- Create: `datasets/bustago_person/README.md`

- [ ] **Step 1: 파일 생성**

```bash
mkdir -p datasets/bustago_person
```

내용:

````markdown
# BUSTAGO Person Detection Dataset

> 최종 갱신: 2026-05-16
> 관리자: 류훈민
> 근거 spec: `docs/superpowers/specs/2026-05-16-yolo-data-track-design.md`

## 구조

```
bustago_person/
├── public_baseline/      # Phase 1: 공개 데이터셋 (baseline 평가용)
│   ├── images/{train,val}/
│   └── labels/{train,val}/
├── self_v1/              # Phase 3: 광주대 자체촬영 (fine-tune용)
│   ├── raw_videos/       # 외장 SSD 보관, Git X
│   ├── frames/
│   ├── images/{train,val}/
│   └── labels/{train,val}/
└── eval_videos/          # Phase 6: Counting 평가 전용
    ├── *.mp4             # Git X
    └── *_groundtruth.json  # Git ✓
```

## 출처

| 항목 | 출처 | 라이선스 | 사용 시기 |
|---|---|---|---|
| public_baseline | [Phase 1-1에서 채움] | [채움] | 2026-05-17~5/20 |
| self_v1 | 광주대 인성관 정류장 INS01 자체촬영 | 본 캡스톤 내부 사용, 2026-12-31 폐기 | 2026-05-21~ |
| eval_videos | 동일 (별도 영상) | 동일 | 2026-06-02~ |

## 라벨링 규칙

- 클래스: `person` (id=0) — 단일 클래스
- bbox: 사람 전신 박스. 잘린 부분은 보이는 영역만.
- 최소 크기: 짧은 변 ≥ 20 픽셀. 그 이하는 학습에 노이즈이므로 제외.
- 가려짐: 60% 이상 가려진 사람은 라벨 안 함.
- 형식: Ultralytics YOLO (txt 1개 = 1장, 행당 `cls cx cy w h`, 좌표는 0~1 정규화).

## 트래킹 정책

- `**/*.{jpg,png,mp4}`: Git ignore (외장 SSD `/media/<USER>/BUSTAGO_DATA/`)
- `**/*_groundtruth.json`: Git 트래킹 (라벨 자산)
- 본 README: Git 트래킹

## 개인정보

자체촬영분은 `docs/03_구축/촬영_동의_및_삭제_절차.md` 적용. 발표 자료 사용 시 비식별 처리 필수.
````

- [ ] **Step 2: 검증**

Run: `ls datasets/bustago_person/README.md`
Expected: 파일 존재

---

## Task 0.7: Phase 0 커밋

- [ ] **Step 1: 변경사항 확인**

```bash
git status --short
git diff --stat
```

예상 변경:
- A docs/03_구축/촬영_동의_및_삭제_절차.md
- M docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
- M hardware/train_yolo.py
- M .gitignore
- A datasets/.gitkeep
- A datasets/bustago_person/README.md
- A runs/.gitkeep

- [ ] **Step 2: 커밋**

```bash
git add docs/03_구축/촬영_동의_및_삭제_절차.md \
        docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md \
        hardware/train_yolo.py \
        .gitignore \
        datasets/.gitkeep \
        datasets/bustago_person/README.md \
        runs/.gitkeep

git commit -m "$(cat <<'EOF'
feat(yolo-data): Phase 0 인프라 + 정책 (촬영동의·리포트v2·train인자·gitignore)

데이터 트랙 spec 2026-05-16 Phase 0 산출물:
- docs/03_구축/촬영_동의_및_삭제_절차.md 신규 (P0 #6)
- docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md v2.0 재작성
  (수동 실시간 카운팅 행 제거, Detection/Counting/Runtime 3축)
- hardware/train_yolo.py --data/--model/--name 인자 추가,
  사전모델 yolo11s → yolo11n으로 변경 (counter.py 배포와 일치)
- .gitignore에 datasets/, runs/, *.engine, *.onnx 추가
- datasets/bustago_person/README.md 신규 (데이터 메타정보)
EOF
)"
```

- [ ] **Step 3: 커밋 확인**

Run: `git log -1 --stat`
Expected: 위 7개 파일 변경 + 커밋 메시지

---

# Phase 1 — baseline 평가 + 시연 준비 (5/17~5/20)

## Task 1.1: sample_frames.py 작성 (TDD)

**Files:**
- Create: `hardware/sample_frames.py`
- Test: `hardware/tests/test_sample_frames.py`

- [ ] **Step 1: 테스트 디렉토리 준비**

Run: `mkdir -p hardware/tests && touch hardware/tests/__init__.py`

- [ ] **Step 2: 실패하는 테스트 작성**

`hardware/tests/test_sample_frames.py`:

```python
"""sample_frames.py 테스트."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
import pytest

from sample_frames import extract_frames


def _make_video(path: Path, num_frames: int = 30, fps: int = 10) -> None:
    """테스트용 합성 영상 생성 (num_frames장, 320x240)."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (320, 240))
    for i in range(num_frames):
        frame = np.full((240, 320, 3), i * 8 % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_extract_frames_every_1s(tmp_path):
    video = tmp_path / "test.mp4"
    _make_video(video, num_frames=30, fps=10)  # 3초 영상
    out_dir = tmp_path / "frames"

    count = extract_frames(video, out_dir, interval_sec=1.0)

    # 3초 영상에서 1초 간격 → 3장 (t=0, 1, 2)
    assert count == 3
    files = sorted(out_dir.glob("*.jpg"))
    assert len(files) == 3


def test_extract_frames_every_05s(tmp_path):
    video = tmp_path / "test.mp4"
    _make_video(video, num_frames=20, fps=10)  # 2초 영상
    out_dir = tmp_path / "frames"

    count = extract_frames(video, out_dir, interval_sec=0.5)

    # 2초 영상에서 0.5초 간격 → 4장 (t=0, 0.5, 1.0, 1.5)
    assert count == 4


def test_extract_frames_filename_pattern(tmp_path):
    video = tmp_path / "demo.mp4"
    _make_video(video, num_frames=10, fps=10)
    out_dir = tmp_path / "frames"

    extract_frames(video, out_dir, interval_sec=1.0)

    files = sorted(out_dir.glob("*.jpg"))
    # 파일명: <video_stem>_<frame_idx>.jpg
    assert files[0].name == "demo_000000.jpg"


def test_extract_frames_creates_outdir(tmp_path):
    video = tmp_path / "x.mp4"
    _make_video(video, num_frames=5, fps=5)
    out_dir = tmp_path / "new" / "dir"
    assert not out_dir.exists()

    extract_frames(video, out_dir, interval_sec=0.2)

    assert out_dir.exists()
    assert any(out_dir.glob("*.jpg"))
```

- [ ] **Step 3: 테스트 실행해서 실패 확인**

Run: `cd /home/ahble/projects/Capstone/bustago && python3 -m pytest hardware/tests/test_sample_frames.py -v`
Expected: 모든 테스트 FAIL (ModuleNotFoundError: sample_frames)

- [ ] **Step 4: 최소 구현 작성**

`hardware/sample_frames.py`:

```python
"""영상에서 일정 간격으로 프레임을 추출해 jpg로 저장."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def extract_frames(video_path: Path, out_dir: Path, interval_sec: float = 2.0) -> int:
    """영상에서 interval_sec 간격으로 프레임을 추출해 out_dir에 jpg로 저장.

    Args:
        video_path: 입력 mp4 경로
        out_dir: 출력 디렉토리 (없으면 생성)
        interval_sec: 프레임 추출 간격 (초)

    Returns:
        추출된 프레임 수
    """
    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        cap.release()
        raise RuntimeError(f"Invalid FPS for video: {video_path}")

    interval_frames = max(1, int(round(fps * interval_sec)))
    stem = video_path.stem

    count = 0
    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % interval_frames == 0:
            out_path = out_dir / f"{stem}_{count:06d}.jpg"
            cv2.imwrite(str(out_path), frame)
            count += 1
        frame_idx += 1

    cap.release()
    return count


def main():
    parser = argparse.ArgumentParser(description="Extract frames from mp4 at fixed interval")
    parser.add_argument("--video", required=True, help="Input mp4 path")
    parser.add_argument("--out", required=True, help="Output dir")
    parser.add_argument("--interval", type=float, default=2.0, help="Frame interval seconds")
    args = parser.parse_args()

    count = extract_frames(Path(args.video), Path(args.out), args.interval)
    print(f"Extracted {count} frames from {args.video}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python3 -m pytest hardware/tests/test_sample_frames.py -v`
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add hardware/sample_frames.py hardware/tests/__init__.py hardware/tests/test_sample_frames.py
git commit -m "feat(yolo-data): add sample_frames.py with TDD (Phase 1-5)

영상에서 interval_sec 간격으로 프레임을 jpg로 추출하는 유틸.
Phase 3-1 (자체 데이터 가공)에서 raw_videos/ → frames/로 사용.

테스트: 1s/0.5s 간격 추출, 파일명 패턴, 자동 디렉토리 생성 — 4 passed."
```

---

## Task 1.2: autolabel.py 작성 (TDD with mock)

**Files:**
- Create: `hardware/autolabel.py`
- Test: `hardware/tests/test_autolabel.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`hardware/tests/test_autolabel.py`:

```python
"""autolabel.py 테스트 (YOLO 모델은 mock)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
import pytest

from autolabel import yolo_results_to_yolo_txt, autolabel_directory


def _make_image(path: Path, width: int = 640, height: int = 480) -> None:
    img = np.full((height, width, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(path), img)


def _fake_yolo_result(boxes_xyxy, classes, scores, width=640, height=480):
    """Ultralytics YOLO predict() 반환값 모사."""
    result = MagicMock()
    result.orig_shape = (height, width)
    result.boxes = MagicMock()
    result.boxes.xyxy = MagicMock()
    result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array(boxes_xyxy, dtype=np.float32)
    result.boxes.cls = MagicMock()
    result.boxes.cls.cpu.return_value.numpy.return_value = np.array(classes, dtype=np.float32)
    result.boxes.conf = MagicMock()
    result.boxes.conf.cpu.return_value.numpy.return_value = np.array(scores, dtype=np.float32)
    return result


def test_yolo_results_to_yolo_txt_format():
    # 640x480 이미지에 person bbox (cx=320, cy=240, w=100, h=200) → 정규화 (0.5, 0.5, 0.156, 0.417)
    result = _fake_yolo_result(
        boxes_xyxy=[[270, 140, 370, 340]],
        classes=[0],  # person
        scores=[0.9],
        width=640, height=480,
    )
    lines = yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=0.25)
    assert len(lines) == 1
    parts = lines[0].split()
    assert parts[0] == "0"  # class id
    assert abs(float(parts[1]) - 0.5) < 0.01    # cx
    assert abs(float(parts[2]) - 0.5) < 0.01    # cy
    assert abs(float(parts[3]) - 100/640) < 0.01  # w
    assert abs(float(parts[4]) - 200/480) < 0.01  # h


def test_filters_by_confidence():
    result = _fake_yolo_result(
        boxes_xyxy=[[0, 0, 100, 100], [0, 0, 50, 50]],
        classes=[0, 0],
        scores=[0.9, 0.1],  # 두 번째는 conf 낮음
    )
    lines = yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=0.25)
    assert len(lines) == 1  # 첫 번째만 통과


def test_filters_by_class():
    result = _fake_yolo_result(
        boxes_xyxy=[[0, 0, 100, 100], [0, 0, 50, 50]],
        classes=[0, 1],  # person + bicycle
        scores=[0.9, 0.9],
    )
    lines = yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=0.25)
    assert len(lines) == 1


def test_empty_results():
    result = _fake_yolo_result(boxes_xyxy=[], classes=[], scores=[])
    lines = yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=0.25)
    assert lines == []


def test_autolabel_directory_writes_txt(tmp_path):
    img_dir = tmp_path / "frames"
    img_dir.mkdir()
    _make_image(img_dir / "a.jpg")
    _make_image(img_dir / "b.jpg")
    label_dir = tmp_path / "labels"

    def fake_predict(image_paths):
        return [_fake_yolo_result(boxes_xyxy=[[0, 0, 50, 50]], classes=[0], scores=[0.9]) for _ in image_paths]

    count = autolabel_directory(img_dir, label_dir, predict_fn=fake_predict, target_classes={0}, min_conf=0.25)

    assert count == 2
    assert (label_dir / "a.txt").exists()
    assert (label_dir / "b.txt").exists()
    content_a = (label_dir / "a.txt").read_text().strip()
    assert content_a.startswith("0 ")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest hardware/tests/test_autolabel.py -v`
Expected: 5 failed (ModuleNotFoundError: autolabel)

- [ ] **Step 3: 최소 구현 작성**

`hardware/autolabel.py`:

```python
"""yolo11x로 frames/ → labels/ (YOLO format txt) 자동 생성."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Iterable, List, Set


def yolo_results_to_yolo_txt(result, target_classes: Set[int], min_conf: float = 0.25) -> List[str]:
    """Ultralytics YOLO 결과 1장 → YOLO format 텍스트 라인 리스트.

    Format: "<cls> <cx> <cy> <w> <h>" with normalized coords [0,1].
    """
    boxes = result.boxes
    if boxes is None:
        return []

    xyxy = boxes.xyxy.cpu().numpy()
    classes = boxes.cls.cpu().numpy()
    scores = boxes.conf.cpu().numpy()

    if len(xyxy) == 0:
        return []

    img_h, img_w = result.orig_shape

    lines: List[str] = []
    for (x1, y1, x2, y2), cls, conf in zip(xyxy, classes, scores):
        cls_id = int(cls)
        if cls_id not in target_classes:
            continue
        if float(conf) < min_conf:
            continue
        cx = ((x1 + x2) / 2) / img_w
        cy = ((y1 + y2) / 2) / img_h
        w = (x2 - x1) / img_w
        h = (y2 - y1) / img_h
        lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def autolabel_directory(
    img_dir: Path,
    label_dir: Path,
    predict_fn: Callable[[List[Path]], Iterable],
    target_classes: Set[int],
    min_conf: float = 0.25,
) -> int:
    """img_dir의 모든 .jpg에 predict_fn을 적용하고 label_dir에 .txt 생성.

    Args:
        predict_fn: image_paths → results iterable. ultralytics YOLO instance를 closure로 받는 함수 권장.

    Returns: 처리된 이미지 수.
    """
    img_dir = Path(img_dir)
    label_dir = Path(label_dir)
    label_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(img_dir.glob("*.jpg"))
    if not image_paths:
        return 0

    results = list(predict_fn(image_paths))

    for img_path, result in zip(image_paths, results):
        lines = yolo_results_to_yolo_txt(result, target_classes, min_conf)
        out_path = label_dir / (img_path.stem + ".txt")
        out_path.write_text("\n".join(lines) + ("\n" if lines else ""))

    return len(image_paths)


def main():
    parser = argparse.ArgumentParser(description="Auto-label images with yolo11x")
    parser.add_argument("--images", required=True, help="Input image dir (jpg)")
    parser.add_argument("--labels", required=True, help="Output label dir")
    parser.add_argument("--model", default="yolo11x.pt", help="YOLO model path")
    parser.add_argument("--conf", type=float, default=0.25, help="Min confidence")
    parser.add_argument("--classes", default="0", help="Comma-separated class IDs (default: 0=person)")
    args = parser.parse_args()

    from ultralytics import YOLO
    yolo = YOLO(args.model)

    def predict_fn(image_paths):
        return yolo.predict(source=[str(p) for p in image_paths], verbose=False, conf=args.conf)

    target_classes = {int(c) for c in args.classes.split(",")}
    count = autolabel_directory(Path(args.images), Path(args.labels), predict_fn, target_classes, args.conf)
    print(f"Auto-labeled {count} images")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest hardware/tests/test_autolabel.py -v`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add hardware/autolabel.py hardware/tests/test_autolabel.py
git commit -m "feat(yolo-data): add autolabel.py with TDD (Phase 1-6)

yolo11x로 frames/ → labels/ (YOLO format txt) 자동 생성.
Phase 3-2 (auto-label)에서 사용. predict_fn 주입 가능해서
mock 기반 단위 테스트 가능.

테스트: bbox 정규화, confidence/class 필터, 빈 결과, 디렉토리 처리 — 5 passed."
```

---

## Task 1.3: eval_counting.py 작성 (TDD)

**Files:**
- Create: `hardware/eval_counting.py`
- Test: `hardware/tests/test_eval_counting.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`hardware/tests/test_eval_counting.py`:

```python
"""eval_counting.py 테스트 (모델 추론은 mock)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from eval_counting import compute_error_rate, load_groundtruth, build_comparison_row


def test_compute_error_rate_zero_error():
    assert compute_error_rate(ai=10, gt=10) == 0.0


def test_compute_error_rate_perfect_overcount():
    assert compute_error_rate(ai=12, gt=10) == 20.0


def test_compute_error_rate_undercount():
    assert compute_error_rate(ai=8, gt=10) == 20.0


def test_compute_error_rate_gt_zero():
    # GT가 0이면 정의되지 않으므로 None 반환
    assert compute_error_rate(ai=5, gt=0) is None


def test_load_groundtruth(tmp_path):
    gt_file = tmp_path / "v01_groundtruth.json"
    gt_file.write_text(json.dumps({
        "video": "v01.mp4",
        "duration_sec": 300,
        "ground_truth": {"count_in": 20, "count_board": 15}
    }))

    gt = load_groundtruth(gt_file)
    assert gt["count_in"] == 20
    assert gt["count_board"] == 15


def test_build_comparison_row():
    row = build_comparison_row(
        model_name="baseline",
        video_name="v01.mp4",
        ai_in=22, ai_board=14,
        gt_in=20, gt_board=15,
    )
    assert row["model"] == "baseline"
    assert row["video"] == "v01.mp4"
    assert row["ai_in"] == 22
    assert row["gt_in"] == 20
    assert row["in_error_pct"] == 10.0
    assert row["ai_board"] == 14
    assert row["gt_board"] == 15
    assert abs(row["board_error_pct"] - 100/15) < 0.01
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python3 -m pytest hardware/tests/test_eval_counting.py -v`
Expected: 6 failed (ModuleNotFoundError: eval_counting)

- [ ] **Step 3: 최소 구현 작성**

`hardware/eval_counting.py`:

```python
"""eval_videos/ × 여러 모델 IN/BOARD 비교 CSV 생성.

Phase 6 (Counting 평가)에서 사용.
영상 단위로 counter.py의 LineCrossingCounter 로직을 import해 재사용.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Optional


def compute_error_rate(ai: int, gt: int) -> Optional[float]:
    """|AI - GT| / GT × 100. GT=0이면 None."""
    if gt == 0:
        return None
    return abs(ai - gt) / gt * 100.0


def load_groundtruth(path: Path) -> dict:
    """*_groundtruth.json에서 ground_truth.count_in/board 추출."""
    data = json.loads(Path(path).read_text())
    gt = data["ground_truth"]
    return {
        "count_in": int(gt["count_in"]),
        "count_board": int(gt["count_board"]),
    }


def build_comparison_row(model_name: str, video_name: str,
                         ai_in: int, ai_board: int,
                         gt_in: int, gt_board: int) -> dict:
    return {
        "model": model_name,
        "video": video_name,
        "ai_in": ai_in,
        "gt_in": gt_in,
        "in_error_pct": compute_error_rate(ai_in, gt_in),
        "ai_board": ai_board,
        "gt_board": gt_board,
        "board_error_pct": compute_error_rate(ai_board, gt_board),
    }


def run_counter_on_video(video_path: Path, model_path: Path,
                          in_ratio: float = 0.7, board_ratio: float = 0.3) -> dict:
    """영상에 counter.py의 LineCrossingCounter를 적용해 IN/BOARD 카운트.

    counter.py의 핵심 로직(LineCrossingCounter)을 import해 영상 frame을 순차 처리.
    실시간 디바이스가 아닌 mp4 파일 입력이므로 카메라 캡처 부분은 건너뜀.

    Returns: {"count_in": int, "count_board": int}
    """
    import cv2
    from ultralytics import YOLO

    # counter.py에서 import (단순화: deepsort 미설치 환경에서도 동작하도록 try)
    sys_path_parent = str(Path(__file__).resolve().parent)
    import sys
    if sys_path_parent not in sys.path:
        sys.path.insert(0, sys_path_parent)
    from counter import LineCrossingCounter

    try:
        from deep_sort_realtime.deepsort_tracker import DeepSort
    except ImportError:
        raise RuntimeError("deep-sort-realtime 필요: pip install deep-sort-realtime")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    counter = LineCrossingCounter(frame_height=h, in_ratio=in_ratio, board_ratio=board_ratio)
    tracker = DeepSort(max_age=30, n_init=3, max_cosine_distance=0.3)
    yolo = YOLO(str(model_path))

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        results = yolo.predict(source=frame, classes=[0], verbose=False)
        detections = []
        if results and results[0].boxes is not None:
            for box, conf in zip(results[0].boxes.xyxy.cpu().numpy(),
                                 results[0].boxes.conf.cpu().numpy()):
                x1, y1, x2, y2 = box
                detections.append(([x1, y1, x2 - x1, y2 - y1], float(conf), 0))

        tracks = tracker.update_tracks(detections, frame=frame)
        for tr in tracks:
            if not tr.is_confirmed():
                continue
            l, t, r, b = tr.to_ltrb()
            cy = (t + b) / 2
            counter.update(int(tr.track_id), cy)

    cap.release()
    return {"count_in": counter.count_in, "count_board": counter.count_board}


def main():
    parser = argparse.ArgumentParser(description="Compare multiple YOLO models on a labeled video")
    parser.add_argument("--video", required=True, help="Path to eval video")
    parser.add_argument("--groundtruth", required=True, help="Path to *_groundtruth.json")
    parser.add_argument("--models", nargs="+", required=True, help="Model .pt paths")
    parser.add_argument("--output", required=True, help="Output CSV path")
    parser.add_argument("--in-ratio", type=float, default=0.7)
    parser.add_argument("--board-ratio", type=float, default=0.3)
    args = parser.parse_args()

    gt = load_groundtruth(Path(args.groundtruth))
    video_name = Path(args.video).name

    rows = []
    for model_path in args.models:
        model_name = Path(model_path).stem
        print(f"[eval_counting] running {model_name} on {video_name} ...")
        ai = run_counter_on_video(Path(args.video), Path(model_path),
                                   in_ratio=args.in_ratio, board_ratio=args.board_ratio)
        row = build_comparison_row(model_name, video_name,
                                    ai["count_in"], ai["count_board"],
                                    gt["count_in"], gt["count_board"])
        rows.append(row)
        print(f"  IN: {row['ai_in']}/{row['gt_in']} ({row['in_error_pct']:.1f}%)  "
              f"BOARD: {row['ai_board']}/{row['gt_board']} ({row['board_error_pct']:.1f}%)")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest hardware/tests/test_eval_counting.py -v`
Expected: 6 passed

(주의: `run_counter_on_video`는 yolo/deepsort/실제 mp4가 필요하므로 단위 테스트에서 제외. Phase 6 실제 실행 시 검증.)

- [ ] **Step 5: 커밋**

```bash
git add hardware/eval_counting.py hardware/tests/test_eval_counting.py
git commit -m "feat(yolo-data): add eval_counting.py with TDD (Phase 6-2)

영상 1개 × 여러 모델에 counter.py LineCrossingCounter 적용해
IN/BOARD 오차율 CSV 출력. Phase 6 (Counting 평가)에서 사용.

테스트: 오차율 계산, GT=0 가드, JSON 로딩, comparison row 빌드 — 6 passed.
(run_counter_on_video는 yolo+deepsort+실제 영상 의존이라 단위 테스트 제외.)"
```

---

## Task 1.4: 공개 데이터셋 선택 + 다운로드

**Files:**
- Modify: `datasets/bustago_person/README.md` (출처 행 채움)
- Create: `datasets/bustago_person/public_baseline/{images,labels}/{train,val}/...` (외장 SSD에서)

> 이 Task는 사람 작업: Roboflow 가입·라이선스 확인이 필요. 코드 작업 아님.

- [ ] **Step 1: 후보 3개 비교**

직접 다음 경로에서 검색해서 비교:

| 출처 | 검색어 | 확인 항목 |
|---|---|---|
| Roboflow Universe (https://universe.roboflow.com/) | "person detection", "pedestrian detection" | val 매수 ≥ 500, 라이선스 (CC BY / MIT 권장), YOLOv11 export 지원 |
| CrowdHuman (https://www.crowdhuman.org/) | — | 학술 사용 한정, 군중 밀집 환경, 매우 큼 |
| COCO val (https://cocodataset.org/) | person 클래스만 필터 | 사실상 yolo11n 학습 데이터 → baseline 상한선이라 자기참조 위험 |

권장 선정 기준 (우선순위 순):
1. 라이선스 명확 (CC BY 4.0 또는 MIT)
2. val 매수 ≥ 500
3. 실내/실외 혼합 (정류장 환경 근사)
4. YOLOv11 export format 다운로드 가능 (라벨 변환 불필요)

선정 후 해당 URL/라이선스/매수를 README.md에 기록.

- [ ] **Step 2: 선택된 데이터셋 다운로드 (YOLOv11 export format)**

Roboflow에서 "Format: YOLOv11" 선택해서 zip 다운로드.

```bash
cd /media/$USER/BUSTAGO_DATA/datasets/bustago_person/public_baseline
unzip ~/Downloads/people-detection-image-dataset.v*.zip
```

기대 구조:
```
public_baseline/
├── data.yaml
├── images/{train,val,test}/
└── labels/{train,val,test}/
```

> 외장 SSD 경로 + 심볼릭 링크: 프로젝트 루트에서  
> `ln -s /media/$USER/BUSTAGO_DATA/datasets/bustago_person/public_baseline datasets/bustago_person/public_baseline`

- [ ] **Step 3: README 출처 갱신**

`datasets/bustago_person/README.md` 표의 `public_baseline` 행에 실제 URL/라이선스/매수 기입.

- [ ] **Step 4: 검증**

```bash
ls datasets/bustago_person/public_baseline/images/val/ | wc -l
```
Expected: ≥ 200 (val 매수 충분)

```bash
head -1 datasets/bustago_person/public_baseline/labels/val/*.txt | head
```
Expected: `0 0.xxx 0.xxx 0.xxx 0.xxx` 형태 (YOLO format)

- [ ] **Step 5: bustago_person.yaml 경로 확인**

`hardware/configs/bustago_person.yaml`이 `public_baseline` 경로를 가리키는지 확인:

```bash
cat hardware/configs/bustago_person.yaml
```

기존 내용:
```yaml
path: datasets/bustago_person
train: images/train
val: images/val
test: images/test
names:
  0: person
```

필요 시 수정 — Roboflow 다운로드한 `data.yaml`의 클래스명이 `person`이 아니라 다른 이름이면 본 yaml의 `names`에 맞추거나, train/val 경로를 `public_baseline/images/train`처럼 변경.

권장 수정:
```yaml
path: datasets/bustago_person/public_baseline
train: images/train
val: images/val
test: images/test
names:
  0: person
```

- [ ] **Step 6: 커밋 (README 업데이트만)**

```bash
git add datasets/bustago_person/README.md hardware/configs/bustago_person.yaml
git commit -m "docs(yolo-data): record public_baseline dataset source (Phase 1-1)

선택: [Roboflow People Detection Dataset URL]
라이선스: CC BY 4.0
매수: train [N] / val [N]
경로: datasets/bustago_person/public_baseline/ (외장 SSD 심볼릭 링크)"
```

> 데이터 파일 자체는 .gitignore되어 커밋 안 됨 — README 메타정보만 트래킹.

---

## Task 1.5: baseline yolo val 실행

**Files:**
- Produces: `runs/bustago/baseline_val/results.csv` (Git X)

- [ ] **Step 1: ultralytics 설치 확인**

Run: `python3 -c "from ultralytics import YOLO; print('OK')"`
Expected: `OK`

미설치 시: `pip install ultralytics`

- [ ] **Step 2: yolo11n.pt 사전모델 다운로드 (자동)**

Run: `python3 -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"`
Expected: yolo11n.pt 자동 다운로드, 종료 코드 0

- [ ] **Step 3: baseline 평가**

```bash
yolo val \
    model=yolo11n.pt \
    data=hardware/configs/bustago_person.yaml \
    project=runs/bustago \
    name=baseline_val \
    exist_ok=True
```

Expected: 종료 후 다음 파일 생성
- `runs/bustago/baseline_val/results.csv` (mAP 곡선)
- `runs/bustago/baseline_val/confusion_matrix.png`
- `runs/bustago/baseline_val/PR_curve.png`

콘솔에서 다음 라인 캡처:
```
                  Class     Images  Instances        Box(P          R      mAP50  mAP50-95)
                    all        ...        ...        0.xxx      0.xxx     0.xxx     0.xxx
```

- [ ] **Step 4: 수치 기록**

위 출력의 P / R / mAP50 / mAP50-95 4개 수치를 적어두고 Task 1.6에서 리포트에 기입.

---

## Task 1.6: 리포트 §4.1 baseline 행 채움

**Files:**
- Modify: `docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md`

- [ ] **Step 1: §4.1 표의 baseline 행 수정**

기존:
```markdown
| YOLO11n baseline (yolo11n.pt) | [기입] | [기입] | [기입] | [기입] | 기준선 |
```

수정 (Task 1.5에서 얻은 실측치 대입):
```markdown
| YOLO11n baseline (yolo11n.pt) | 0.xxx | 0.xxx | 0.xxx | 0.xxx | 기준선 (public val) |
```

> public 데이터셋 기준이므로 비고에 명시. self_v1 val 결과는 Phase 4 이후 행 추가.

- [ ] **Step 2: §1 평가 개요의 측정 환경 갱신**

리포트 §1 표의 "평가 환경" 행에 실제 데이터셋 명 + 다운로드 일자 기입.

- [ ] **Step 3: 커밋**

```bash
git add docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
git commit -m "docs(yolo-data): record baseline yolo11n.pt mAP on public val (Phase 1-4)

mAP50: 0.xxx / P: 0.xxx / R: 0.xxx (Roboflow [DATASET] val)
self_v1 val 측정은 Phase 4 이후 추가 행으로 기록."
```

---

## Task 1.7: 시연 안내문 + 촬영 스크립트 준비

**Files:**
- Produces (외부): A4 안내문 출력본

- [ ] **Step 1: 안내문 텍스트는 `docs/03_구축/촬영_동의_및_삭제_절차.md` §3 사용**

- [ ] **Step 2: 책임자 연락처를 실제값으로 채워 별도 인쇄용 파일 작성**

`/tmp/bustago_안내문.txt` 또는 워드로 작성 → A4 1매 출력 → 시연 현장 부착.

> 본 단계는 코드 변경 없음. 시연 전날(5/20) 출력.

- [ ] **Step 3: 촬영 장비 점검 체크리스트**

- [ ] Jetson Orin Nano 부팅 (이미 5/16 검증됨)
- [ ] USB 웹캠 또는 Pi Camera v2 연결 (5/16 USB 웹캠 검증됨)
- [ ] 외장 SSD `BUSTAGO_DATA` 마운트
- [ ] `mkdir -p /media/$USER/BUSTAGO_DATA/raw_videos`
- [ ] 시연 영상 녹화 스크립트 1줄:
  ```bash
  ffmpeg -f v4l2 -i /dev/video0 -t 3600 -c:v libx264 -preset ultrafast \
      /media/$USER/BUSTAGO_DATA/raw_videos/2026-05-21_demo_INS01.mp4
  ```

---

# Phase 2 (5/21 시연 당일) — baseline 시연 + 데이터 수집

> 본 Phase는 절차적 실행. 코드 변경 없음.

- [ ] **Step 1: counter.py 시연 실행**

```bash
cd /home/bustago/bustago
python3 hardware/counter.py \
    --camera 0 --model yolo11n.pt \
    --server http://SERVER_IP:5000/api/crowd-count \
    --station-id INS01 --post-interval 10 --debug
```

- [ ] **Step 2: 별도 트랙으로 영상 녹화 (Task 1.7 Step 3의 ffmpeg)**

동의 시간대 시작/종료 시각을 노트에 기록.

- [ ] **Step 3: 시연 종료 직후 raw 영상 이중 백업**

```bash
rsync -avh /media/$USER/BUSTAGO_DATA/raw_videos/ ~/PC_BACKUP/raw_videos/
```

---

# Phase 3 (5/22~5/24) — 자체 데이터 가공

- [ ] **Step 1: 프레임 추출**

```bash
python3 hardware/sample_frames.py \
    --video /media/$USER/BUSTAGO_DATA/raw_videos/2026-05-21_demo_INS01.mp4 \
    --out datasets/bustago_person/self_v1/frames \
    --interval 2.0
```

Expected: 600~1800장 출력

- [ ] **Step 2: auto-label**

```bash
python3 hardware/autolabel.py \
    --images datasets/bustago_person/self_v1/frames \
    --labels datasets/bustago_person/self_v1/labels_auto \
    --model yolo11x.pt --conf 0.25 --classes 0
```

Expected: frames 매수와 동일한 .txt 파일

- [ ] **Step 3: 사람 검수 (Roboflow 또는 LabelImg)**

Roboflow 무료 plan:
1. Project 생성 → Upload `frames/` + `labels_auto/`
2. 잘못 잡힌 bbox 드롭/수정
3. 8:2 train/val split (Roboflow가 자동 처리)
4. Export → YOLOv11 format → `datasets/bustago_person/self_v1/images/`, `labels/`

검수 시 영상 단위 grouping 유지 — 한 영상의 프레임은 train 또는 val 한쪽에만.

- [ ] **Step 4: self yaml 생성**

`hardware/configs/bustago_person_self.yaml`:

```yaml
path: datasets/bustago_person/self_v1
train: images/train
val: images/val
names:
  0: person
```

```bash
git add hardware/configs/bustago_person_self.yaml
git commit -m "feat(yolo-data): add self_v1 dataset yaml (Phase 3-5)"
```

- [ ] **Step 5: yaml 로딩 sanity check**

```bash
python3 -c "
from ultralytics import YOLO
m = YOLO('yolo11n.pt')
m.val(data='hardware/configs/bustago_person_self.yaml', project='runs/bustago', name='self_v1_val_sanity', exist_ok=True)
"
```

Expected: 종료 코드 0 + 결과 mAP 출력 (수치 자체는 무의미, 경로 검증용)

---

# Phase 4 (5/25~5/29) — fine-tune 1차

- [ ] **Step 1: 로컬 RTX 3080 환경 확인**

```bash
python3 -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

Expected: `CUDA: True`, `Device: NVIDIA GeForce RTX 3080`

실패 시 → R4 폴백: Colab으로 전환 (Phase 1-1 끝에 미리 노트북 1개 준비).

- [ ] **Step 2: fine-tune 1차 실행**

```bash
python3 hardware/train_yolo.py \
    --data hardware/configs/bustago_person_self.yaml \
    --model yolo11n.pt \
    --name self_v1_finetune \
    --epochs 100 --imgsz 640 --batch 16 --device 0
```

> imgsz를 960 → 640으로 줄임: 자체 데이터셋 양이 적을 가능성 + 학습 시간 절약. 결과 안 좋으면 imgsz=960으로 재시도.

Expected:
- `runs/bustago/self_v1_finetune/weights/best.pt` 생성
- `runs/bustago/self_v1_finetune/results.csv` 생성
- mAP50 0.5+ 권장

- [ ] **Step 3: self_v1 val 평가**

```bash
yolo val \
    model=runs/bustago/self_v1_finetune/weights/best.pt \
    data=hardware/configs/bustago_person_self.yaml \
    project=runs/bustago \
    name=self_v1_finetune_val \
    exist_ok=True
```

수치를 기록.

- [ ] **Step 4: baseline도 self_v1 val에서 평가 (비교 일관성)**

```bash
yolo val \
    model=yolo11n.pt \
    data=hardware/configs/bustago_person_self.yaml \
    project=runs/bustago \
    name=baseline_on_self_val \
    exist_ok=True
```

- [ ] **Step 5: 리포트 §4.1 갱신**

baseline 행을 self_v1 val 결과로 갱신 + fine-tune1 행 추가.

```bash
git add docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
git commit -m "docs(yolo-data): record fine-tune1 vs baseline on self_v1 val (Phase 4-3)"
```

---

# Phase 5 (5/30~6/1) — 증강 fine-tune 2차

- [ ] **Step 1: 증강 hyperparam 명시한 학습 실행**

Ultralytics는 train hyperparam을 명령행에 직접 지정 가능 (가장 영향력 큰 3개):

```bash
yolo train \
    model=yolo11n.pt \
    data=hardware/configs/bustago_person_self.yaml \
    project=runs/bustago \
    name=self_v1_augmented \
    epochs=100 imgsz=640 batch=16 device=0 \
    cos_lr=True close_mosaic=10 \
    fliplr=0.5 hsv_h=0.015 hsv_s=0.7 hsv_v=0.4 mosaic=1.0 \
    exist_ok=True
```

- [ ] **Step 2: self val 평가**

```bash
yolo val \
    model=runs/bustago/self_v1_augmented/weights/best.pt \
    data=hardware/configs/bustago_person_self.yaml \
    project=runs/bustago \
    name=self_v1_augmented_val \
    exist_ok=True
```

- [ ] **Step 3: 리포트 §4.1 fine-tune2 행 추가**

```bash
git add docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
git commit -m "docs(yolo-data): record fine-tune2 (+aug) on self_v1 val (Phase 5-2)"
```

- [ ] **Step 4: R3 트리거 확인**

If mAP50(fine-tune2) < mAP50(baseline) - 0.02:
→ R3 폴백 실행: hyperparam 조정 (epochs 50, freeze 일부 layer) → 데이터 추가 → baseline 채택 + 원인 분석.

---

# Phase 6 (6/2~6/3) — Counting 평가

- [ ] **Step 1: eval_videos 확보**

train/val에 없는 별도 영상 1~3개. 시연 영상 중 일부 분리 금지(불변식 3). 추가 촬영이 가장 안전.

- [ ] **Step 2: 영상 사후 라벨링**

각 영상에 대해 사람이 일시정지·되감기하며 통과 인스턴스 카운트. `datasets/bustago_person/eval_videos/<영상>_groundtruth.json` 작성:

```json
{
  "video": "video01.mp4",
  "duration_sec": 600,
  "camera_position": "INS01_north_2.2m_45deg",
  "lighting": "낮_실내_밝음",
  "in_line": [[100, 350], [540, 350]],
  "board_line": [[100, 200], [540, 200]],
  "ground_truth": {"count_in": 47, "count_board": 33, "crossings_in": [], "crossings_board": []},
  "labeled_by": "류훈민",
  "labeled_at": "2026-06-02"
}
```

- [ ] **Step 3: eval_counting.py 3 모델 비교**

각 영상별:
```bash
python3 hardware/eval_counting.py \
    --video datasets/bustago_person/eval_videos/video01.mp4 \
    --groundtruth datasets/bustago_person/eval_videos/video01_groundtruth.json \
    --models yolo11n.pt \
             runs/bustago/self_v1_finetune/weights/best.pt \
             runs/bustago/self_v1_augmented/weights/best.pt \
    --output runs/bustago/eval_counting_video01.csv
```

- [ ] **Step 4: 리포트 §4.2 Counting 비교표 채움**

CSV의 in_error_pct / board_error_pct를 리포트 §4.2 표에 옮김.

- [ ] **Step 5: 리포트 §4.3 Runtime fine-tune 추가**

Jetson에서 각 모델 추론 latency 측정:

```bash
# Jetson에서
python3 hardware/counter.py \
    --camera 0 --model runs/bustago/self_v1_finetune/weights/best.pt --debug
# 콘솔의 ms/frame 평균값 5분 측정
```

- [ ] **Step 6: 커밋**

```bash
git add datasets/bustago_person/eval_videos/*_groundtruth.json
git add docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md
git commit -m "docs(yolo-data): record Counting eval + Runtime (Phase 6-3, 6-4)

eval_videos N개에 baseline/ft1/ft2 비교, IN/BOARD 오차율 표 채움.
Jetson runtime ms/frame 측정값 §4.3에 추가."
```

---

# Phase 7 (6/4) — 마무리

- [ ] **Step 1: 리포트 §5 환경별 표 채움**

§4.2의 영상별 결과를 환경 조건(밝음/어두움/다중)으로 재정렬.

- [ ] **Step 2: 리포트 §6 오차 원인 분석**

mAP·Counting 결과 보면서 §6 후보 목록에서 해당하는 것 골라 서술. fine-tune이 baseline 못 이긴 부분이 있으면 R3 폴백의 원인 분석 결과를 인용.

- [ ] **Step 3: 리포트 §7 개선 방안 + §8 결론**

- [ ] **Step 4: 발표 자료에 §4.1 / §4.2 표 삽입**

`docs/발표자료/발표_슬라이드_구조.md`에 표 ID로 참조 추가.

- [ ] **Step 5 (선택): TensorRT export**

```bash
yolo export model=runs/bustago/self_v1_augmented/weights/best.pt format=engine half=True
# 출력: best.engine → Jetson `runs/bustago/self_v1_augmented/weights/best.engine`
```

R6 폴백: 실패 시 `.pt` 그대로 Jetson 추론 (이미 35 FPS 검증).

- [ ] **Step 6: 최종 커밋 + 푸시**

```bash
git add docs/04_테스트/AI_카운팅_정확도_리포트_템플릿.md docs/발표자료/
git commit -m "docs(yolo-data): finalize report §5-§8 for 2026-06-04 contest (Phase 7)"
git push origin feat/hunmin
```

---

## 완료 정의 (Definition of Done)

본 plan은 다음을 만족하면 완료:

1. 리포트 §4.1에 3행 (baseline / ft1 / ft2) 모두 실측치
2. 리포트 §4.2에 3 모델 × N 영상 Counting 오차율
3. 리포트 §4.3에 FPS / latency
4. `docs/03_구축/촬영_동의_및_삭제_절차.md` 존재 + 시연 부착 안내문 출력 완료
5. 모든 Phase 커밋이 `feat/hunmin` 브랜치에 push됨
6. Self-review: pytest hardware/tests/ 전체 통과 (test_sample_frames + test_autolabel + test_eval_counting = 15 passed)
