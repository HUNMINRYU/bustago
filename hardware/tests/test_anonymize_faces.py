"""anonymize_faces.py 테스트 (YuNet 모델 mock, 픽셀 효과 검증)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
import pytest

from anonymize_faces import anonymize_image, detect_faces, process_path


def _make_image(w: int = 640, h: int = 480, color: int = 128) -> np.ndarray:
    """단일 색 합성 이미지."""
    return np.full((h, w, 3), color, dtype=np.uint8)


def _fake_detector(face_boxes):
    """YuNet detector mock. setInputSize는 no-op, detect는 (retval, faces ndarray)."""
    det = MagicMock()
    det.setInputSize = MagicMock()
    if not face_boxes:
        det.detect.return_value = (1, None)
    else:
        # YuNet output shape: (N, 15) — x, y, w, h, 10 landmark+score
        arr = np.zeros((len(face_boxes), 15), dtype=np.float32)
        for i, (x, y, w, h) in enumerate(face_boxes):
            arr[i, :4] = [x, y, w, h]
            arr[i, 14] = 0.99  # score
        det.detect.return_value = (1, arr)
    return det


def test_detect_faces_empty():
    det = _fake_detector([])
    img = _make_image()
    assert detect_faces(det, img) == []


def test_detect_faces_clips_to_image_bounds():
    # bbox가 이미지 밖으로 나가는 경우 clip
    det = _fake_detector([(600, 400, 200, 200)])  # 이미지 640x480 → w/h clip 됨
    img = _make_image(w=640, h=480)
    boxes = detect_faces(det, img)
    assert len(boxes) == 1
    x, y, w, h = boxes[0]
    assert x + w <= 640
    assert y + h <= 480


def test_anonymize_blur_changes_pixels():
    # 균일한 이미지 가운데에 노이즈 패턴 넣고 블러가 적용되는지 확인
    img = _make_image()
    img[100:200, 100:200] = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    det = _fake_detector([(100, 100, 100, 100)])

    out, n = anonymize_image(img, det, method="blur")
    assert n == 1
    # 블러 후엔 분산이 줄어들어야 함
    orig_var = float(img[100:200, 100:200].var())
    blur_var = float(out[100:200, 100:200].var())
    assert blur_var < orig_var


def test_anonymize_mask_zeros_region():
    img = _make_image(color=200)
    det = _fake_detector([(50, 50, 100, 100)])

    out, n = anonymize_image(img, det, method="mask")
    assert n == 1
    # 마스킹 영역(pad 포함)은 모두 0
    assert (out[60:140, 60:140] == 0).all()


def test_anonymize_pixel_reduces_unique_colors():
    img = _make_image()
    img[100:200, 100:200] = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    det = _fake_detector([(100, 100, 100, 100)])

    out, n = anonymize_image(img, det, method="pixel")
    assert n == 1
    # 픽셀화: 16x16 격자로 NEAREST 업샘플하면 unique color ≤ 16*16 = 256
    region = out[100:200, 100:200].reshape(-1, 3)
    unique = np.unique(region, axis=0)
    assert len(unique) <= 256


def test_anonymize_no_faces_returns_image_unchanged():
    img = _make_image()
    det = _fake_detector([])
    out, n = anonymize_image(img, det, method="blur")
    assert n == 0
    np.testing.assert_array_equal(out, img)


def test_anonymize_unknown_method_raises():
    img = _make_image()
    det = _fake_detector([(10, 10, 50, 50)])
    with pytest.raises(ValueError, match="Unknown method"):
        anonymize_image(img, det, method="garbage")


def test_process_path_single_file(tmp_path):
    img = _make_image()
    img[100:200, 100:200] = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    in_path = tmp_path / "in.jpg"
    out_path = tmp_path / "out" / "in.jpg"
    cv2.imwrite(str(in_path), img)
    det = _fake_detector([(100, 100, 100, 100)])

    n_imgs, n_faces = process_path(in_path, out_path, det, method="blur")
    assert n_imgs == 1
    assert n_faces == 1
    assert out_path.exists()


def test_process_path_directory(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    for i in range(3):
        img = _make_image()
        cv2.imwrite(str(in_dir / f"a{i}.jpg"), img)
    out_dir = tmp_path / "out"
    det = _fake_detector([(10, 10, 50, 50)])

    n_imgs, n_faces = process_path(in_dir, out_dir, det, method="mask")
    assert n_imgs == 3
    assert n_faces == 3
    assert len(list(out_dir.glob("*.jpg"))) == 3


def test_process_path_missing_input_raises(tmp_path):
    det = _fake_detector([])
    with pytest.raises(RuntimeError, match="not found"):
        process_path(tmp_path / "nope", tmp_path / "out", det, method="blur")


def test_process_path_empty_dir(tmp_path):
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    det = _fake_detector([])

    n_imgs, n_faces = process_path(in_dir, out_dir, det, method="blur")
    assert n_imgs == 0
    assert n_faces == 0
