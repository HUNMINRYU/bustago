---
# HW 설치 가이드 Part 2 — Raspberry Pi 4 설정 + 통합 테스트

> 작성일: 2026-05-01 | 담당: 이건영 (Pi), 이트겔 (서버/통합), 류훈민 (통합 확인)
> 전제: Part 1 Jetson 설정 완료 상태에서 시작

---

## 1단계: Raspberry Pi OS 설치

### 1.1 OS 플래싱
```bash
# Raspberry Pi Imager 사용 (PC에서)
# OS 선택: Raspberry Pi OS Lite (64-bit) — 추천
# 또는: Raspberry Pi OS (64-bit) with desktop (GUI 필요 시)

# 고급 설정 (⚙️ 아이콘):
# - 호스트명: bustago-kiosk
# - SSH 활성화: 체크
# - 사용자명: pi / 비밀번호: (팀 공통 비밀번호)
# - WiFi SSID/비밀번호: 현장 WiFi 정보 입력
```

### 1.2 초기 SSH 접속
```bash
# 같은 WiFi에서 접속
ssh pi@bustago-kiosk.local
# 또는 IP로 접속
ssh pi@192.168.x.x
```

---

## 2단계: 기본 환경 설정

```bash
# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y chromium-browser     unclutter     xdotool     python3-pip

# 한국어 폰트 설치 (PWA 텍스트 표시용)
sudo apt install -y fonts-noto-cjk

# 자동 로그인 설정
sudo raspi-config
# → System Options → Boot / Auto Login → Console Autologin
```

---

## 3단계: Chromium Kiosk systemd 서비스 등록

### 3.1 서비스 파일 생성
```bash
sudo nano /etc/systemd/system/bustago-kiosk.service
```

아래 내용 입력 (SERVER_IP를 실제 서버 IP로 변경):

```ini
[Unit]
Description=BUSTAGO Kiosk Browser
After=network.target graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium-browser     --kiosk     --noerrdialogs     --disable-infobars     --no-first-run     --disable-restore-session-state     --disable-session-crashed-bubble     http://SERVER_IP/student/index.html
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

### 3.2 서비스 등록 및 시작
```bash
sudo systemctl daemon-reload
sudo systemctl enable bustago-kiosk.service
sudo systemctl start bustago-kiosk.service

# 상태 확인
sudo systemctl status bustago-kiosk.service
# → Active: active (running) 표시되면 성공
```

---

## 4단계: Kiosk 동작 확인

### 4.1 화면 확인 (7인치 DSI 디스플레이)
- Chromium이 전체 화면으로 PWA 표시
- 정류장 드롭다운 + 혼잡도 카드 표시
- 60초마다 자동 갱신 (화면 깜빡임 없음)

### 4.2 마우스 커서 숨기기
```bash
# unclutter 자동 시작 설정
echo "unclutter -idle 0 -root &" >> /home/pi/.bashrc
```

### 4.3 WiFi 연결 안정성 확인
```bash
# 서버 핑 테스트
ping -c 10 SERVER_IP
# → 패킷 손실 0% 확인

# API 응답 확인
curl "http://SERVER_IP/api/health"
# → {"status":"ok"} 출력되면 성공
```

---

## 5단계: Watchdog Pi 설정

```bash
# watchdog_pi.sh 복사
scp /path/to/bustago/hardware/watchdog_pi.sh pi@bustago-kiosk.local:~/

# 실행 권한 부여
chmod +x ~/watchdog_pi.sh

# crontab 등록
crontab -e
# 아래 줄 추가:
# */2 * * * * /home/pi/watchdog_pi.sh >> /var/log/bustago-watchdog-pi.log 2>&1

# 등록 확인
crontab -l
```

---

## 6단계: 시스템 통합 테스트

> **전제:** Jetson + Pi + 서버 모두 동작 중인 상태

### 6.1 Admin 대시보드 실시간 확인
```bash
# 운영자 PC 브라우저에서:
# http://SERVER_IP/admin/index.html

