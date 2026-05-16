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
