"""
BUSTAGO Backend -- /api/crowd-count 엔드포인트
Jetson 디바이스에서 전송하는 군중 카운팅 데이터를 수신·조회.
"""

import logging
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, abort

from backend.models.db import fetchone, fetchall, execute
from backend.extensions import limiter

log = logging.getLogger(__name__)

crowd_bp = Blueprint("crowd", __name__)


def _validate_station_id(station_id):
    """station_id 유효성 검사. 실패 시 abort(400)."""
    if not station_id:
        abort(400, description="station_id is required")
    if not re.fullmatch(r"[A-Za-z0-9]{3,10}", station_id):
        abort(400, description="station_id must be 3-10 alphanumeric characters")


def _validate_non_negative_int(value, name):
    """non-negative integer 유효성 검사. 실패 시 abort(400)."""
    if not isinstance(value, int) or isinstance(value, bool):
        abort(400, description=f"{name} must be a non-negative integer")
    if value < 0:
        abort(400, description=f"{name} must be a non-negative integer")


DEMO_STATION_ID = "DEMO01"


def _validate_demo_station(station_id):
    """시연 전용 엔드포인트 진입 전 station_id 검사. DEMO01만 허용."""
    _validate_station_id(station_id)
    if station_id != DEMO_STATION_ID:
        abort(400, description=f"This endpoint only accepts station_id={DEMO_STATION_ID}")


@crowd_bp.route("/api/crowd-count", methods=["POST"])
@limiter.limit("60 per minute")
def post_crowd_count():
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="JSON body is required")

    station_id = data.get("station_id")
    _validate_station_id(station_id)

    count_in = data.get("count_in", 0)
    count_board = data.get("count_board", 0)
    current_waiting = data.get("current_waiting", 0)

    _validate_non_negative_int(count_in, "count_in")
    _validate_non_negative_int(count_board, "count_board")
    _validate_non_negative_int(current_waiting, "current_waiting")

    source = data.get("source", "jetson")

    try:
        execute(
            "INSERT INTO crowd_counts (station_id, count_in, count_board, current_waiting, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (station_id, count_in, count_board, current_waiting, source),
        )
    except Exception as e:
        # crowd_counts INSERT 실패는 클라이언트(Jetson)에 500을 반환해 재시도 유도.
        # 원인은 운영자가 확인할 수 있게 반드시 로깅.
        log.error(
            "crowd_counts INSERT 실패 station_id=%s in=%s board=%s: %s",
            station_id, count_in, count_board, e,
        )
        abort(500, description="Failed to save crowd count")

    return jsonify({
        "status": "ok",
        "message": "Crowd count saved",
        "timestamp": datetime.now().isoformat(),
    })


@crowd_bp.route("/api/crowd-count", methods=["GET"])
@limiter.limit("30 per minute")
def get_crowd_count():
    station_id = request.args.get("station_id")
    _validate_station_id(station_id)

    row = fetchone(
        "SELECT station_id, count_in, count_board, current_waiting, source, created_at "
        "FROM crowd_counts WHERE station_id = ? ORDER BY id DESC LIMIT 1",
        (station_id,),
    )

    if not row:
        abort(404, description="No crowd count data found for this station")

    return jsonify({
        "status": "ok",
        "data": dict(row),
        "timestamp": datetime.now().isoformat(),
    })


@crowd_bp.route("/api/crowd-count/history", methods=["GET"])
@limiter.limit("10 per minute")
def get_crowd_count_history():
    station_id = request.args.get("station_id")
    _validate_station_id(station_id)

    limit = request.args.get("limit", "60")
    if not limit.isdigit() or int(limit) < 1:
        abort(400, description="limit must be a positive integer")
    limit = int(limit)

    rows = fetchall(
        "SELECT station_id, count_in, count_board, current_waiting, source, created_at "
        "FROM crowd_counts WHERE station_id = ? ORDER BY id DESC LIMIT ?",
        (station_id, limit),
    )

    return jsonify({
        "status": "ok",
        "data": rows,
        "count": len(rows),
        "timestamp": datetime.now().isoformat(),
    })


@crowd_bp.route("/api/crowd-count/event", methods=["POST"])
@limiter.limit("30 per minute")
def post_crowd_count_event():
    """시연용 수동 이벤트 주입. station_id=DEMO01 전용.

    Body: {"station_id": "DEMO01", "event_type": "in" | "board"}
    마지막 row를 읽어와 count_in 또는 count_board 를 +1 한 새 row INSERT.
    """
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="JSON body is required")

    station_id = data.get("station_id")
    _validate_demo_station(station_id)

    event_type = data.get("event_type")
    if event_type not in ("in", "board"):
        abort(400, description="event_type must be 'in' or 'board'")

    last = fetchone(
        "SELECT count_in, count_board FROM crowd_counts "
        "WHERE station_id = ? ORDER BY id DESC LIMIT 1",
        (station_id,),
    )
    last_in = last["count_in"] if last else 0
    last_board = last["count_board"] if last else 0

    if event_type == "in":
        new_in = last_in + 1
        new_board = last_board
    else:
        if last_in - last_board <= 0:
            abort(400, description="대기 인원이 0인데 board 불가")
        new_in = last_in
        new_board = last_board + 1

    new_waiting = max(0, new_in - new_board)

    execute(
        "INSERT INTO crowd_counts (station_id, count_in, count_board, current_waiting, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (station_id, new_in, new_board, new_waiting, "demo_button"),
    )

    return jsonify({
        "status": "ok",
        "count_in": new_in,
        "count_board": new_board,
        "current_waiting": new_waiting,
        "timestamp": datetime.now().isoformat(),
    })
