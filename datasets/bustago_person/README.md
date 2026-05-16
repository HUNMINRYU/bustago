# BUSTAGO Person Detection Dataset

> 최종 갱신: 2026-05-16
> 관리자: 류훈민
> 근거 spec: `docs/superpowers/specs/2026-05-16-yolo-data-track-design.md`

## 구조

```
bustago_person/
├── public_baseline/      # Phase 1: 공개 데이터셋 (baseline 평가용)
│   ├── data.yaml         # Roboflow 원본 yaml (참고용)
│   ├── train/{images,labels}/   # 19,204장
│   ├── valid/{images,labels}/   #  1,857장
│   └── test/{images,labels}/    #    929장
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

| 항목 | 출처 | 라이선스 | 매수 | 사용 시기 |
|---|---|---|---|---|
| public_baseline | [Keio DBA team CrowdHuman v3 BlurHumanFinal](https://universe.roboflow.com/keio-dba-team/crowdhuman-nur7g/dataset/3) — CrowdHuman 원본 기반, 얼굴 비식별 블러 처리 | **CC BY 4.0** | train 19,204 / valid 1,857 / test 929 | 2026-05-16 ~ |
| self_v1 | 광주대 인성관 정류장 INS01 자체촬영 | 본 캡스톤 내부 사용, 2026-12-31 폐기 | TBD | 2026-05-21~ |
| eval_videos | 동일 (별도 영상) | 동일 | TBD | 2026-06-02~ |

## 라벨링 규칙

- 클래스: id=0 — 단일 클래스
  - public_baseline의 데이터셋 yaml은 `body`로 명명
  - 자체촬영(self_v1, eval_videos)은 `person`으로 명명
  - 두 이름은 동일한 ID 0을 가리킴 (yolo 평가 시 영향 없음)
- bbox: 사람 전신 박스. 잘린 부분은 보이는 영역만.
- 최소 크기: 짧은 변 ≥ 20 픽셀. 그 이하는 학습에 노이즈이므로 제외.
- 가려짐: 60% 이상 가려진 사람은 라벨 안 함.
- 형식: Ultralytics YOLO (txt 1개 = 1장, 행당 `cls cx cy w h`, 좌표는 0~1 정규화).

## Baseline 평가 시 주의

CrowdHuman은 군중 밀집·가려짐이 많은 데이터셋이라 yolo11n(COCO 사전학습) baseline mAP50은
일반 보행자 데이터셋(예: COCO val person) 대비 낮게 나올 가능성 큼. 이는 데이터 분포 차이에서
오는 것이며, 광주대 자체 데이터(self_v1) fine-tune 후 개선 폭을 측정하는 reference로 사용한다.

## 트래킹 정책

- `**/*.{jpg,png,mp4}`: Git ignore (외장 SSD `/media/<USER>/BUSTAGO_DATA/`)
- `**/*_groundtruth.json`: Git 트래킹 (라벨 자산)
- 본 README: Git 트래킹

## 개인정보

자체촬영분은 `docs/03_구축/촬영_동의_및_삭제_절차.md` 적용. 발표 자료 사용 시 비식별 처리 필수.
