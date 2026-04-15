-- BUSTAGO MySQL Schema

CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ars_no VARCHAR(10) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_ars_no VARCHAR(10) NOT NULL,
    hour TINYINT NOT NULL,
    weekday TINYINT NOT NULL,
    predicted_level TINYINT NOT NULL,
    predicted_label VARCHAR(20) NOT NULL,
    probabilities JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (station_ars_no) REFERENCES stations(ars_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS weather_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(50) NOT NULL,
    hour TINYINT NOT NULL,
    weather TINYINT,
    temperature DECIMAL(4,1),
    rain TINYINT,
    humidity TINYINT,
    wind_speed DECIMAL(4,1),
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS crowd_counts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_id VARCHAR(10) NOT NULL,
    count_in INT NOT NULL DEFAULT 0,
    count_board INT NOT NULL DEFAULT 0,
    current_waiting INT NOT NULL DEFAULT 0,
    source VARCHAR(20) DEFAULT 'jetson',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 초기 데이터: 샘플 정류장
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude) VALUES
('22011', '지하철2호선강남역', 37.4979502, 127.0276368),
('22012', '강남역12번출구', 37.4985440, 127.0285530),
('23115', '서울역버스환승센터', 37.5546788, 126.9706069),
('21148', '광화문광장앞', 37.5713680, 126.9774430),
('22341', '잠실역', 37.5133890, 127.1001510);
