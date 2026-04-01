"""
BUSTAGO Backend -- Flask 확장 모듈
순환 참조 방지를 위해 Limiter 등 확장 객체를 여기서 생성한다.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "60 per minute"],
    storage_uri="memory://",
)
