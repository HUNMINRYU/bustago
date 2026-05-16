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
