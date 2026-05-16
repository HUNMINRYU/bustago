---
# HW 설치 가이드 Part 1 — Jetson Orin Nano 설정

> 작성일: 2026-05-01 | 담당: 류훈민
> 전제: 부품 수령 완료 상태에서 시작

---

## 0. 사전 준비 (부품 수령 즉시 확인)

### 0.1 부품 체크리스트
| # | 부품 | 수량 | 확인 |
|---|------|------|------|
| 1 | Jetson Orin Nano 8GB 모듈 | 1 | [ ] |
| 2 | Carrier Board (Developer Kit 또는 상용 보드) | 1 | [ ] |
| 3 | Pi Camera v2 (8MP IMX219) | 1 | [ ] |
| 4 | CSI 리본 케이블 (15핀→22핀 변환, 60cm) | 1 | [ ] |
| 5 | 전원 어댑터 (DC 9~19V, 5A 이상) | 1 | [ ] |
| 6 | MicroSD 카드 64GB 이상 (JetPack용) 또는 eMMC | 1 | [ ] |
| 7 | WiFi 안테나 (M.2 Key E 또는 USB WiFi) | 1 | [ ] |

> 부족 부품 발견 시 즉시 박건우에게 보고 후 추가 구매 진행

---

## 1단계: JetPack 6.x 설치

### 1.1 방법 선택
**권장: SDK Manager 사용 (PC에서 플래싱)**

```bash
# Ubuntu 22.04 PC에서 실행
# NVIDIA SDK Manager 설치 후:
# 1. Jetson → Developer Tools → JetPack 6.x 선택
# 2. Jetson Orin Nano 연결 (USB-C OTG 모드)
# 3. Flash 실행 (약 20~30분)
```

**대안: 사전 플래시된 이미지 사용**
- NVIDIA 공식 Jetson Orin Nano Developer Kit 이미지 다운로드
- Balena Etcher로 SD카드에 플래싱

### 1.2 초기 부팅 설정
```bash
# 화면 연결 후 언어/계절 설정
# 사용자명: bustago
# 비밀번호: (팀 공통 비밀번호 — 팀장에게 문의)
# 자동 로그인: 활성화 (키오스크 운용)
```

### 1.3 JetPack 설치 확인
```bash
# 터미널에서 실행
jetson_release   # JetPack 버전 확인

# jtop 설치 및 확인 (GPU/CUDA/TensorRT 상태)
sudo pip3 install jetson-stats
sudo jtop
# → GPU 사용률, CUDA 버전, TensorRT 버전 표시되면 성공
```

**성공 기준:**
- JetPack 6.x 버전 표시
- CUDA 12.x 표시
- TensorRT 버전 표시

---

## 2단계: Python 환경 및 의존성 설치

```bash
# 가상환경 생성
cd ~
python3 -m venv bustago-env
source bustago-env/bin/activate

# ultralytics (YOLOv11) 설치 — JetPack 용 특별 절차
pip install --upgrade pip
pip install ultralytics

# 나머지 의존성
pip install deep-sort-realtime opencv-python requests numpy

# 설치 확인
python3 -c "from ultralytics import YOLO; print('YOLOv11 OK')"
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
```

---

## 3단계: Pi Camera v2 연결 및 확인

### 3.1 물리적 연결
```
Jetson CSI 포트 (CAM0) ← CSI 리본 케이블 (22핀 측) ← 변환 커넥터 ← Pi Camera (15핀 측)
```
> **주의:** 케이블 방향 확인 필수. 파란 면이 커넥터 잠금 방향 기준.

### 3.2 카메라 인식 확인
```bash
# V4L2 드라이버 확인
ls /dev/video*
# → /dev/video0 표시되면 성공

# 카메라 테스트 (5초 캡처)
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print('Camera OK:', ret, frame.shape if ret else 'FAIL')
cap.release()
"
```

---

## 4단계: YOLOv11-nano TensorRT FP16 변환

```bash
# 모델 다운로드 + 변환 (최초 1회, 약 5~10분)
source ~/bustago-env/bin/activate
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')  # 자동 다운로드
model.export(format='engine', half=True, imgsz=640)
print('TensorRT 엔진 변환 완료: yolo11n.engine')
"

# 변환 확인
ls -lh yolo11n.engine
# → 파일 크기 약 5~15MB면 성공

# TensorRT 추론 테스트
python3 -c "
from ultralytics import YOLO
model = YOLO('yolo11n.engine')
import cv2, numpy as np
dummy = np.zeros((640, 640, 3), dtype=np.uint8)
result = model(dummy)
print('TensorRT 추론 OK, 클래스 수:', len(result[0].boxes))
"
```

