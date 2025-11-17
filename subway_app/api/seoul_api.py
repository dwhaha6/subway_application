"""
서울 열린데이터광장 API 연동 모듈
실시간 지하철 도착 정보 제공
"""
import requests
from typing import List, Dict, Optional

class SeoulSubwayAPI:
    def __init__(self, api_key: str):
        """
        Args:
            api_key: 서울 열린데이터광장 API 키
        """
        self.api_key = api_key
        self.base_url = "http://swopenapi.seoul.go.kr/api/subway"

    def get_realtime_arrival(self, station_name: str) -> List[Dict]:
        """
        특정 역의 실시간 도착 정보 조회

        Args:
            station_name: 역 이름 (예: "강남")

        Returns:
            열차 도착 정보 리스트
            [{
                'line': '2호선',
                'direction': '외선순환(시청방면)',
                'arrival_time': 180,  # 초 단위
                'arrival_msg': '3분 후 도착',
                'current_station': '선릉',
                'train_no': '2241'
            }]
        """
        url = f"{self.base_url}/{self.api_key}/json/realtimeStationArrival/1/10/{station_name}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if 'realtimeArrivalList' not in data:
                return []

            arrivals = []
            for item in data['realtimeArrivalList']:
                arrivals.append({
                    'line': item.get('subwayId', ''),
                    'line_name': self._get_line_name(item.get('subwayId', '')),
                    'direction': item.get('trainLineNm', ''),
                    'arrival_time': int(item.get('barvlDt', '0')),
                    'arrival_msg': item.get('arvlMsg2', ''),
                    'current_station': item.get('arvlMsg3', ''),
                    'train_no': item.get('btrainNo', ''),
                    'dest_station': item.get('bstatnNm', ''),
                    'express_yn': item.get('btrainSttus', '0')  # 0:일반, 1:급행
                })

            return arrivals

        except Exception as e:
            print(f"API 호출 오류: {e}")
            return []

    def _get_line_name(self, subway_id: str) -> str:
        """지하철 노선 ID를 이름으로 변환"""
        line_map = {
            '1001': '1호선',
            '1002': '2호선',
            '1003': '3호선',
            '1004': '4호선',
            '1005': '5호선',
            '1006': '6호선',
            '1007': '7호선',
            '1008': '8호선',
            '1009': '9호선',
            '1063': '경의중앙선',
            '1065': '공항철도',
            '1067': '경춘선',
            '1075': '수인분당선',
            '1077': '신분당선',
        }
        return line_map.get(subway_id, subway_id)


# 데모용 Mock API (실제 API 키가 없을 때 사용)
class MockSeoulSubwayAPI:
    def get_realtime_arrival(self, station_name: str) -> List[Dict]:
        """데모용 Mock 데이터"""
        import random

        # 시뮬레이션: 2-3개의 열차 정보
        num_trains = random.randint(2, 3)
        arrivals = []

        for i in range(num_trains):
            arrival_time = (i + 1) * random.randint(120, 300)  # 2-5분 간격
            minutes = arrival_time // 60

            arrivals.append({
                'line': '1002',
                'line_name': '2호선',
                'direction': '외선순환(시청방면)' if i % 2 == 0 else '내선순환(을지로입구방면)',
                'arrival_time': arrival_time,
                'arrival_msg': f'{minutes}분 {arrival_time % 60}초 후',
                'current_station': ['선릉', '역삼', '강남'][i % 3],
                'train_no': f'224{i}',
                'dest_station': '시청',
                'express_yn': '0'
            })

        return sorted(arrivals, key=lambda x: x['arrival_time'])
