"""
BUSTAGO - 서울시 버스도착정보 API에서 차내혼잡도 수집
API: 서울시 공공데이터 버스도착정보 (arrive/getArrInfoByRouteAll)

혼잡도 필드:
    - reride_Num1 / reride_Num2: 차내혼잡도 코드 (0:여유, 3:보통, 4:혼잡, 5:매우혼잡)
    - rerdie_Div1 / rerdie_Div2: 차내혼잡도 구분
"""

import requests
import pandas as pd
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

API_KEY = os.getenv("DATA_GO_KR_API_KEY")
if not API_KEY:
    raise ValueError("DATA_GO_KR_API_KEY가 .env 파일에 설정되지 않았습니다.")

BASE_URL = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll"

# 수집 대상 노선 (busRouteId)
TARGET_ROUTES = {
    "100100118": "753",
    "100100124": "401",
    "100100130": "144",
    "100100042": "140",
}

# 혼잡도 코드 → 라벨 매핑
CONGESTION_MAP = {
    0: "여유",
    3: "보통",
    4: "혼잡",
    5: "매우혼잡",
}

# 혼잡도 코드 → 모델 라벨 (0~3)
CONGESTION_TO_LABEL = {
    0: 0,   # 여유
    3: 1,   # 보통
    4: 2,   # 혼잡
    5: 3,   # 매우혼잡
}


def fetch_congestion_by_route(bus_route_id: str) -> pd.DataFrame:
    """
    특정 노선의 전체 정류소 도착정보에서 차내혼잡도를 수집한다.

    Returns:
        DataFrame: stId, stNm, busRouteId, route_name,
                   arrmsg1, congestion1, congestion_label1,
                   arrmsg2, congestion2, congestion_label2,
                   collected_at
    """
    params = {
        "serviceKey": API_KEY,
        "busRouteId": bus_route_id,
        "resultType": "json",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        header = data.get("msgHeader", {})
        if header.get("headerCd") != "0":
            print(f"  [ERROR] {bus_route_id}: {header.get('headerMsg', '알 수 없는 오류')}")
            return pd.DataFrame()

        items = data.get("msgBody", {}).get("itemList", [])
        if not items:
            print(f"  [WARNING] {bus_route_id}: 도착정보 없음")
            return pd.DataFrame()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = []

        for item in items:
            cong1 = int(item.get("reride_Num1", 0) or 0)
            cong2 = int(item.get("reride_Num2", 0) or 0)

            records.append({
                "stId": item.get("stId", ""),
                "stNm": item.get("stNm", ""),
                "arsId": item.get("arsId", ""),
                "busRouteId": bus_route_id,
                "route_name": TARGET_ROUTES.get(bus_route_id, ""),
                "arrmsg1": item.get("arrmsg1", ""),
                "congestion1": cong1,
                "congestion_label1": CONGESTION_MAP.get(cong1, "알수없음"),
                "label1": CONGESTION_TO_LABEL.get(cong1, 0),
                "arrmsg2": item.get("arrmsg2", ""),
                "congestion2": cong2,
                "congestion_label2": CONGESTION_MAP.get(cong2, "알수없음"),
                "label2": CONGESTION_TO_LABEL.get(cong2, 0),
                "collected_at": now,
            })

        df = pd.DataFrame(records)
        print(f"  [{TARGET_ROUTES.get(bus_route_id, bus_route_id)}] {len(df)}건 수집")
        return df

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] API 호출 실패 ({bus_route_id}): {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"  [ERROR] 데이터 처리 중 예외 ({bus_route_id}): {e}")
        return pd.DataFrame()


def collect_all_routes() -> pd.DataFrame:
    """모든 대상 노선의 혼잡도를 수집한다."""
    all_dfs = []

    for route_id, route_name in TARGET_ROUTES.items():
        df = fetch_congestion_by_route(route_id)
        if not df.empty:
            all_dfs.append(df)
        time.sleep(0.5)  # API 부하 방지

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..", "..")
    output_dir = os.path.join(project_root, "data", "congestion")
    os.makedirs(output_dir, exist_ok=True)

    print(f"저장 경로: {os.path.abspath(output_dir)}")
    print(f"수집 대상 노선: {len(TARGET_ROUTES)}개\n")

    print("=== 차내혼잡도 수집 ===")
    df = collect_all_routes()

    if df.empty:
        print("\n수집된 데이터가 없습니다.")
        return pd.DataFrame()

    # 저장
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"congestion_{now}.csv")
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    print(f"\n{'='*50}")
    print(f"저장 완료: {os.path.basename(filepath)} ({len(df):,}건)")
    print(f"\n혼잡도 분포 (첫 번째 버스):")
    print(df["congestion_label1"].value_counts().to_string())

    return df


if __name__ == "__main__":
    df = main()
