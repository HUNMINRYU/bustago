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


def test_invalid_min_conf_raises():
    result = _fake_yolo_result(boxes_xyxy=[[0, 0, 50, 50]], classes=[0], scores=[0.9])
    with pytest.raises(ValueError, match="min_conf"):
        yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=1.5)
    with pytest.raises(ValueError, match="min_conf"):
        yolo_results_to_yolo_txt(result, target_classes={0}, min_conf=-0.1)


def test_empty_target_classes_raises():
    result = _fake_yolo_result(boxes_xyxy=[[0, 0, 50, 50]], classes=[0], scores=[0.9])
    with pytest.raises(ValueError, match="target_classes"):
        yolo_results_to_yolo_txt(result, target_classes=set(), min_conf=0.25)


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
