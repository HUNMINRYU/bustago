"""
BUSTAGO - 수집 데이터 결합 및 Feature DataFrame 구축
승하차 이력 + 기상 데이터 → Random Forest 학습용 데이터셋
"""

import pandas as pd
import numpy as np
import os
import glob


def load_boarding_data(data_dir):
    """승하차 데이터 로드 (boarding_all.csv 또는 월별 CSV 통합)"""
    all_path = os.path.join(data_dir, "boarding_all.csv")

    if os.path.exists(all_path):
        df = pd.read_csv(all_path, encoding="utf-8-sig")
        print(f"[승하차] boarding_all.csv 로드: {len(df):,}건")
    else:
        files = glob.glob(os.path.join(data_dir, "boarding_*.csv"))
        dfs = [pd.read_csv(f, encoding="utf-8-sig") for f in files]
        df = pd.concat(dfs, ignore_index=True)
        print(f"[승하차] {len(files)}개 파일 통합: {len(df):,}건")

    return df


def load_weather_data(data_dir):
    """기상 데이터 로드 (가장 최근 파일)"""
    files = sorted(glob.glob(os.path.join(data_dir, "weather_*.csv")))

    if not files:
        print("[기상] 데이터 파일 없음 — 기본값으로 대체")
        return pd.DataFrame()

    df = pd.read_csv(files[-1], encoding="utf-8-sig")
    print(f"[기상] {os.path.basename(files[-1])} 로드: {len(df):,}건")
    return df


def create_congestion_label(df):
    """
    승차 인원 기준으로 혼잡도 4단계 라벨 생성
    정류장별 시간대별 총 승차량의 분위수(quartile) 기준

    0: 여유 (하위 25%)
    1: 보통 (25~50%)
    2: 혼잡 (50~75%)
    3: 매우혼잡 (상위 25%)
    """
    # 정류장별 시간대별 총 승차량 집계
    agg = df.groupby(["stops_ars_no", "hour"]).agg(
        total_boarding=("boarding", "sum"),
        total_alighting=("alighting", "sum"),
    ).reset_index()

    # 정류장별 분위수 기반 라벨 부여
    labels = []
    for station_id, group in agg.groupby("stops_ars_no"):
        q25 = group["total_boarding"].quantile(0.25)
        q50 = group["total_boarding"].quantile(0.50)
        q75 = group["total_boarding"].quantile(0.75)

        for idx, row in group.iterrows():
            val = row["total_boarding"]
            if val <= q25:
                labels.append(0)
            elif val <= q50:
                labels.append(1)
            elif val <= q75:
                labels.append(2)
            else:
                labels.append(3)

    agg["label"] = labels

    print(f"\n[라벨] 혼잡도 분포:")
    label_names = {0: "여유", 1: "보통", 2: "혼잡", 3: "매우혼잡"}
    for label, name in label_names.items():
        cnt = len(agg[agg["label"] == label])
        print(f"  {name}: {cnt}건")

    return agg


