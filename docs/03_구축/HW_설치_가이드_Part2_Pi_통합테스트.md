---
# HW 설치 가이드 Part 2 — Raspberry Pi 4 설정 + 통합 테스트

> **버전:** 1.1 (2026-05-22 갱신)
> 작성일: 2026-05-01 | 담당: 이건영 (Pi), 이트겔 (서버/통합), 류훈민 (통합 확인)
> 전제: Part 1 Jetson 설정 완료 상태에서 시작 (counter.py 단독 동작 검증됨)

---

## ⚠️ 2026-05-22 현황 (D-13)

- **Pi 셋업 진행됨 (수동 실행 동작 확인).** 6/4 경진대회까지 13일.
- **백엔드 구성**: 5/22 결정으로 백엔드를 **Jetson 자체에서 구동**한다 (별도 서버 X).
  → 본 가이드의 `SERVER_IP`는 **Jetson IP**(현재 `172.30.1.75`, 포트 `5000`)이다.
  → Pi와 Jetson은 **같은 WiFi**에 있어야 한다.
- **Pi 없이 시연 가능 여부**: 노트북 브라우저로 Student PWA를 띄우면 동일 동작.
  Pi는 "정류장 키오스크" 컨셉을 물리적으로 보여주는 역할이지 데이터 흐름엔 안 들어감(§9).

### 실 셋업 환경 (5/22 진행분 — 가이드 기본값과 다른 부분)

| 항목 | 가이드 기본값 | **실제 셋업값** (이게 진실) |
|---|---|---|
| 호스트명 | `bustago-kiosk` | `amoo-rp` |
| 사용자명 | `pi` | `amoo_rp` |
| 홈 디렉터리 | `/home/pi` | `/home/amoo_rp` |
| OS | Bookworm 가정 | **Debian 13 Trixie** (Bookworm 이후) |
| 브라우저 패키지 | `chromium-browser` (구) | **`chromium`** |
| 브라우저 경로 | `/usr/bin/chromium-browser` | **`/usr/bin/chromium`** |
| 저장소 클론 경로 | `/home/pi/bustago` | **`/home/amoo_rp/bustago`** |
| 저장소 브랜치 | (기본) main | **`develop`** (5/22 수정사항 포함) |
| Jetson 백엔드 URL | `http://SERVER_IP/...` | **`http://172.30.1.75:5000/...`** |
| 추가 설치 패키지 | — | **`fonts-noto-color-emoji`** (이모지 폰트) |

> 아래 모든 명령은 위 실제 셋업값 기준으로 정정됨. 다른 팀이 다른 환경으로 셋업하면 위 표를 참고해 치환할 것.

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

# 필수 패키지 설치 (Bookworm 기준 — chromium-browser → chromium)
sudo apt install -y \
    chromium \
    unclutter \
    xdotool \
    xserver-xorg \
    x11-xserver-utils \
    xinit \
    openbox \
    fonts-noto-cjk \
    git \
    python3-pip

# OS 버전 확인 (Bookworm/Bullseye 구분)
cat /etc/os-release | grep VERSION_CODENAME
# → bookworm: chromium (위 명령 그대로)
# → bullseye 이전: 'chromium' 대신 'chromium-browser'로 교체 필요

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

**아래는 5/22 셋업한 실제 환경(`amoo_rp`)에 맞춘 서비스 파일.** 다른 환경이면 §0 표대로 치환.

```ini
[Unit]
Description=BUSTAGO Kiosk Browser
After=network.target graphical.target

[Service]
Type=simple
User=amoo_rp
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/amoo_rp/.Xauthority
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --disable-restore-session-state \
    --disable-session-crashed-bubble \
    --disable-cache \
    --disk-cache-dir=/tmp/chromium-kiosk \
    http://172.30.1.75:5000/student/index.html
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

> `--disable-cache`는 5/22 PWA 코드 변경(광주 정류장 우선·반응형) 후 구버전 캐시
> 묻어나오는 것 방지. 운영 안정화되면 빼도 됨.

> Jetson IP가 바뀌면 이 파일의 마지막 URL과 `watchdog_pi.sh` 안의 `SERVICE` 환경도 함께 갱신.
> Jetson 측 백엔드는 **`host="0.0.0.0"`**로 떠야 외부 접근 가능 (Flask `app.run` 또는 `python3 -m backend.app` 기본값으로 OK).
> **Bookworm 이상은 `/usr/bin/chromium`, Bullseye 이하는 `/usr/bin/chromium-browser`.** `which chromium`으로 사전 확인.

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
# Jetson 핑 테스트 (Jetson IP로 — 위 §3.1에서 확인한 값)
ping -c 10 172.30.1.75
# → 패킷 손실 0% 확인

# API 응답 확인
curl "http://172.30.1.75:5000/api/health"
# → {"status":"ok"} 출력되면 성공

# 만약 실패하면: Jetson 측 백엔드가 0.0.0.0으로 떠있는지, 같은 WiFi인지,
# 방화벽이 5000번 포트 막고 있지 않은지 순서대로 확인
```

