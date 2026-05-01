#!/bin/bash
# BUSTAGO Jetson Watchdog — counter.py 프로세스 감시 및 자동 재시작
#
# crontab 등록 (Jetson에서):
#   crontab -e
#   */5 * * * * /home/bustago/hardware/watchdog_jetson.sh >> /var/log/bustago-watchdog.log 2>&1
#
# 설치 전 수정 필요: SERVER_IP를 실제 서버 IP로 변경

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS=$(date '+%Y-%m-%d %H:%M:%S')

SERVER_IP="SERVER_IP"          # TODO: 실제 서버 IP로 변경 (예: 192.168.0.100)
STATION_ID="INS01"
MODEL="yolov8n.engine"
LOG="/var/log/bustago-counter.log"

if pgrep -f "counter.py" > /dev/null 2>&1; then
    echo "${TS} [JETSON] counter.py 정상 동작 중"
else
    echo "${TS} [JETSON] counter.py 미실행 — 재시작"
    nohup python3 "${SCRIPT_DIR}/counter.py" \
        --camera 0 \
        --model "${SCRIPT_DIR}/${MODEL}" \
        --server "http://${SERVER_IP}/api/crowd-count" \
        --station-id "${STATION_ID}" \
        --post-interval 10 \
        >> "${LOG}" 2>&1 &
    echo "${TS} [JETSON] 재시작 완료 PID=$!"
fi