# 확인 항목:
# [ ] Jetson 연결 상태 표시 (녹색 dot)
# [ ] 대기/IN/BOARD 수치 표시 (10초마다 갱신)
# [ ] 실제 사람이 지나갔을 때 IN 카운트 증가
```

### 6.2 E2E 데이터 흐름 확인
```bash
# 1. Jetson에서 counter.py POST 확인
python3 counter.py --camera 0 --model ~/yolov8n.engine   --server http://SERVER_IP/api/crowd-count   --station-id INS01 --post-interval 10

# 2. 서버 DB에서 데이터 증가 확인 (서버에서 실행)
watch -n 5 'sqlite3 backend/bustago.db "SELECT * FROM crowd_counts ORDER BY created_at DESC LIMIT 3;"'

# 3. Student PWA에서 혼잡도 표시 확인
# → Pi 화면 또는 http://SERVER_IP/student/index.html 에서 INS01 선택

# 4. Admin 대시보드 카운팅 패널 실시간 확인
# → 사람 통과 → IN 증가 → 10초 후 Admin 패널 반영
```

---

## 7단계: 비상 대응 플랜 (시연 당일 대비)

| 상황 | 대응 방법 |
|------|----------|
| Jetson 미도착 / 고장 | `python3 counter.py --camera 0 --model yolov8n.pt --debug` (PC 웹캠) |
| TensorRT 변환 실패 | `.pt` 모델로 대체 (FPS 낮지만 기능 동작) |
| Pi 화면 안 나옴 | 노트북 브라우저로 PWA 직접 접속 대체 |
| WiFi 불안정 | 핫스팟 라우터 + 유선 연결 혼용 |
| 서버 응답 없음 | `python3 backend/app.py` 직접 실행 확인 |
| DB 데이터 없음 | `curl -X POST http://SERVER_IP/api/crowd-count -H "Content-Type: application/json" -d '{"station_id":"INS01","count_in":5,"count_board":3,"current_waiting":2}'` 로 더미 데이터 주입 |

---

## 8단계: 통합 완료 최종 체크리스트

```
Jetson 측:
[ ] JetPack 6.x + CUDA/TensorRT 확인
[ ] Pi Camera /dev/video0 인식
[ ] yolov8n.engine 변환 완료
[ ] counter.py 25+ FPS 확인
[ ] POST /api/crowd-count 10초 간격 200 OK
[ ] DB crowd_counts 증가 확인
[ ] Line Crossing 라인 현장 튜닝 완료
[ ] watchdog_jetson.sh crontab 등록

Pi 측:
[ ] Pi OS 설치 + SSH 접속 성공
[ ] WiFi 서버 연결 확인 (ping 0% 손실)
[ ] bustago-kiosk.service active (running)
[ ] 7인치 DSI 화면에 PWA 표시
[ ] 60초 자동 갱신 동작
[ ] watchdog_pi.sh crontab 등록

통합:
[ ] Admin 대시보드 Jetson 녹색 dot 확인
[ ] 실제 인원 카운팅 → Admin 패널 반영 확인
[ ] Student PWA 혼잡도 4단계 표시 확인
[ ] E2E 시나리오 1회 완주 (진입 → 탑승 → 관리자 확인)
```

---

## 시연 당일 체크리스트 (5/21)

```
시연 1시간 전:
[ ] 서버 실행 확인 (Docker 또는 직접 실행)
[ ] Jetson counter.py 실행 확인
[ ] Admin 대시보드 녹색 dot 확인
[ ] Student PWA 정상 표시 확인
[ ] 비상 더미 데이터 주입 명령어 메모 준비

시연 직전:
[ ] Admin 대시보드 DB 카운트 리셋 (필요 시)
[ ] 브라우저 확대율 100% 설정
[ ] 화면 공유 또는 빔프로젝터 연결 확인
```
---
