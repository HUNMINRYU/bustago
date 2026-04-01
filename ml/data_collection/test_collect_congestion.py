import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# 모듈이 .env를 로드하면서 실제 API 키를 요구하므로 환경변수를 모킹합니다.
import os
os.environ["DATA_GO_KR_API_KEY"] = "MOCK_API_KEY"

from ml.data_collection.collect_congestion import fetch_congestion_by_route


@patch("ml.data_collection.collect_congestion.requests.get")
def test_fetch_congestion_success(mock_get):
    """정상적인 API 응답이 왔을 때 DataFrame이 올바르게 생성되는지 테스트"""
    # Mock Response 생성
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "msgHeader": {"headerCd": "0", "headerMsg": "정상처리되었습니다."},
        "msgBody": {
            "itemList": [
                {
                    "stId": "100000001",
                    "stNm": "테스트정류소",
                    "arsId": "01001",
                    "arrmsg1": "곧 도착",
                    "reride_Num1": "3",  # 보통
                    "arrmsg2": "10분 후",
                    "reride_Num2": "4",  # 혼잡
                }
            ]
        }
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    df = fetch_congestion_by_route("100100118")

    assert not df.empty
    assert len(df) == 1
    
    row = df.iloc[0]
    assert row["stNm"] == "테스트정류소"
    assert row["congestion_label1"] == "보통"
    assert row["label1"] == 1
    assert row["congestion_label2"] == "혼잡"
    assert row["label2"] == 2


@patch("ml.data_collection.collect_congestion.requests.get")
def test_fetch_congestion_api_error(mock_get):
    """API 헤더 응답이 에러 코드일 때 빈 DataFrame을 반환하는지 테스트"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "msgHeader": {"headerCd": "7", "headerMsg": "Key Error"},
    }
    mock_get.return_value = mock_resp

    df = fetch_congestion_by_route("100100118")
    assert df.empty


@patch("ml.data_collection.collect_congestion.requests.get")
def test_fetch_congestion_empty_data(mock_get):
    """데이터가 없을 때 (itemList가 비었을 때) 빈 DataFrame을 반환하는지 테스트"""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "msgHeader": {"headerCd": "0"},
        "msgBody": {} # itemList 누락
    }
    mock_get.return_value = mock_resp

    df = fetch_congestion_by_route("100100118")
    assert df.empty
