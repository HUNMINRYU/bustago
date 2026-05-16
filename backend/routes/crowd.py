"""
BUSTAGO Backend -- /api/crowd-count 엔드포인트
Jetson 디바이스에서 전송하는 군중 카운팅 데이터를 수신·조회.
"""

import re
from datetime import datetime
from flask import Blueprint, request, jsonify, abort

from backend.models.db import fetchone, fetchall, execute
from backend.extensions import limiter

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
    except Exception:
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
