"""
BUSTAGO AI People Counter
=========================
YOLOv11 + DeepSORT + Line Crossing 기반 정류장 인원 카운팅.

- Jetson Orin Nano: TensorRT FP16 엔진 사용 (25~40 FPS)
- PC 개발: PyTorch .pt 모델로 웹캠 테스트 가능

Usage:
    # PC 웹캠 테스트
    python counter.py --camera 0 --model yolo11n.pt --server http://localhost:5000

    # Jetson 배포 (TensorRT)
    python counter.py --camera 0 --model yolo11n.engine --server http://SERVER_IP/api/crowd-count

    # 디버그 모드 (화면 표시)
    python counter.py --camera 0 --model yolo11n.pt --debug
"""

from __future__ import annotations

import argparse
import time
import logging
import sys
from collections import defaultdict

import cv2
import numpy as np
import requests
from ultralytics import YOLO

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
except ImportError:
    print("[WARN] deep-sort-realtime 미설치. pip install deep-sort-realtime")
    DeepSort = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("counter")


# ---------------------------------------------------------------------------
# Line Crossing Counter
# ---------------------------------------------------------------------------
class LineCrossingCounter:
    """가상 라인 2개(IN, BOARD)를 기준으로 Track ID별 통과를 판정."""

    def __init__(self, frame_height: int, in_ratio: float = 0.7, board_ratio: float = 0.3):
        """
        Args:
            frame_height: 프레임 세로 해상도
            in_ratio: IN 라인의 y 위치 비율 (0=상단, 1=하단). 정류장 진입 라인.
            board_ratio: BOARD 라인의 y 위치 비율. 버스 탑승 라인.
        """
        self.in_line_y = int(frame_height * in_ratio)
        self.board_line_y = int(frame_height * board_ratio)

        self.count_in = 0       # IN 라인 통과 (정류장 진입)
        self.count_board = 0    # BOARD 라인 통과 (버스 탑승)

        # Track ID별 이전 프레임 중심 y 좌표 (DeepSORT track_id는 str)
        self._prev_y: dict[str, float] = {}
        # Track ID별 라인 통과 여부 (중복 카운팅 방지)
        self._crossed_in: set[str] = set()
        self._crossed_board: set[str] = set()

    def update(self, track_id: str, cy: float):
        """Track ID의 현재 중심 y 좌표로 라인 통과 여부를 판정.

        Args:
            track_id: DeepSORT가 부여한 고유 Track ID
            cy: 바운딩 박스 중심 y 좌표
        """
        prev = self._prev_y.get(track_id)
        self._prev_y[track_id] = cy

        if prev is None:
            return

        # IN 라인: 위→아래 통과 (정류장 진입)
        if track_id not in self._crossed_in:
            if prev < self.in_line_y <= cy:
                self.count_in += 1
                self._crossed_in.add(track_id)
                log.info("Track #%s: IN line crossed (진입). Total IN=%d", track_id, self.count_in)

        # BOARD 라인: 아래→위 통과 (버스 탑승)
        if track_id not in self._crossed_board:
            if prev > self.board_line_y >= cy:
                self.count_board += 1
                self._crossed_board.add(track_id)
                log.info("Track #%s: BOARD line crossed (탑승). Total BOARD=%d", track_id, self.count_board)

    @property
    def current_waiting(self) -> int:
        """현재 대기 인원 추정 = 진입 - 탑승 (최소 0)."""
        return max(0, self.count_in - self.count_board)

    def cleanup_lost_tracks(self, active_ids: set[str]):
        """더 이상 추적되지 않는 Track ID 정리."""
        lost = set(self._prev_y.keys()) - active_ids
        for tid in lost:
            del self._prev_y[tid]

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """프레임에 라인과 카운트 정보를 오버레이."""
        h, w = frame.shape[:2]

        # IN 라인 (파란색)
        cv2.line(frame, (0, self.in_line_y), (w, self.in_line_y), (255, 0, 0), 2)
        cv2.putText(frame, f"IN LINE (entered: {self.count_in})",
                    (10, self.in_line_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # BOARD 라인 (초록색)
        cv2.line(frame, (0, self.board_line_y), (w, self.board_line_y), (0, 255, 0), 2)
        cv2.putText(frame, f"BOARD LINE (boarded: {self.count_board})",
                    (10, self.board_line_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 현재 대기 인원 (화면 상단)
        cv2.putText(frame, f"Waiting: {self.current_waiting}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        return frame


# ---------------------------------------------------------------------------
# API Reporter
# ---------------------------------------------------------------------------
class APIReporter:
    """카운팅 결과를 Backend에 주기적으로 POST."""

    def __init__(self, server_url: str, station_id: str, interval: float = 10.0):
        self.url = server_url.rstrip("/")
        if not self.url.endswith("/api/crowd-count"):
            self.url += "/api/crowd-count"
        self.station_id = station_id
        self.interval = interval
        self._last_post = 0.0

    def maybe_post(self, counter: LineCrossingCounter):
        """interval 경과 시 POST 전송."""
        now = time.time()
        if now - self._last_post < self.interval:
            return

        payload = {
            "station_id": self.station_id,
            "count_in": counter.count_in,
            "count_board": counter.count_board,
            "current_waiting": counter.current_waiting,
        }
        try:
            resp = requests.post(self.url, json=payload, timeout=5)
            if resp.status_code == 200:
                log.info("POST → %s (waiting=%d)", self.url, counter.current_waiting)
            else:
                log.warning("POST failed: %d %s", resp.status_code, resp.text[:100])
        except requests.RequestException as e:
            log.warning("POST error: %s", e)

        self._last_post = now


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def run_counter(args):
    """메인 카운팅 루프."""

    target_classes = [int(cls.strip()) for cls in args.classes.split(",") if cls.strip()]

    # 1) YOLO 모델 로드
    log.info("Loading model: %s", args.model)
    model = YOLO(args.model)
    log.info("Model loaded. Type: %s", type(model.predictor).__name__ if model.predictor else "auto")

    # 2) DeepSORT 트래커 초기화
    if DeepSort is None:
        log.error("DeepSORT not available. Install: pip install deep-sort-realtime")
        sys.exit(1)

    tracker = DeepSort(
        max_age=30,             # 30프레임 미탐지 시 Track 삭제
        n_init=3,               # 3프레임 연속 탐지 후 Track 확정
        max_iou_distance=0.7,   # IoU 매칭 임계값
        max_cosine_distance=0.3,  # Re-ID 코사인 거리 임계값
    )

    # 3) 카메라 열기
    cam_id = int(args.camera) if args.camera.isdigit() else args.camera
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        log.error("Cannot open camera: %s", args.camera)
        sys.exit(1)

    # 해상도 설정 (추론 속도 최적화)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info("Camera opened: %dx%d", actual_w, actual_h)

    # 4) Line Crossing 카운터
    lc = LineCrossingCounter(
        frame_height=actual_h,
        in_ratio=args.in_line,
        board_ratio=args.board_line,
    )

    # 5) API Reporter
    reporter = APIReporter(
        server_url=args.server,
        station_id=args.station_id,
        interval=args.post_interval,
    )

    # 6) 메인 루프
    fps_counter = 0
    fps_start = time.time()
    display_fps = 0.0

    log.info("Starting counting loop. Press 'q' to quit (debug mode).")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                log.warning("Frame read failed. Retrying...")
                time.sleep(0.1)
                continue

            # YOLOv11 추론 (기본값: COCO person class 0)
            results = model(frame, classes=target_classes, verbose=False, conf=args.conf)

            # Detection → DeepSORT 입력 형식 변환
            detections = []
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    cls_name = model.names.get(cls_id, str(cls_id))
                    detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls_name))

            # DeepSORT 트래킹
            tracks = tracker.update_tracks(detections, frame=frame)

            # Track별 Line Crossing 체크
            active_ids = set()
            for track in tracks:
                if not track.is_confirmed():
                    continue

                track_id = track.track_id
                active_ids.add(track_id)
                ltwh = track.to_ltwh()
                cx = ltwh[0] + ltwh[2] / 2
                cy = ltwh[1] + ltwh[3] / 2

                lc.update(track_id, cy)

                # 디버그: 바운딩 박스 + Track ID 표시
                if args.debug:
                    x, y, w, h = [int(v) for v in ltwh]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                    cv2.putText(frame, f"ID:{track_id}",
                                (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # 추적 해제된 Track 정리
            lc.cleanup_lost_tracks(active_ids)

            # API POST (10초 간격)
            reporter.maybe_post(lc)

            # FPS 계산
            fps_counter += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                display_fps = fps_counter / elapsed
                fps_counter = 0
                fps_start = time.time()

            # 디버그 화면 표시
            if args.debug:
                lc.draw(frame)
                cv2.putText(frame, f"FPS: {display_fps:.1f}",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.imshow("BUSTAGO Counter", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    finally:
        cap.release()
        if args.debug:
            cv2.destroyAllWindows()
        # 최종 POST
        reporter.maybe_post(lc)
        log.info("Final count — IN: %d, BOARD: %d, Waiting: %d",
                 lc.count_in, lc.count_board, lc.current_waiting)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="BUSTAGO AI People Counter")

    # 카메라
    p.add_argument("--camera", default="0", help="카메라 인덱스 또는 RTSP URL (default: 0)")
    p.add_argument("--width", type=int, default=640, help="캡처 해상도 너비 (default: 640)")
    p.add_argument("--height", type=int, default=480, help="캡처 해상도 높이 (default: 480)")
    p.add_argument("--fps", type=int, default=30, help="캡처 FPS (default: 30)")

    # 모델
    p.add_argument("--model", default="yolo11n.pt",
                   help="YOLOv11 모델 경로 (.pt 또는 .engine)")
    p.add_argument("--conf", type=float, default=0.5,
                   help="YOLO confidence 임계값 (default: 0.5)")
    p.add_argument("--classes", default="0",
                   help="탐지할 클래스 ID 목록, 쉼표로 구분 (default: 0)")

    # Line Crossing
    p.add_argument("--in-line", type=float, default=0.7,
                   help="IN 라인 y 비율 (0=상단, 1=하단, default: 0.7)")
    p.add_argument("--board-line", type=float, default=0.3,
                   help="BOARD 라인 y 비율 (default: 0.3)")

    # 서버
    p.add_argument("--server", default="http://localhost:5000",
                   help="BUSTAGO Backend URL (default: http://localhost:5000)")
    p.add_argument("--station-id", default="INS01",
                   help="정류장 ID (default: INS01)")
    p.add_argument("--post-interval", type=float, default=10.0,
                   help="API POST 간격 (초, default: 10)")

    # 디버그
    p.add_argument("--debug", action="store_true",
                   help="디버그 모드: 화면에 바운딩 박스·라인·FPS 표시")

    return p.parse_args()


if __name__ == "__main__":
    run_counter(parse_args())
