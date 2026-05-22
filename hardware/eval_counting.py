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


def _fmt_pct(x):
    return f"{x:.1f}%" if x is not None else "N/A"


def load_groundtruth(path: Path) -> dict:
    """*_groundtruth.json에서 ground_truth.count_in/board 추출."""
    try:
        data = json.loads(Path(path).read_text())
        gt = data["ground_truth"]
        return {
            "count_in": int(gt["count_in"]),
            "count_board": int(gt["count_board"]),
        }
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid groundtruth JSON {path}: {e}") from e


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

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    counter = LineCrossingCounter(frame_width=w, in_ratio=in_ratio, board_ratio=board_ratio)
    tracker = DeepSort(max_age=30, n_init=3, max_cosine_distance=0.3)
    yolo = YOLO(str(model_path))

    try:
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
                cx = (l + r) / 2
                counter.update(tr.track_id, cx)
    finally:
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
        print(f"  IN: {row['ai_in']}/{row['gt_in']} ({_fmt_pct(row['in_error_pct'])})  "
              f"BOARD: {row['ai_board']}/{row['gt_board']} ({_fmt_pct(row['board_error_pct'])})")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
