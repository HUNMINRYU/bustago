"""yolo11x로 frames/ → labels/ (YOLO format txt) 자동 생성."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Iterable, List, Set


def _validate_params(target_classes: Set[int], min_conf: float) -> None:
    """공통 입력 검증: min_conf ∈ [0,1], target_classes 비어있지 않음."""
    if not target_classes:
        raise ValueError("target_classes must not be empty")
    if not (0.0 <= float(min_conf) <= 1.0):
        raise ValueError(f"min_conf must be in [0, 1], got {min_conf}")


def yolo_results_to_yolo_txt(result, target_classes: Set[int], min_conf: float = 0.25) -> List[str]:
    """Ultralytics YOLO 결과 1장 → YOLO format 텍스트 라인 리스트.

    Format: "<cls> <cx> <cy> <w> <h>" with normalized coords [0,1].
    """
    _validate_params(target_classes, min_conf)

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
    _validate_params(target_classes, min_conf)

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
