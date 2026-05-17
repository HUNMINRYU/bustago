# BUSTAGO Hardware - AI People Counter

Jetson Orin Nano에서 실행되는 YOLOv11 + DeepSORT 기반 인원 카운팅 스크립트.

## 구성

```
hardware/
├── counter.py              # 메인 카운팅 스크립트 (YOLOv11 + DeepSORT + Line Crossing)
├── watchdog_jetson.sh      # Jetson counter.py 프로세스 감시·자동 재시작 (crontab: */5분)
├── watchdog_pi.sh          # Pi Chromium Kiosk 프로세스 감시·자동 재시작 (crontab: */2분)
├── requirements.txt        # Python 의존성
└── README.md
```

## 실행 방법

### PC 웹캠 테스트

```bash
pip install -r requirements.txt
python counter.py --camera 0 --model yolo11n.pt --debug
```

### Jetson 배포

```bash
# 1) YOLOv11-nano → TensorRT FP16 변환 (최초 1회)
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='engine', half=True)"

# 2) 카운팅 실행
python counter.py \
  --camera 0 \
  --model yolo11n.engine \
  --server http://SERVER_IP/api/crowd-count \
  --station-id INS01
```

## CLI 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--camera` | 0 | 카메라 인덱스 또는 RTSP URL |
| `--model` | yolo11n.pt | YOLOv11 모델 (.pt 또는 .engine) |
| `--conf` | 0.5 | YOLO confidence 임계값 |
| `--in-line` | 0.7 | IN 라인 y 비율 (정류장 진입) |
| `--board-line` | 0.3 | BOARD 라인 y 비율 (버스 탑승) |
| `--server` | http://localhost:5000 | Backend URL |
| `--station-id` | INS01 | 정류장 ID |
| `--post-interval` | 10 | API POST 주기 (초) |
| `--debug` | off | 화면에 bbox/라인/FPS 표시 |
