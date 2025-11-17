# 🚇 지하철 좌석 예측 앱

실시간 API 연동 + 모바일 친화적 UI

## 📁 프로젝트 구조

```
subway_app/
├── api/                    # API 연동 모듈
│   ├── __init__.py
│   ├── seoul_api.py       # 서울 열린데이터광장 API (실시간 도착 정보)
│   └── sk_api.py          # SK Open API (칸별 혼잡도)
├── templates/              # HTML 템플릿
│   ├── index.html         # 메인 화면 (출발/도착역 선택)
│   └── journey.html       # 여정 화면 (지도 + 열차/칸 선택)
├── static/                 # 정적 파일 (CSS, JS, 이미지)
├── app.py                  # Flask 메인 애플리케이션
└── README.md
```

## 🎯 구현된 기능

### ✅ 완료
1. **출발/도착역 선택** - 모바일 친화적 UI
2. **API 모듈화** - 서울/SK API 분리
3. **실시간 도착 정보** (Mock)
4. **칸별 혼잡도** (Mock)

### 🚧 작업 중
- 지도 통합 (카카오맵 API)
- 여정 화면 완성
- 탑승 및 하차 예측

## 🚀 실행 방법

```bash
cd subway_app
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 📱 주요 화면

1. **메인 (index.html)**
   - 출발역/도착역 검색 및 선택
   - 모바일 최적화 UI

2. **여정 (journey.html)** [작업 중]
   - 지도로 경로 표시
   - 실시간 열차 정보
   - 칸별 혼잡도
   - 하차 예측

## 🔑 API 키 설정

### 필요한 API 키:
1. **서울 열린데이터광장** - 실시간 도착 정보
   - 발급: https://data.seoul.go.kr
   - 설정: `api/seoul_api.py`의 `API_KEY`

2. **SK Open API** - 칸별 혼잡도
   - 발급: https://openapi.sk.com
   - 설정: `api/sk_api.py`의 `API_KEY`

3. **카카오맵 API** - 지도 표시
   - 발급: https://developers.kakao.com
   - 설정: `templates/journey.html`의 `YOUR_KAKAO_API_KEY`

## 💡 현재 상태

- Mock API로 작동 (실제 API 키 없이 테스트 가능)
- 데모용으로 2호선만 구현
- 모바일 친화적 UI 적용

## 📝 다음 단계

1. journey.html 템플릿 완성
2. 카카오맵 통합
3. 실시간 업데이트 기능
4. 도착 알림 기능
5. 하차 예측 알고리즘 개선
