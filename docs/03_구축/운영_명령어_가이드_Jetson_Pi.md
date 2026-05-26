# BUSTAGO 운영 명령어 가이드 — Jetson(백엔드) + Pi(키오스크)

> **용도:** 데모/시연 당일 펼쳐놓고 복붙하는 명령어 카드.
> 모든 명령은 실제 셋업 환경(2026-05-22 검증) 기준. 값이 다르면 §0 표대로 치환.
> 상세 절차·트러블슈팅은 `HW_설치_가이드_Part2_Pi_통합테스트.md` 참고.

---

## 0. 환경 (실측값)

| 구분 | Jetson (백엔드 + AI) | Raspberry Pi (키오스크) |
|------|----------------------|--------------------------|
| 역할 | Flask 백엔드 + `counter.py` AI 카운팅 | Chromium 키오스크(학생 PWA 표시) |
| 사용자 | `amoo` (호스트 `ubuntu`) | `amoo_rp` |
| 접속 | `ssh amoo@172.30.1.75` | `ssh amoo_rp@amoo-rp.local` 또는 VNC |
| 저장소 | `/home/amoo/bustago` (`~/bustago`) | `/home/amoo_rp/bustago` |
| 모델(엔진) | `~/bustago/yolo11n.engine` ← hardware 한 단계 **위** | — |
| 서버 URL | `http://172.30.1.75:5000` (외부) / `http://localhost:5000` (자체) | — |
| 정류장 ID | `INS01` (광주대 인성관) | — |
| 브라우저 | — | `/usr/bin/chromium` (Trixie/Bookworm) |

> **순서가 중요:** ① Jetson 백엔드 → ② Jetson 카운팅 → ③ Pi 키오스크.
> 백엔드가 먼저 떠 있어야 Pi 화면과 카운팅 POST가 동작한다.

---

## A. Jetson — 백엔드 + AI 카운팅

### A-1. 접속 & 최신 코드 동기화
```bash
ssh amoo@172.30.1.75
cd ~/bustago
git checkout develop && git pull origin develop   # ← 반드시 develop
```

### A-2. 백엔드 기동 (터미널 1)
```bash
cd ~/bustago
python3 -m backend.app
# → "Running on http://0.0.0.0:5000" 뜨면 성공. 이 터미널은 켜둔 채로 둔다.
```
> 0.0.0.0 으로 떠야 Pi·노트북이 `172.30.1.75:5000`으로 접근 가능.

### A-3. AI 카운팅 기동 (터미널 2 — 새 SSH 세션)
```bash
cd ~/bustago/hardware
python3 counter.py \
    --camera 0 \
    --model ~/bustago/yolo11n.engine \
    --server http://localhost:5000 \
    --station-id INS01 \
    --post-interval 10
```
- ⚠️ **엔진은 `~/bustago/yolo11n.engine` (hardware 한 단계 위)**. 경로 생략하면 `FileNotFoundError`.
- `.engine` 없으면 `cd ~/bustago && yolo export model=yolo11n.pt format=engine half=True`로 재생성, 또는 `--model yolo11n.pt`로 대체 (느리지만 동작).
- 라인 확인용 화면 띄우려면 끝에 `--debug` 추가 (바운딩박스·세로라인·FPS 표시).
- 로그에 `POST → ...crowd-count (waiting=N)` 주기적으로 찍히면 정상.

### A-4. 동작 확인 (터미널 3)
```bash
curl http://localhost:5000/api/health                    # {"status":"ok"...}
curl "http://localhost:5000/api/crowd-count?station_id=INS01"   # 최신 카운트
sqlite3 ~/bustago/backend/bustago.db \
  "SELECT count_in,count_board,current_waiting,created_at FROM crowd_counts ORDER BY id DESC LIMIT 3;"
```

### A-5. 종료
```bash
# 각 터미널에서 Ctrl+C. 백그라운드로 띄웠다면:
pkill -f counter.py
pkill -f "backend.app"
```

---

## B. Raspberry Pi — 키오스크(학생 PWA)

### B-1. 접속
```bash
ssh amoo_rp@amoo-rp.local      # 또는 VNC로 데스크톱 접속
```

### B-2. 백엔드가 페이지를 주는지 먼저 확인
ping이 돼도 Flask가 떠 있는지는 별개다. **URL은 셸이 아니라 브라우저/`curl`에 넣는다.**
```bash
ping -c 4 172.30.1.75                                  # Jetson 닿는지 (네트워크)
curl -I "http://172.30.1.75:5000/student/index.html"   # 학생 화면 200 인지
curl -I "http://172.30.1.75:5000/admin/"               # 관리자 화면 200 인지
```
- **`HTTP/1.1 200 OK`** → B-3으로.
- **`Connection refused`** → Jetson에서 백엔드 안 떠 있음 → `cd ~/bustago && python3 -m backend.app` 먼저.