---

## 5단계: BUSTAGO 코드 배포

```bash
# 리포지토리 클론 또는 파일 복사
git clone https://github.com/HUNMINRYU/bustago.git ~/bustago
cd ~/bustago/hardware

# 또는 USB/SCP로 counter.py, requirements.txt 복사
# scp user@PC_IP:/path/to/bustago/hardware/counter.py ~/bustago/hardware/
```

---

## 6단계: counter.py 실행 확인

### 6.1 디버그 모드 (화면 표시)
```bash
cd ~/bustago/hardware
source ~/bustago-env/activate

# 디버그 모드 — 화면에 bbox/라인/FPS 표시
python3 counter.py \
  --camera 0 \
  --model ~/yolo11n.engine \
  --debug
```

**성공 기준:**
- 터미널에 FPS 출력: `FPS: 25~40` 이상
- 화면에 초록 bbox + IN/BOARD 라인 표시

### 6.2 서버 연동 모드
```bash
# SERVER_IP를 실제 서버 IP로 변경
python3 counter.py \
  --camera 0 \
  --model ~/yolo11n.engine \
  --server http://SERVER_IP/api/crowd-count \
  --station-id INS01 \
  --post-interval 10
```

**성공 기준:**
- 10초마다 터미널에 `POST 200 OK` 출력
- 서버 DB 확인: `sqlite3 backend/bustago.db "SELECT * FROM crowd_counts ORDER BY created_at DESC LIMIT 3;"`

---

## 7단계: Line Crossing 라인 현장 튜닝

> **전제:** 카메라 현장 설치 완료 후 진행

### 7.1 현재 기본값
```
IN 라인: y=0.7 (화면 높이의 70% — 진입 감지)
BOARD 라인: y=0.3 (화면 높이의 30% — 탑승 감지)
```

### 7.2 튜닝 방법
```bash
# 디버그 모드로 현장 영상 확인
python3 counter.py --camera 0 --model ~/yolo11n.engine --debug

# 실제 사람 통과 위치 보면서 라인 조정
python3 counter.py \
  --camera 0 \
  --model ~/yolo11n.engine \
  --in-line 0.65 \
  --board-line 0.35 \
  --debug

# 적절한 값 찾으면 watchdog_jetson.sh에 해당 값 추가
```

### 7.3 확인 방법
- 실제 진입자가 IN 라인 통과 시 카운트 1 증가 확인
- 동일 인물 재통과 시 카운트 증가 없음 (Track ID 재사용 방지) 확인

---

## 8단계: Watchdog 설정

```bash
# watchdog_jetson.sh 내 SERVER_IP 수정
nano ~/bustago/hardware/watchdog_jetson.sh
# → SERVER_IP="192.168.x.x" 로 변경

chmod +x ~/bustago/hardware/watchdog_jetson.sh

# crontab 등록
crontab -e
# 아래 줄 추가:
# */5 * * * * /home/bustago/bustago/hardware/watchdog_jetson.sh >> /var/log/bustago-watchdog.log 2>&1

# 등록 확인
crontab -l
```

### Watchdog 동작 테스트
```bash
# counter.py 강제 종료
pkill -f counter.py

# 5분 대기 후 로그 확인
tail -f /var/log/bustago-watchdog.log
# → "[JETSON] 재시작" 메시지 + PID 출력 확인
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| FPS < 10 | TensorRT 미적용 | `.pt` 모델 사용 중인지 확인, `.engine`으로 전환 |
| 카메라 /dev/video0 없음 | CSI 케이블 연결 불량 | 케이블 재삽입 (방향 확인) |
| TensorRT 변환 실패 | CUDA 메모리 부족 | Jetson 재부팅 후 재시도 |
| POST 실패 (Connection refused) | 서버 IP 오류 또는 서버 미실행 | `ping SERVER_IP` 확인 → Flask 실행 확인 |
| 중복 카운팅 발생 | FPS 낮아 Track ID 끊김 | TensorRT 사용 확인, confidence 임계값 0.5 유지 |

---

## 완료 체크리스트

```
[ ] JetPack 6.x 설치 및 jtop CUDA/TensorRT 확인
[ ] Pi Camera v2 /dev/video0 인식 확인
[ ] yolo11n.engine 변환 완료
[ ] counter.py --debug 모드 25+ FPS 확인
[ ] 서버 POST 10초 간격 200 OK 확인
[ ] DB crowd_counts 증가 확인
[ ] 라인 현장 튜닝 완료
[ ] watchdog_jetson.sh crontab 등록 및 자동 재시작 확인
```
