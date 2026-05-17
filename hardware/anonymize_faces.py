"""학습 데이터 / 발표 자료용 얼굴 비식별 처리 (블러 또는 마스킹).

Phase 3 검수 시점 또는 발표 자료 캡처 가공 시 사용.
OpenCV YuNet (FaceDetectorYN) 사용 — cv2 4.5+ 내장 모듈.

사용 예:
    # 이미지 1장
    python anonymize_faces.py --input frame.jpg --output frame_blur.jpg

    # 디렉토리 일괄 (원본 보존, 결과는 별도 경로)
    python anonymize_faces.py --input datasets/.../images/ --output datasets/.../images_anon/

    # 마스킹 (블러 대신 검은 박스)
    python anonymize_faces.py --input frame.jpg --output frame_mask.jpg --method mask

모델 파일은 첫 실행 시 자동 다운로드 (~338KB).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

log = logging.getLogger("anonymize")

# OpenCV Zoo YuNet 2023mar (최신 안정 버전, 8.5MB → 실제 라이트는 ~338KB)
YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
DEFAULT_MODEL_PATH = Path.home() / ".cache" / "bustago" / "yunet_2023mar.onnx"


def ensure_model(model_path: Path = DEFAULT_MODEL_PATH) -> Path:
    """YuNet ONNX 모델이 없으면 다운로드. 경로 반환."""
    if model_path.exists() and model_path.stat().st_size > 100_000:
        return model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    log.info(f"YuNet 모델 다운로드 중: {YUNET_URL}")
    try:
        urllib.request.urlretrieve(YUNET_URL, str(model_path))
    except Exception as e:
        raise RuntimeError(
            f"YuNet 모델 다운로드 실패: {e}. "
            f"수동으로 받아서 {model_path}에 두세요: {YUNET_URL}"
        ) from e
    size_kb = model_path.stat().st_size // 1024
    log.info(f"다운로드 완료: {model_path} ({size_kb} KB)")
    return model_path


def load_detector(model_path: Path, conf_threshold: float = 0.6):
    """YuNet detector 인스턴스 생성. input_size는 detect() 직전 setInputSize로 갱신."""
    detector = cv2.FaceDetectorYN.create(
        model=str(model_path),
        config="",
        input_size=(320, 320),
        score_threshold=conf_threshold,
        nms_threshold=0.3,
        top_k=5000,
    )
    return detector


def detect_faces(detector, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """이미지에서 얼굴 bbox 리스트 반환. format: [(x, y, w, h), ...]."""
    h, w = image.shape[:2]
    detector.setInputSize((w, h))
    retval, faces = detector.detect(image)
    if faces is None:
        return []
    boxes: List[Tuple[int, int, int, int]] = []
    for face in faces:
        # YuNet output: [x, y, w, h, 5개 landmark x/y, score]
        x, y, fw, fh = (int(round(v)) for v in face[:4])
        x = max(0, x)
        y = max(0, y)
        fw = min(fw, w - x)
        fh = min(fh, h - y)
        if fw > 0 and fh > 0:
            boxes.append((x, y, fw, fh))
    return boxes


def anonymize_image(
    image: np.ndarray,
    detector,
    method: str = "blur",
    pad_ratio: float = 0.15,
) -> Tuple[np.ndarray, int]:
    """이미지 얼굴 영역을 비식별. 처리된 얼굴 수 반환.

    method: "blur" (가우시안) | "mask" (검은 박스) | "pixel" (모자이크)
    pad_ratio: bbox 확장 비율 (얼굴 가장자리 누락 방지)
    """
    boxes = detect_faces(detector, image)
    if not boxes:
        return image, 0

    h, w = image.shape[:2]
    out = image.copy()
    for x, y, fw, fh in boxes:
        # bbox 확장
        pad_w = int(fw * pad_ratio)
        pad_h = int(fh * pad_ratio)
        x0 = max(0, x - pad_w)
        y0 = max(0, y - pad_h)
        x1 = min(w, x + fw + pad_w)
        y1 = min(h, y + fh + pad_h)
        roi = out[y0:y1, x0:x1]
        if roi.size == 0:
            continue

        if method == "blur":
            # 강한 가우시안 — 식별 불가 수준
            k = max(31, ((min(roi.shape[:2]) // 4) | 1))  # odd
            out[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)
        elif method == "mask":
            out[y0:y1, x0:x1] = 0
        elif method == "pixel":
            # 16x16 픽셀로 다운/업샘플 (모자이크)
            small = cv2.resize(roi, (16, 16), interpolation=cv2.INTER_LINEAR)
            out[y0:y1, x0:x1] = cv2.resize(
                small, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_NEAREST
            )
        else:
            raise ValueError(f"Unknown method: {method}")

    return out, len(boxes)


def process_path(
    input_path: Path,
    output_path: Path,
    detector,
    method: str,
) -> Tuple[int, int]:
    """input_path (파일 또는 디렉토리) → output_path. (총 이미지 수, 총 얼굴 수) 반환.

    디렉토리면 *.jpg / *.png를 모두 처리. 라벨 파일(.txt)은 함께 복사.
    """
    if input_path.is_file():
        img = cv2.imread(str(input_path))
        if img is None:
            raise RuntimeError(f"Cannot read image: {input_path}")
        out, n_faces = anonymize_image(img, detector, method=method)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), out)
        return 1, n_faces

    if not input_path.is_dir():
        raise RuntimeError(f"Input path not found: {input_path}")

    output_path.mkdir(parents=True, exist_ok=True)
    images = sorted(
        list(input_path.glob("*.jpg")) + list(input_path.glob("*.png"))
    )
    if not images:
        log.warning(f"No images found in {input_path}")
        return 0, 0

    total_faces = 0
    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            log.warning(f"Skip unreadable: {img_path}")
            continue
        out, n_faces = anonymize_image(img, detector, method=method)
        cv2.imwrite(str(output_path / img_path.name), out)
        total_faces += n_faces

    return len(images), total_faces


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description="YuNet으로 얼굴 비식별 (학습 데이터 / 발표 자료용)"
    )
    parser.add_argument("--input", required=True, help="입력 이미지 또는 디렉토리")
    parser.add_argument("--output", required=True, help="출력 경로 (입력과 동일하면 덮어씀)")
    parser.add_argument(
        "--method",
        default="blur",
        choices=["blur", "mask", "pixel"],
        help="비식별 방식 (기본: blur)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.6,
        help="YuNet confidence threshold (기본: 0.6)",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL_PATH),
        help=f"YuNet ONNX 모델 경로 (기본: {DEFAULT_MODEL_PATH})",
    )
    args = parser.parse_args()

    model_path = ensure_model(Path(args.model))
    detector = load_detector(model_path, conf_threshold=args.conf)

    n_images, n_faces = process_path(
        Path(args.input), Path(args.output), detector, args.method
    )
    log.info(f"Done. images={n_images}, faces_anonymized={n_faces}, method={args.method}")


if __name__ == "__main__":
    main()
