"""
BUSTAGO - 기상청 단기예보 API 날씨 데이터 수집
API: VilageFcstInfoService_2.0 / getVilageFcst (공공데이터포털)

[가이드 기준 핵심 정보]
- 서비스 URL: http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst
- 발표 시각(base_time): 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
- 호출 시점: 발표 시각 + 10분 이후부터 가능
- 단기예보 카테고리: POP(강수확률), PTY(강수형태), PCP(1시간강수량),
                    REH(습도), SNO(적설), SKY(하늘상태), TMP(기온),
                    TMN(최저기온), TMX(최고기온), WSD(풍속)
- SKY 코드: 맑음(1), 구름많음(3), 흐림(4)
- PTY 코드(단기): 없음(0), 비(1), 비/눈(2), 눈(3), 소나기(4)
- 격자 좌표: 별첨 엑셀 참조
"""

import requests
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# .env 파일 로드 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# 기상청 API 키
KMA_API_KEY = os.getenv("DATA_GO_KR_API_KEY")
if not KMA_API_KEY:
    raise ValueError("DATA_GO_KR_API_KEY가 .env 파일에 설정되지 않았습니다.")

# 가이드 기준 정확한 엔드포인트 (언더스코어 _2.0)
KMA_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

# 격자 좌표 (별첨 엑셀 기준 정확한 값)
GRID_COORDS = {
    "서울_중구":     {"nx": 60, "ny": 127},   # 명동 — 서울 모델용
    "서울_강남구":   {"nx": 61, "ny": 126},   # 강남역 — 서울 모델용
    "광주_남구":     {"nx": 59, "ny": 73},    # 광주 정문 정류장 — 광주 적용용
}

# 단기예보 발표 시각 (가이드 기준)
BASE_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]


def get_base_time(now=None):
    """
    기상청 단기예보 발표 시각 계산
    발표 시각: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
    실제 API 제공: 발표 시각 + 10분 이후부터 호출 가능 (가이드 기준)
    """
    if now is None:
        now = datetime.now()

    # 10분 보정 (발표 시각 + 10분 이후 호출 가능)
    adjusted = now - timedelta(minutes=10)
    h = adjusted.hour

    valid = [b for b in BASE_HOURS if b <= h]
    if valid:
        base_h = valid[-1]
        base_date = adjusted.strftime("%Y%m%d")
    else:
        # 자정~02:10 사이 → 전날 23시 발표 데이터 사용
        base_h = 23
        base_date = (adjusted - timedelta(days=1)).strftime("%Y%m%d")

    return base_date, f"{base_h:02d}00"


