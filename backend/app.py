"""
BUSTAGO Backend -- Flask Application
"""

import logging
import sys
import os

# 프로젝트 루트를 sys.path에 추가 (ml.models.predict import 가능하게)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import DEBUG, PORT
from backend.models.db import init_db
from backend.extensions import limiter
from backend.routes.congestion import congestion_bp  # 2026-05-17 단순화 D: predict + recommend 통합
from backend.routes.stats import stats_bp
from backend.routes.stations import stations_bp
from backend.routes.crowd import crowd_bp


def _configure_logging():
    """backend.* 모듈의 logger를 stderr WARNING 이상으로 노출.
    Flask 디버그 모드에서는 Flask의 logger도 같은 핸들러를 공유한다.
    이미 핸들러가 붙어있으면(중복 호출) 두 번 추가하지 않는다.
    """
    root_logger = logging.getLogger("backend")
    if root_logger.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                            datefmt="%H:%M:%S")
    handler.setFormatter(fmt)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if DEBUG else logging.WARNING)


def create_app():
    _configure_logging()

    app = Flask(__name__)
    CORS(app)
    limiter.init_app(app)

    # Blueprint 등록 (2026-05-17 단순화 D: predict_bp + recommend_bp → congestion_bp)
    app.register_blueprint(congestion_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(stations_bp)
    app.register_blueprint(crowd_bp)

    # DB 초기화
    with app.app_context():
        init_db()

    # 헬스 체크
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

    # 전역 에러 핸들러
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"status": "error", "message": str(e.description), "code": 400}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"status": "error", "message": "Not found", "code": 404}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"status": "error", "message": "요청 횟수 초과. 잠시 후 다시 시도해주세요.", "code": 429}), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"status": "error", "message": "Internal server error", "code": 500}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
