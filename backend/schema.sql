-- BUSTAGO MySQL Schema

CREATE TABLE IF NOT EXISTS stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ars_no VARCHAR(10) UNIQUE NOT NULL,
    station_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    gj_busstop_id INT DEFAULT NULL  -- 광주 BIS API용 정류소 번호 (NULL이면 서울/셔틀)
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

-- 2026-05-17 단순화 C: weather_cache 테이블 제거.
-- RF feature에서 weather/temperature 빠졌고 frontend·backend 모두 호출 0건이라 정리.
-- 기존 DB에 weather_cache가 있어도 영향 X (참조하는 코드 없음).

CREATE TABLE IF NOT EXISTS crowd_counts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_id VARCHAR(10) NOT NULL,
    count_in INT NOT NULL DEFAULT 0,
    count_board INT NOT NULL DEFAULT 0,
    current_waiting INT NOT NULL DEFAULT 0,
    source VARCHAR(20) DEFAULT 'jetson',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 광주대학교 정류장 (셔틀 + 시내버스)
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude, gj_busstop_id) VALUES
('INS01',  '광주대 인성관 (셔틀)',    35.1377000, 126.8930000, NULL),
('GATE01', '광주대 정문 (시내버스)', 35.1380000, 126.8955000, 1981);

-- 광주 BIS 실제 정류장 (captest/bus_server.py에서 확인, gj_bis arriveInfo 호출용)
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude, gj_busstop_id) VALUES
('GJ3230', '광주대 (3230)', 35.1380000, 126.8956000, 1981),
('GJ3229', '광주대 (3229)', 35.1378000, 126.8954000, 80),
('GJ3228', '광주대입구 (3228)', 35.1370000, 126.8940000, 3219);

-- 시연용 정류장 (광주대 좌표와 동일 — 지도 동일점에 찍힘)
INSERT IGNORE INTO stations (ars_no, station_name, latitude, longitude) VALUES
('DEMO01', '시연용 정류장 (광주대)', 35.1378, 126.8942);

-- 노선 테이블 (route-recommend API용)
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY,
    route_no VARCHAR(20) NOT NULL UNIQUE,  -- UNIQUE → INSERT OR IGNORE 멱등 보장
    route_name VARCHAR(100) NOT NULL,
    start_station_id VARCHAR(10) NOT NULL,
    end_stations TEXT NOT NULL,
    route_count INTEGER DEFAULT 5,
    is_shuttle INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO routes
    (route_no, route_name, start_station_id, end_stations, route_count, is_shuttle) VALUES
('419',     '419번 (광주역행)', 'GATE01', '["광주역","충장로","금남로"]', 8, 0),
('518',     '518번 (금남로행)', 'GATE01', '["금남로","충장로","광주대입구"]', 7, 0),
('SHUTTLE1','셔틀 1호차', 'INS01', '["정문"]', 2, 1),
('SHUTTLE2','셔틀 2호차', 'INS01', '["정문"]', 2, 1),
('SHUTTLE3','셔틀 3호차', 'GATE01', '["인성관"]', 2, 1),
('SHUTTLE4','셔틀 4호차', 'GATE01', '["인성관"]', 2, 1),
('SHUTTLE5','셔틀 5호차', 'INS01', '["정문"]', 2, 1),
('SHUTTLE6','셔틀 6호차', 'INS01', '["정문"]', 2, 1);