def fetch_weather(nx, ny, base_date=None, base_time=None):
    """
    기상청 단기예보 수집 → 시간대별 날씨 DataFrame 반환

    가이드 기준 요청 인자:
        serviceKey(필수), numOfRows, pageNo, dataType,
        base_date(필수), base_time(필수), nx(필수), ny(필수)

    Returns:
        DataFrame: fcst_date, hour, weather, temperature, rain,
                   rain_prob, humidity, wind_speed, sky, pty
    """
    if base_date is None or base_time is None:
        base_date, base_time = get_base_time()

    params = {
        "serviceKey": KMA_API_KEY,
        "numOfRows": 1000,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    print(f"  요청: {base_date} {base_time} (nx={nx}, ny={ny})")

    try:
        resp = requests.get(KMA_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 응답 코드 확인 (가이드: resultCode '00' = 정상)
        header = data.get("response", {}).get("header", {})
        result_code = header.get("resultCode", "")
        result_msg = header.get("resultMsg", "")

        if result_code != "00":
            print(f"  [ERROR] {result_code} - {result_msg}")
            return pd.DataFrame()

        items = (data.get("response", {})
                     .get("body", {})
                     .get("items", {})
                     .get("item", []))

        if not items:
            print(f"  [WARNING] 데이터 없음")
            return pd.DataFrame()

        df = pd.DataFrame(items)

        # 단기예보 주요 카테고리만 추출
        # TMP:기온, SKY:하늘상태, PTY:강수형태, POP:강수확률, REH:습도, WSD:풍속
        target_cats = ["TMP", "SKY", "PTY", "POP", "REH", "WSD"]
        df = df[df["category"].isin(target_cats)].copy()

        # 시간대별 피벗
        pivot = df.pivot_table(
            index=["fcstDate", "fcstTime"],
            columns="category",
            values="fcstValue",
            aggfunc="first"
        ).reset_index()
        pivot.columns.name = None

        # 컬럼 가공
        pivot["fcst_date"] = pivot["fcstDate"].astype(str)
        pivot["hour"] = pivot["fcstTime"].astype(str).str[:2].astype(int)

        # 안전한 숫자 변환
        pivot["sky"] = pd.to_numeric(pivot.get("SKY", 1), errors="coerce").fillna(1).astype(int)
        pivot["pty"] = pd.to_numeric(pivot.get("PTY", 0), errors="coerce").fillna(0).astype(int)
        pivot["temperature"] = pd.to_numeric(pivot.get("TMP", 15), errors="coerce").fillna(15.0)
        pivot["rain_prob"] = pd.to_numeric(pivot.get("POP", 0), errors="coerce").fillna(0).astype(int)
        pivot["humidity"] = pd.to_numeric(pivot.get("REH", 50), errors="coerce").fillna(50).astype(int)
        pivot["wind_speed"] = pd.to_numeric(pivot.get("WSD", 0), errors="coerce").fillna(0.0)

        # 강수 여부 (0/1)
        pivot["rain"] = (pivot["pty"] > 0).astype(int)

        # 날씨 레이블 (가이드 기준 코드값)
        # SKY: 맑음(1), 구름많음(3), 흐림(4)
        # PTY(단기): 없음(0), 비(1), 비/눈(2), 눈(3), 소나기(4)
        def to_weather(row):
            pty = row["pty"]
            sky = row["sky"]
            if pty in [1, 2, 4]:    # 비, 비/눈, 소나기
                return 2
            if pty == 3:            # 눈
                return 3
            if sky == 1:            # 맑음
                return 0
            return 1                # 구름많음(3) 또는 흐림(4)

        pivot["weather"] = pivot.apply(to_weather, axis=1)

        result = pivot[[
            "fcst_date", "hour", "weather", "temperature", "rain",
            "rain_prob", "humidity", "wind_speed", "sky", "pty"
        ]].copy()

        return result.reset_index(drop=True)

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] API 호출 실패: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  [ERROR] 데이터 처리 중 예외: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")
    output_dir = os.path.join(project_root, "data", "weather")
    os.makedirs(output_dir, exist_ok=True)

    print(f"저장 경로: {os.path.abspath(output_dir)}")
    print(f"API URL: {KMA_URL}\n")

    all_dfs = []

    for loc_name, coords in GRID_COORDS.items():
        print(f"=== {loc_name} 날씨 수집 ===")
        df = fetch_weather(coords["nx"], coords["ny"])

        if df.empty:
            continue

        df["location"] = loc_name
        all_dfs.append(df)

        print(f"  {len(df)}건 수집 완료")
        print(df[["fcst_date", "hour", "weather", "temperature", "rain"]].head(10).to_string(index=False))
        print()

    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)
        today = datetime.now().strftime("%Y%m%d")
        filepath = os.path.join(output_dir, f"weather_{today}.csv")
        df_all.to_csv(filepath, index=False, encoding="utf-8-sig")

        print(f"{'='*50}")
        print(f"저장 완료: weather_{today}.csv ({len(df_all)}건)")
        print(f"\n날씨 분포:")
        weather_labels = {0: "맑음", 1: "흐림", 2: "비", 3: "눈"}
        for code, label in weather_labels.items():
            cnt = len(df_all[df_all["weather"] == code])
            if cnt > 0:
                print(f"  {label}: {cnt}건")
        return df_all

    return pd.DataFrame()


if __name__ == "__main__":
    df = main()