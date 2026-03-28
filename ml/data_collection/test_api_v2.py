import requests
import xml.etree.ElementTree as ET
import os
from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트 기준)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

# 공공데이터포털에서 발급받은 Decoding 키
API_KEY = os.getenv("DATA_GO_KR_API_KEY")
if not API_KEY:
    raise ValueError("DATA_GO_KR_API_KEY가 .env 파일에 설정되지 않았습니다.")

# 가이드 기준 엔드포인트: arrive/getArrInfoByRouteList
# 필요 파라미터: stId(정류소고유ID) + busRouteId(노선ID)
# 먼저 getArrInfoByRouteAllList로 노선 전체 정류소 조회 테스트
url = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll"

params = {
    "serviceKey": API_KEY,
    "busRouteId": "100100118",   # 가이드 샘플: 753번 버스
    "resultType": "json",
}

print("=== 버스도착정보 API 테스트 (가이드 기준) ===\n")

resp = requests.get(url, params=params, timeout=10)
print(f"상태코드: {resp.status_code}\n")

# JSON 응답 시도
try:
    data = resp.json()
    header = data.get("msgHeader", {})
    print(f"응답코드: {header.get('headerCd')} | 메시지: {header.get('headerMsg')}")

    items = data.get("msgBody", {}).get("itemList", [])
    print(f"조회 건수: {len(items)}\n")

    for item in items[:5]:
        print(f"정류장: {item.get('stNm', '')} (stId: {item.get('stId', '')})")
        print(f"  도착1: {item.get('arrmsg1', '')} | 혼잡구분: {item.get('rerdie_Div1', '')} | 혼잡코드: {item.get('reride_Num1', '')} | 만차: {item.get('full1', '')}")
        print(f"  도착2: {item.get('arrmsg2', '')} | 혼잡구분: {item.get('rerdie_Div2', '')} | 혼잡코드: {item.get('reride_Num2', '')} | 만차: {item.get('full2', '')}")
        print()

except:
    # XML 응답인 경우
    print("JSON 파싱 실패, XML 응답 확인:")
    print(resp.text[:1500])