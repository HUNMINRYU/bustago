---
name: bustago-backend
description: "BUSTAGO Flask Backend 구현 스킬. Flask 앱 구조, MySQL 스키마(stations/predictions/weather_cache), REST API 엔드포인트(/api/predict, /api/stats, /api/stations, /api/weather/current), CORS, 에러 핸들링, requirements.txt. Backend API 서버 구축, DB 설계, REST 엔드포인트 구현 시 반드시 이 스킬을 사용."
---

# BUSTAGO Backend

## Flask 앱 구조

```
backend/
├── app.py              # Flask 앱 팩토리 + 실행
├── config.py           # 설정 (DB, API 키, 모델 경로)
├── routes/
│   ├── __init__.py
│   ├── predict.py      # GET /api/predict
│   ├── stats.py        # GET /api/stats
│   └── stations.py     # GET /api/stations, GET /api/weather/current
├── models/
│   ├── __init__.py
│   └── db.py           # MySQL/SQLite 연결 헬퍼
├── schema.sql          # DDL
└── requirements.txt
```

## MySQL 스키마 (schema.sql)

```sql
CREATE TABLE stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ars_no VARCHAR(10) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7)
);

CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_ars_no VARCHAR(10) NOT NULL,
    hour TINYINT NOT NULL,
    weekday TINYINT NOT NULL,
    predicted_level TINYINT NOT NULL,
    predicted_label VARCHAR(20) NOT NULL,
    probabilities JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_ars_no) REFERENCES stations(ars_no)
);

CREATE TABLE weather_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(50) NOT NULL,
    hour TINYINT NOT NULL,
    weather TINYINT,
    temperature DECIMAL(4,1),
    rain TINYINT,
    humidity TINYINT,
    wind_speed DECIMAL(4,1),
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API 엔드포인트

### GET /api/predict
- 파라미터: station_id (ARS번호, 필수), hour (0-23, 필수), weekday (0-6, 선택)
- 응답:
```json
{
  "status": "ok",
  "data": {
    "station_id": "22011",
    "station_name": "지하철2호선강남역",
    "hour": 8,
    "prediction": {
      "level": 2,
      "label": "혼잡",
      "probabilities": [0.1, 0.2, 0.5, 0.2]
    },
    "recommendation": "혼잡이 예상됩니다. 다음 시간대를 추천합니다.",
    "next_hour_prediction": { "level": 1, "label": "보통" }
  },
  "timestamp": "2026-03-29T14:00:00"
}
```

### GET /api/stats
- 파라미터: station_id (필수), period (today|week|month, 기본 today)
- 응답: 시간대별 평균 혼잡도 배열

### GET /api/stations
- 파라미터: 없음
- 응답: 정류장 목록 [{ars_no, station_name, latitude, longitude}]

### GET /api/weather/current
- 파라미터: 없음
- 응답: 현재 날씨 정보 (기상청 API 프록시)

## 에러 응답 형식
```json
{ "status": "error", "message": "station_id is required", "code": 400 }
```

## 모델 연동 패턴
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ml.models.predict import predict_congestion
```

## requirements.txt
```
flask>=3.0
flask-cors>=4.0
pymysql>=1.1
python-dotenv>=1.0
joblib>=1.3
pandas>=2.0
numpy>=1.24
```

## API 계약서
구현 완료 후 _workspace/02_api_contract.json에 모든 엔드포인트의 URL, 메서드, 파라미터, 응답 shape을 저장한다.