---

## 5단계: Watchdog Pi 설정

> ⚠️ **2026-05-22 수정 반영**: `watchdog_pi.sh`의 `chromium-browse` 오타가 수정됐다
> (`chromium-browser`로). 반드시 **최신 develop 브랜치**에서 받을 것 — 구버전을
> 받으면 키오스크가 2분마다 재시작된다.

```bash
# 옵션 A: Jetson에서 clone 받은 저장소에서 직접 복사 (같은 WiFi 전제)
scp ahble@172.30.1.75:~/bustago/hardware/watchdog_pi.sh pi@bustago-kiosk.local:~/

# 옵션 B: Pi가 인터넷 되면 git clone으로 직접 가져오기 (권장)
ssh pi@bustago-kiosk.local
git clone https://github.com/HUNMINRYU/bustago.git ~/bustago
ls ~/bustago/hardware/watchdog_pi.sh
# 검증: 11행이 chromium-browser인지 확인
grep "chromium-browser" ~/bustago/hardware/watchdog_pi.sh
# → chromium-browser가 보이면 OK. chromium-browse(끝 r 없음)면 구버전 → git pull

# 실행 권한 부여
chmod +x ~/bustago/hardware/watchdog_pi.sh

# crontab 등록
crontab -e
# 아래 줄 추가 (경로 주의):
# */2 * * * * /home/pi/bustago/hardware/watchdog_pi.sh >> /var/log/bustago-watchdog-pi.log 2>&1

# 등록 확인
crontab -l
```

---

## 6단계: 시스템 통합 테스트

> **전제:** Jetson (백엔드 + counter.py) + Pi 모두 같은 WiFi에서 동작 중.
> 5/22 결정으로 별도 서버 없이 백엔드는 Jetson에서 구동.

### 6.1 Admin 대시보드 실시간 확인
```bash
# 운영자 노트북 브라우저에서 (Jetson IP):
# http://172.30.1.75:5000/admin/

# 확인 항목:
# [ ] Jetson 연결 상태 표시 (녹색 dot)
# [ ] 대기/IN/BOARD 수치 표시 (10초마다 갱신)
# [ ] 실제 사람이 지나갔을 때 IN 카운트 증가
# [ ] 광주대 지도 표시 (서울 강남 아님 — 5/22 수정 반영 확인)
```

### 6.2 E2E 데이터 흐름 확인
```bash
# 1. Jetson에서 백엔드 + counter.py 동시 실행
#    (터미널 2개 또는 tmux/screen)
ssh ahble@172.30.1.75
# Tmux 권장:
tmux new -s bustago
# 창 1
cd ~/bustago && python3 -m backend.app
# Ctrl+B → " (가로 분할)
cd ~/bustago/hardware && python3 counter.py \
    --camera 0 --model yolo11n.pt \
    --server http://localhost:5000/api/crowd-count \
    --station-id INS01 --post-interval 10 --debug

# 2. Jetson DB에서 데이터 증가 확인 (별도 SSH)
ssh ahble@172.30.1.75
watch -n 5 'sqlite3 ~/bustago/backend/bustago.db "SELECT * FROM crowd_counts ORDER BY created_at DESC LIMIT 3;"'

# 3. Student PWA에서 혼잡도 표시 확인
# → Pi 화면 또는 http://172.30.1.75:5000/student/index.html 에서 INS01 선택

# 4. Admin 대시보드 카운팅 패널 실시간 확인
# → 사람 통과 → IN 증가 → 10초 후 Admin 패널 반영
```

---

## 7단계: 비상 대응 플랜 (시연 당일 대비)

| 상황 | 대응 방법 |
|------|----------|
| Jetson 미도착 / 고장 | `python3 counter.py --camera 0 --model yolo11n.pt --debug` (PC 웹캠) |
| TensorRT 변환 실패 | `.pt` 모델로 대체 (FPS 낮지만 기능 동작) |
| Pi 화면 안 나옴 | 노트북 브라우저로 `http://172.30.1.75:5000/student/index.html` 직접 접속 대체 |
| WiFi 불안정 | 모바일 핫스팟 라우터 (Jetson·Pi·노트북 모두 같은 핫스팟에) |
| 백엔드 응답 없음 | Jetson에서 `python3 -m backend.app` 직접 실행 확인. 포트 5000 열림 확인: `curl http://localhost:5000/api/health` |
| DB 데이터 없음 | `curl -X POST http://172.30.1.75:5000/api/crowd-count -H "Content-Type: application/json" -d '{"station_id":"INS01","count_in":5,"count_board":3,"current_waiting":2}'` |

