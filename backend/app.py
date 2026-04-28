"""
BUSTAGO Backend -- Flask Application
"""

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
from backend.routes.predict import predict_bp
from backend.routes.stats import stats_bp
from backend.routes.stations import stations_bp
from backend.routes.crowd import crowd_bp
from backend.routes.recommend import recommend_bp


def create_app():
    app = Flask(__name__)
    CORS(app)
    limiter.init_app(app)

    # Blueprint 등록
    app.register_blueprint(predict_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(stations_bp)
    app.register_blueprint(crowd_bp)
    app.register_blueprint(recommend_bp)

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
