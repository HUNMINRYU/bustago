"""
BUSTAGO Backend -- /api/stats 엔드포인트
"""

import time
from datetime import datetime, timedelta
from functools import lru_cache
from flask import Blueprint, request, jsonify, abort

from backend.models.db import fetchall
from backend.extensions import limiter

stats_bp = Blueprint("stats", __name__)

_STATS_CACHE = {}
_STATS_CACHE_TTL = 60


@lru_cache(maxsize=256)
def _stats_cache_key(station_id: str, period: str) -> tuple[str, str]:
    return (station_id, period)


def _get_cached_rows(station_id: str, period: str, since: str):
    cache_key = _stats_cache_key(station_id, period)
    cached = _STATS_CACHE.get(cache_key)
    now_ts = time.time()

    if cached and now_ts - cached["timestamp"] < _STATS_CACHE_TTL:
        return cached["rows"]

    rows = fetchall(
        "SELECT hour, predicted_level, predicted_label, created_at "
        "FROM predictions "
        "WHERE station_ars_no = ? AND created_at >= ? "
        "ORDER BY hour",
        (station_id, since),
    )
    _STATS_CACHE[cache_key] = {"timestamp": now_ts, "rows": rows}
    return rows


@stats_bp.route("/api/stats")
@limiter.limit("30 per minute")
def stats():
    station_id = request.args.get("station_id")
    period = request.args.get("period", "today")

    if not station_id:
        abort(400, description="station_id is required")
    if period not in ("today", "week", "month"):
        abort(400, description="period must be one of: today, week, month")

    now = datetime.now()

    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    elif period == "week":
        since = (now - timedelta(days=7)).isoformat()
    else:
        since = (now - timedelta(days=30)).isoformat()

    rows = _get_cached_rows(station_id, period, since)

    # 시간대별 평균 혼잡도
    hourly = {}
    for row in rows:
        h = row["hour"]
        if h not in hourly:
            hourly[h] = {"sum": 0, "count": 0}
        hourly[h]["sum"] += row["predicted_level"]
        hourly[h]["count"] += 1

    hourly_stats = []
    for h in range(24):
        if h in hourly:
            avg = round(hourly[h]["sum"] / hourly[h]["count"], 2)
        else:
            avg = None
        hourly_stats.append({"hour": h, "avg_level": avg})

    return jsonify({
        "status": "ok",
        "data": {
            "station_id": station_id,
            "period": period,
            "hourly_stats": hourly_stats,
            "total_predictions": len(rows),
        },
        "timestamp": now.isoformat(),
    })