---

## 8단계: 통합 완료 최종 체크리스트

```
Jetson 측:
[ ] JetPack 6.x + CUDA/TensorRT 확인
[ ] Pi Camera /dev/video0 인식
[ ] yolo11n.engine 변환 완료
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

## 9단계: Pi 미연결 폴백 시나리오 (현실)

Pi 셋업이 시연 일정 안에 끝나지 않거나, 발표 형식이 **부스/판넬형(노트북 시연)**이면
Pi는 *없어도 시스템은 동일하게 동작한다.*

### 9.1 Pi 역할의 본질
| 컴포넌트 | 책임 | Pi 미연결 영향 |
|---|---|---|
| Jetson + 카메라 | 카운팅 → POST | **0%** — 자체 동작 |
| Backend (Jetson) | DB · API | **0%** — Pi 의존 없음 |
| ML 예측 | RandomForest | **0%** — Pi 의존 없음 |
| Student PWA 표시 | 브라우저 한 개 | Pi 대신 **노트북 브라우저**로 대체 가능 |
| Admin 대시보드 | 노트북에서 봄 | Pi 의존 없음 |

→ Pi는 "현장 정류장 사이니지"이지 시스템 핵심이 아니다.

### 9.2 발표 시 멘트 (Pi 미연결인 경우)
> "키오스크 H/W는 **포트폴리오용 구조 결정 포인트**입니다. 실제 셋업은 광주대 현장
> 설치 단계에서 진행 예정이고, 오늘 시연은 노트북 브라우저로 Student PWA를 띄워서
> Pi 키오스크와 **동일한 사용자 경험**을 보여드립니다 — Pi든 노트북이든 같은 PWA를
> 같은 백엔드에서 받습니다."

### 9.3 노트북 폴백 셋업
```bash
# 노트북에서 (어떤 OS든):
# Jetson과 같은 WiFi 접속 확인
ping 172.30.1.75

# 브라우저 전체화면(F11)으로 PWA 띄우기
# Chrome/Edge → 주소창에 입력 → F11
http://172.30.1.75:5000/student/index.html

# 시연 후 Admin 화면도 같은 브라우저 새 탭으로:
http://172.30.1.75:5000/admin/
```

이 구성으로 6/4 라이브 시연은 **100% 가능**하다. Pi는 "있으면 더 좋은 사이니지"이지
필수 의존성이 아니다.

---

## 시연 당일 체크리스트 (6/4 경진대회)

```
시연 1시간 전:
[ ] Jetson 부팅 + WiFi 연결 확인 (`ip addr show wlan0`)
[ ] Jetson에서 백엔드 실행: `cd ~/bustago && python3 -m backend.app`
[ ] curl http://localhost:5000/api/health → status ok
[ ] Jetson에서 counter.py 실행 (--debug 모드, IN/BOARD 라인 위치 OK 확인)
[ ] 노트북 브라우저로 http://<Jetson IP>:5000/admin/ 접속 → 녹색 dot 확인
[ ] Student PWA: http://<Jetson IP>:5000/student/index.html → INS01 선택 → 혼잡도 표시
[ ] (Pi 사용 시) Pi systemctl status bustago-kiosk → active
[ ] 비상 더미 데이터 주입 명령어 메모/터미널 히스토리 준비

시연 직전:
[ ] (필요 시) Admin DB 카운트 리셋: `sqlite3 ~/bustago/backend/bustago.db "DELETE FROM crowd_counts WHERE station_id='INS01';"`
[ ] 브라우저 확대율 100% 설정
[ ] 화면 공유 또는 빔프로젝터 연결 확인 (특히 HDMI/USB-C 어댑터)
[ ] 모바일 핫스팟 백업 준비 (현장 WiFi 불안 대비)
[ ] 사전 녹화 시연 영상 1세트 (노트북 / USB) 보관
```

---

## 변경 이력

| 일자 | 버전 | 변경 |
|------|------|------|
| 2026-05-01 | v1.0 | 초안 (이건영 작성) |
| 2026-05-22 | v1.1 | 백엔드 Jetson 자체 구동으로 변경 반영 (`SERVER_IP` → Jetson IP 명시), `watchdog_pi.sh` 오타 수정 반영, §9 Pi 미연결 폴백 시나리오 추가, 시연 체크리스트 6/4용으로 갱신 |

---
