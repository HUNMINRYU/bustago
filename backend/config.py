"""
BUSTAGO Backend -- 설정
"""

import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Flask
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
PORT = int(os.getenv("FLASK_PORT", "5000"))

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "bustago")

# SQLite 폴백 경로
SQLITE_PATH = os.path.join(PROJECT_ROOT, "backend", "bustago.db")

# ML 모델
MODEL_PATH = os.path.join(PROJECT_ROOT, "ml", "models", "rf_model.pkl")

# 기상청 API
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_API_URL = os.getenv(
    "WEATHER_API_URL",
    "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst",
)
