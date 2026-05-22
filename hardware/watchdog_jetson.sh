#!/bin/bash
# BUSTAGO Jetson Watchdog — counter.py 프로세스 감시 및 자동 재시작
#
# crontab 등록 (Jetson에서):
#   crontab -e
#   */5 * * * * /home/bustago/hardware/watchdog_jetson.sh >> /var/log/bustago-watchdog.log 2>&1
#
# 구성: 백엔드를 Jetson 자체에서 구동 → SERVER_IP=localhost:5000
#       백엔드를 별도 머신에서 구동하면 SERVER_IP를 해당 IP:포트로 변경

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS=$(date '+%Y-%m-%d %H:%M:%S')

SERVER_IP="localhost:5000"     # 백엔드를 Jetson 자체에서 구동하는 구성
STATION_ID="INS01"
MODEL="yolo11n.engine"
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
