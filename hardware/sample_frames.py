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
    if interval_sec <= 0:
        raise ValueError(f"interval_sec must be positive, got {interval_sec}")
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
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % interval_frames == 0:
                out_path = out_dir / f"{stem}_{count:06d}.jpg"
                cv2.imwrite(str(out_path), frame)
                count += 1
            frame_idx += 1
    finally:
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
