#!/bin/bash
# BUSTAGO Pi Kiosk Watchdog — Chromium 키오스크 프로세스 감시 및 자동 재시작
#
# crontab 등록 (Raspberry Pi에서):
#   crontab -e
#   */2 * * * * /home/pi/hardware/watchdog_pi.sh >> /var/log/bustago-watchdog-pi.log 2>&1

TS=$(date '+%Y-%m-%d %H:%M:%S')
SERVICE="bustago-kiosk.service"

if pgrep -x "chromium-browser" > /dev/null 2>&1 || pgrep -x "chromium" > /dev/null 2>&1; then
    echo "${TS} [PI] Kiosk 정상 동작 중"
else
    echo "${TS} [PI] Kiosk 미실행 — 재시작"
    sudo systemctl restart "${SERVICE}"
    echo "${TS} [PI] ${SERVICE} restart 완료"
fi