def build_feature_dataframe(df_boarding, df_weather=None):
    """
    최종 학습용 Feature DataFrame 구축

    Features (2026-05-16 갱신, weekday 제거):
        hour, weather, temperature, rain,
        prev_boarding, prev_alighting, route_count, boarding, alighting
    Label:
        label (0=여유, 1=보통, 2=혼잡, 3=매우혼잡)

    Note:
        서울 공공데이터(use_month 단위 월별 집계)에는 요일 정보가 없다.
        원본 weekday 컬럼이 -1로 채워져 있고 과거 build_features.py는
        hour < 12 → 0, else 2 placeholder로 덮어썼는데 이는 의미 없는 신호였다.
        2026-05-16 진단 P0 반영으로 weekday feature 자체를 제거.
        광주대 자체 카운팅 데이터에 실제 요일이 확보되면 별도 학습 트랙에서 부활.
    """

    # 1. 혼잡도 라벨 생성
    df_label = create_congestion_label(df_boarding)

    # 2. 승하차 데이터에 라벨 병합
    df = df_boarding.merge(
        df_label[["stops_ars_no", "hour", "label"]],
        on=["stops_ars_no", "hour"],
        how="left"
    )

    # 3. weekday 제거: 원본 데이터에 요일 정보 없음 (모두 -1).
    # 이전 코드의 hour 기반 placeholder는 의미 없는 신호 → 진단 P0로 제거.
    if "weekday" in df.columns:
        df = df.drop(columns=["weekday"])

    # 4. 기상 데이터 결합
    if df_weather is not None and not df_weather.empty:
        # 서울 지역 날씨만 필터 (첫 번째 location 기준)
        seoul_weather = df_weather[
            df_weather["location"].str.contains("서울")
        ].copy()

        if not seoul_weather.empty:
            # hour 기준으로 평균 날씨 매핑 (월 데이터 ↔ 일일 예보 매칭)
            weather_avg = seoul_weather.groupby("hour").agg(
                weather=("weather", lambda x: x.mode().iloc[0] if len(x) > 0 else 0),
                temperature=("temperature", "mean"),
                rain=("rain", "max"),
                rain_prob=("rain_prob", "mean"),
                humidity=("humidity", "mean"),
                wind_speed=("wind_speed", "mean"),
            ).reset_index()

            df = df.merge(weather_avg, on="hour", how="left")
            print(f"\n[기상] 날씨 데이터 결합 완료")
        else:
            print(f"\n[기상] 서울 데이터 없음 — 기본값 사용")
            df["weather"] = 0
            df["temperature"] = 15.0
            df["rain"] = 0
            df["rain_prob"] = 0.0
            df["humidity"] = 50.0
            df["wind_speed"] = 2.0
    else:
        df["weather"] = 0
        df["temperature"] = 15.0
        df["rain"] = 0
        df["rain_prob"] = 0.0
        df["humidity"] = 50.0
        df["wind_speed"] = 2.0

    # 5. 최종 Feature 선택 (weekday 제거, 2026-05-16 진단 P0 반영)
    feature_cols = [
        "hour",
        "weather", "temperature", "rain",
        "prev_boarding", "prev_alighting",
        "route_count",
        "boarding", "alighting",
        "label"
    ]

    # 존재하는 컬럼만 선택
    available = [c for c in feature_cols if c in df.columns]
    df_final = df[available].copy()

    # 결측값 제거
    df_final.dropna(subset=["label"], inplace=True)
    df_final["label"] = df_final["label"].astype(int)

    # 숫자형 변환
    for col in df_final.columns:
        if col != "label":
            df_final[col] = pd.to_numeric(df_final[col], errors="coerce").fillna(0)

    return df_final.reset_index(drop=True)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")

    boarding_dir = os.path.join(project_root, "data", "seoul_boarding")
    weather_dir = os.path.join(project_root, "data", "weather")
    output_dir = os.path.join(project_root, "data", "features")
    os.makedirs(output_dir, exist_ok=True)

    print(f"{'='*50}")
    print(f"BUSTAGO Feature DataFrame 구축")
    print(f"{'='*50}\n")

    # 1. 데이터 로드
    df_boarding = load_boarding_data(boarding_dir)
    df_weather = load_weather_data(weather_dir)

    # 2. Feature DataFrame 구축
    df_final = build_feature_dataframe(df_boarding, df_weather)

    # 3. 저장
    output_path = os.path.join(output_dir, "train_features.csv")
    df_final.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"\n{'='*50}")
    print(f"저장 완료: {os.path.abspath(output_path)}")
    print(f"데이터: {len(df_final):,}행 × {len(df_final.columns)}열")
    print(f"\n컬럼 목록: {list(df_final.columns)}")
    print(f"\n라벨 분포:\n{df_final['label'].value_counts().sort_index().to_string()}")
    print(f"\n시간대별 평균 승차량:")
    print(df_final.groupby("hour")["boarding"].mean().round(1).to_string())

    return df_final


if __name__ == "__main__":
    df = main()