### B-3. 화면 바로 띄우기 (수동 — 제일 빠름)
서비스 등록 전에는 이 방법으로 띄운다. **VNC가 아니라 실물 터치스크린(`DISPLAY=:0`)에 뜬다.**
```bash
# 학생 PWA (키오스크용)
DISPLAY=:0 chromium --kiosk --noerrdialogs --disable-infobars \
    --disable-cache --disk-cache-dir=/tmp/chromium-kiosk \
    http://172.30.1.75:5000/student/index.html

# 관리자 대시보드 (운영자 화면)
DISPLAY=:0 chromium --kiosk --noerrdialogs --disable-infobars \
    http://172.30.1.75:5000/admin/
```
끄기: 화면에서 `Alt+F4`, 또는 다른 터미널에서 `pkill chromium`.

### B-4. 자동시작 서비스 (선택 — 무인 운영 시)
> ⚠️ `bustago-kiosk.service`는 **기본으로 없다.** `Unit could not be found`가 뜨면 아직 안 만든 것.
> 만드는 법은 `HW_설치_가이드_Part2_Pi_통합테스트.md` §3 (systemd 서비스 파일) 참고.
> 만든 뒤부터 아래 제어 명령 사용:
```bash
sudo systemctl status  bustago-kiosk.service     # 상태 (active 면 OK)
sudo systemctl restart bustago-kiosk.service     # 화면 새로고침/복구
sudo systemctl stop    bustago-kiosk.service     # 끄기
sudo systemctl start   bustago-kiosk.service     # 켜기
journalctl -u bustago-kiosk.service -n 30 --no-pager   # 최근 로그
```

---

## C. 두 화면 주소 & 노트북 대체

| 화면 | 주소 | 보는 사람 | 내용 |
|------|------|-----------|------|
| 학생 PWA | `http://172.30.1.75:5000/student/index.html` | 이용자 (Pi 키오스크) | 정류장 선택 → 혼잡도 예측 |
| 관리자 | `http://172.30.1.75:5000/admin/` | 운영자 (노트북) | 실시간 카운팅(대기/IN/BOARD) + 지도 + Jetson 연결상태 |

- **관리자 화면**은 키오스크가 아니라 **노트북 브라우저**로 주소창에 직접 입력해 본다.
- **관리자 카운팅 숫자**는 Jetson `counter.py`가 POST를 보내야 채워진다. counter.py 미실행이면 "Jetson 미연결" 표시.
- **Pi 키오스크가 실패하면** 노트북 브라우저로 위 학생 주소를 직접 열면 된다 — 시연 영향 없음.

---

## D. 자주 쓰는 한 줄 (트러블슈팅)

| 증상 | 명령 |
|------|------|
| DB에 데이터가 없다(카메라 없이 시연) | `curl -X POST http://172.30.1.75:5000/api/crowd-count -H "Content-Type: application/json" -d '{"station_id":"INS01","count_in":5,"count_board":3,"current_waiting":2}'` |
| 카운팅이 0에서 안 변함 | counter.py 터미널 로그 확인 → 사람이 **우→좌(IN)** 로 라인을 넘는지 확인 (`--in-line 0.7` 우측) |
| Pi 화면 구버전 캐시 | 서비스 등록 시 `sudo systemctl restart bustago-kiosk.service` / 수동 실행이면 `pkill chromium` 후 B-3 재실행 |
| URL을 셸에 쳐서 `No such file` | URL은 브라우저/`curl` 대상. 셸에 직접 입력하지 말 것 |
| `Unit ...could not be found` | 키오스크 서비스 미생성 → B-3 수동 실행 또는 Part2 §3으로 서비스 생성 |
| 백엔드 외부 접근 불가 | `python3 -m backend.app` 로그에 `0.0.0.0:5000` 인지 확인 (127.0.0.1 이면 외부 차단) |
| Jetson IP 변경됨 | Pi의 `bustago-kiosk.service` 마지막 URL + `watchdog_pi.sh` 갱신 후 `daemon-reload` |

---

## E. (선택) Watchdog 자동복구 — 무인 운영 시
프로세스가 죽으면 cron이 자동 재시작. 데모 중 수동 운영이면 불필요.
```bash
# Jetson
crontab -e
*/5 * * * * /home/amoo/bustago/hardware/watchdog_jetson.sh >> /var/log/bustago-watchdog.log 2>&1
# ⚠️ watchdog_jetson.sh 내부 MODEL 경로는 hardware/ 기준 → 엔진이 상위 폴더이므로
#    스크립트의 --model 줄을 "${SCRIPT_DIR}/../yolo11n.engine" 로 수정 필요

# Pi
crontab -e
*/2 * * * * /home/amoo_rp/bustago/hardware/watchdog_pi.sh >> /var/log/bustago-watchdog-pi.log 2>&1
```
