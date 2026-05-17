FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY backend/ ./backend/
COPY ml/ ./ml/

ENV PYTHONPATH=/app

EXPOSE 5000

# gunicorn 동시성 모델 — 2026-05-17 시스템 진단 SI-1 반영.
# 단일 워커 + 멀티스레드: flask_limiter의 memory:// 스토리지가 워커 간 공유 안 됨 →
# workers=2면 Rate Limit이 명세(60/min)의 2배까지 풀리는 버그가 있었다.
# 현재 부하(0.1 req/s)에서는 1 worker + 4 threads로 충분, Rate Limit 명세 정합 보장.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "backend.app:create_app()"]
