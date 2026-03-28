"""
BUSTAGO - 서울시 버스노선별 정류장별 시간대별 승하차 인원 수집
API: CardBusTimeNew (서울 열린데이터광장)
"""

import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

API_KEY = os.getenv("SEOUL_OPENDATA_API_KEY")
if not API_KEY:
    raise ValueError("SEOUL_OPENDATA_API_KEY가 .env 파일에 설정되지 않았습니다.")
BASE_URL = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/CardBusTimeNew"

# 수집 대상 정류장 (ARS번호 기준)
TARGET_STATIONS = {
    "02142": "명동.롯데영프라자",
    "22011": "지하철2호선강남역",
    "22009": "신분당선강남역",
    "22012": "지하철2호선강남역(반대편)",
}

# ============================================================
# 1. 특정 월의 전체 데이터 수집 (페이징 처리)
# ============================================================
def fetch_month_data(use_month: str, page_size: int = 1000) -> pd.DataFrame:
    """
    특정 월의 전체 승하차 데이터를 수집한다.
    use_month: 'YYYYMM' 형식 (예: '202511')
    """
    all_rows = []
    start = 1

    # 먼저 총 건수 확인
    url = f"{BASE_URL}/1/1/{use_month}/"
    resp = requests.get(url, timeout=15)
    data = resp.json()

    if "CardBusTimeNew" not in data:
        print(f"[ERROR] {use_month}: {data}")
        return pd.DataFrame()

    total = data["CardBusTimeNew"]["list_total_count"]
    print(f"[{use_month}] 총 {total:,}건 수집 시작...")

    # 페이징하며 전체 수집
    while start <= total:
        end = min(start + page_size - 1, total)
        url = f"{BASE_URL}/{start}/{end}/{use_month}/"

        try:
            resp = requests.get(url, timeout=30)
            rows = resp.json()["CardBusTimeNew"]["row"]
            all_rows.extend(rows)
            print(f"  {start:>6,} ~ {end:>6,} / {total:,} ({len(all_rows):,}건 수집)")
        except Exception as e:
            print(f"  [ERROR] {start}~{end}: {e}")

        start += page_size
        time.sleep(0.5)  # API 부하 방지

    df = pd.DataFrame(all_rows)
    print(f"[{use_month}] 완료: {len(df):,}건\n")
    return df


# ============================================================
# 2. 타겟 정류장만 필터링
# ============================================================
def filter_target_stations(df: pd.DataFrame) -> pd.DataFrame:
    """수집 대상 정류장만 필터링"""
    target_ids = list(TARGET_STATIONS.keys())
    df_filtered = df[df["STOPS_ARS_NO"].astype(str).isin(target_ids)].copy()
    print(f"필터링: {len(df):,}건 → {len(df_filtered):,}건 (대상 정류장 {len(target_ids)}곳)")
    return df_filtered


# ============================================================
# 3. wide → long 변환 (시간대별 승하차를 행으로 펼침)
# ============================================================
def melt_to_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    HR_0_GET_ON_TNOPE ~ HR_23_GET_ON_TNOPE 를
    (hour, boarding, alighting) 행으로 변환
    """
    records = []

    for _, row in df.iterrows():
        for h in range(24):
            on_col = f"HR_{h}_GET_ON_TNOPE"
            off_col = f"HR_{h}_GET_OFF_TNOPE"

            boarding = float(row.get(on_col, 0) or 0)
            alighting = float(row.get(off_col, 0) or 0)

            records.append({
                "use_month": row.get("USE_YM", ""),
                "route_no": row.get("RTE_NO", ""),
                "route_name": row.get("RTE_NM", ""),
                "stops_ars_no": str(row.get("STOPS_ARS_NO", "")),
                "station_name": row.get("SBWY_STNS_NM", ""),
                "bus_type": row.get("TRFC_MNS_TYPE_NM", ""),
                "hour": h,
                "boarding": int(boarding),
                "alighting": int(alighting),
            })

    df_long = pd.DataFrame(records)

    # 직전 시간대 승하차량 추가 (shift by 1 hour)
    df_long.sort_values(["stops_ars_no", "route_no", "hour"], inplace=True)
    grp = df_long.groupby(["stops_ars_no", "route_no"])
    df_long["prev_boarding"] = grp["boarding"].shift(1).fillna(0).astype(int)
    df_long["prev_alighting"] = grp["alighting"].shift(1).fillna(0).astype(int)

    return df_long.reset_index(drop=True)


# ============================================================
# 4. 정류장별 경유 노선 수 계산
# ============================================================
def add_route_count(df_long: pd.DataFrame) -> pd.DataFrame:
    """정류장별 경유 노선 수를 계산하여 추가"""
    route_count = (df_long.groupby("stops_ars_no")["route_no"]
                   .nunique().reset_index()
                   .rename(columns={"route_no": "route_count"}))
    df_long = df_long.merge(route_count, on="stops_ars_no", how="left")
    return df_long


# ============================================================
# 5. 요일 정보 추가 (월 데이터이므로 평균값 사용)
# ============================================================
def add_weekday_avg(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    월 단위 데이터이므로 요일 구분이 없음.
    weekday는 현장 카운팅 데이터에서 보완할 예정.
    여기서는 placeholder로 -1 지정.
    """
    df_long["weekday"] = -1  # 추후 카운팅/혼잡도 데이터에서 보완
    return df_long


# ============================================================
# MAIN: 실행
# ============================================================
def main():
    # 수집할 월 목록 (최근 6개월)
    months = ["202509", "202510", "202511", "202512", "202601", "202602"]

    # 출력 디렉토리 (스크립트 위치 기준으로 절대경로 생성)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")
    output_dir = os.path.join(project_root, "data", "seoul_boarding")
    os.makedirs(output_dir, exist_ok=True)

    print(f"저장 경로: {os.path.abspath(output_dir)}\n")

    all_dfs = []

    for month in months:
        # 1. 전체 데이터 수집
        df_raw = fetch_month_data(month)
        if df_raw.empty:
            continue

        # 2. 타겟 정류장 필터링
        df_filtered = filter_target_stations(df_raw)
        if df_filtered.empty:
            print(f"  [{month}] 대상 정류장 데이터 없음, 건너뜀")
            continue

        # 3. long 포맷 변환
        df_long = melt_to_hourly(df_filtered)

        # 4. 경유 노선 수 추가
        df_long = add_route_count(df_long)

        # 5. 요일 placeholder
        df_long = add_weekday_avg(df_long)

        all_dfs.append(df_long)

        # 월별 개별 저장
        df_long.to_csv(
            os.path.join(output_dir, f"boarding_{month}.csv"),
            index=False, encoding="utf-8-sig"
        )

    # 전체 통합 저장
    if all_dfs:
        df_all = pd.concat(all_dfs, ignore_index=True)
        df_all.to_csv(
            os.path.join(output_dir, "boarding_all.csv"),
            index=False, encoding="utf-8-sig"
        )
        print(f"\n{'='*50}")
        print(f"전체 수집 완료: {len(df_all):,}건")
        print(f"정류장 수: {df_all['stops_ars_no'].nunique()}")
        print(f"노선 수: {df_all['route_no'].nunique()}")
        print(f"\n시간대별 평균 승차 인원:")
        print(df_all.groupby("hour")["boarding"].mean().round(1).to_string())
        return df_all

    return pd.DataFrame()


if __name__ == "__main__":
    df = main()