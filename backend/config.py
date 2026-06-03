"""
BUSTAGO Backend -- 설정

비밀 키는 .env에서 로드한다. 키가 누락되면 시작 시 명시적 경고를 출력하고,
해당 키를 쓰는 기능은 빈 응답/502 폴백으로 동작한다 (앱 시작은 막지 않음).

2026-05-16 진단 §6/§8 P0 반영: GJ_BIS_API_KEY 하드코딩 fallback 제거.
키 rotate는 시연(2026-05-21) 후 별도 진행 — git history에 남은 이전 키는
공공데이터포털 마이페이지에서 재발급해야 완전 해소된다.
"""

import os
import sys
import warnings
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Flask
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
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

# 기상청 API (선택 — 빈 키면 stations.py에서 기본 날씨 반환)
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_API_URL = os.getenv(
    "WEATHER_API_URL",
    "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst",
)

# 광주광역시 버스정보시스템 API (필수)
GJ_BIS_API_KEY = os.getenv("GJ_BIS_API_KEY", "")
GJ_BIS_BASE_URL = os.getenv("GJ_BIS_BASE_URL", "https://apis.data.go.kr/6290000/gj_bis")

# 카카오 지도 JavaScript 키 (운영 대시보드 전용 — /api/public-config로 프론트에 전달).
# 빈 값이면 대시보드 지도 자리에 "키 필요" 안내 박스가 뜸 (화면은 안 깨짐).
# 카카오 JS 키는 브라우저 노출이 정상이며, 보안은 카카오 콘솔의 도메인 화이트리스트로 한다.
KAKAO_MAP_APP_KEY = os.getenv("KAKAO_MAP_APP_KEY", "")


def _warn_missing_keys() -> None:
    """비밀 키 누락 시 명시적 경고. 시작은 막지 않음 (테스트/CI 환경 대응)."""
    missing = []
    if not GJ_BIS_API_KEY:
        missing.append("GJ_BIS_API_KEY")
    if not WEATHER_API_KEY:
        # WEATHER는 선택. 정보 수준 메시지만.
        print(
            "[config] WEATHER_API_KEY 미설정 — 날씨 API 미호출, 기본값 반환 모드.",
            file=sys.stderr,
        )

    if missing:
        msg = (
            "[config] 다음 환경변수가 설정되지 않음: "
            + ", ".join(missing)
            + ". `.env` 파일 또는 시스템 환경변수에 설정하세요. "
            "`.env.example` 참고. 해당 기능은 빈 응답 / 502 폴백으로 동작합니다."
        )
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
        print(msg, file=sys.stderr)


_warn_missing_keys()
