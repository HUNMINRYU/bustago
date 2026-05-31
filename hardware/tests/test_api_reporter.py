"""APIReporter.post_if_changed 단위 테스트 (HTTP 모킹).

dev 머신에 torch/ultralytics 미설치 시 자동 skip — Jetson에서만 실행되도록.
"""

import pytest
from unittest.mock import patch, MagicMock

# counter.py를 모듈로 import — sys.path 보강
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from counter import APIReporter, LineCrossingCounter
except ImportError as e:
    pytest.skip(f"counter import 실패 (Jetson 의존성 필요): {e}", allow_module_level=True)


@pytest.fixture
def reporter():
    return APIReporter(server_url="http://localhost:5000", station_id="DEMO01", interval=10.0)


@pytest.fixture
def counter():
    return LineCrossingCounter(frame_width=640, in_ratio=0.7, board_ratio=0.3)


def test_post_if_changed_skips_when_unchanged(reporter, counter):
    """count_in, count_board 둘 다 0이면 POST 안 보냄."""
    with patch("counter.requests.post") as mock_post:
        result = reporter.post_if_changed(counter)
    assert result is False
    mock_post.assert_not_called()


def test_post_if_changed_sends_when_count_in_increases(reporter, counter):
    """count_in 증가 시 즉시 POST 발사."""
    counter.count_in = 1
    with patch("counter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        reporter.post_if_changed(counter)
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["count_in"] == 1


def test_post_if_changed_remembers_state(reporter, counter):
    """동일 값 재호출 시 POST 안 보냄."""
    counter.count_in = 1
    with patch("counter.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        reporter.post_if_changed(counter)  # 첫 호출 → POST
        reporter.post_if_changed(counter)  # 두 번째 → no-op
    assert mock_post.call_count == 1
