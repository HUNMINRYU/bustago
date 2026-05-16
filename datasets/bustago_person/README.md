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
