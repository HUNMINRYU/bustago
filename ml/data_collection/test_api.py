import requests
import os
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

API_KEY = os.getenv("SEOUL_OPENDATA_API_KEY")
if not API_KEY:
    raise ValueError("SEOUL_OPENDATA_API_KEY가 .env 파일에 설정되지 않았습니다.")

# 정류장명으로 ARS번호 검색
stations = ["명동", "강남역", "사당"]

for keyword in stations:
    url = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/CardBusTimeNew/1/3/202511/"
    resp = requests.get(url, timeout=15)
    data = resp.json()
    rows = data["CardBusTimeNew"]["row"]

    # 전체 데이터에서 키워드로 필터
    url2 = f"http://openapi.seoul.go.kr:8088/{API_KEY}/json/CardBusTimeNew/1/1000/202511/"
    resp2 = requests.get(url2, timeout=30)
    rows2 = resp2.json()["CardBusTimeNew"]["row"]

    matches = [r for r in rows2 if keyword in str(r.get("SBWY_STNS_NM", ""))]

    print(f"\n=== '{keyword}' 검색 결과 (상위 5건) ===")
    seen = set()
    for r in matches[:20]:
        key = r["STOPS_ARS_NO"]
        if key not in seen:
            seen.add(key)
            print(f"  ARS: {key} | 정류장: {r['SBWY_STNS_NM']} | 노선: {r['RTE_NM']}")
        if len(seen) >= 5:
            break