# app.py
from flask import Flask, request, redirect, render_template_string
from datetime import datetime
import random

app = Flask(__name__)

# 서울 지하철 노선 데이터 (주요 노선만)
SUBWAY_LINES = {
    "1호선": {
        "stations": ["소요산", "동두천", "보산", "동두천중앙", "지행", "덕정", "덕계", "양주", "녹양", "가능", "의정부", "회룡", "망월사", "도봉산", "도봉", "방학", "창동", "녹천", "월계", "광운대", "석계", "신이문", "외대앞", "회기", "청량리", "제기동", "신설동", "동묘앞", "동대문", "종로5가", "종로3가", "종각", "시청", "서울역", "남영", "용산", "노량진", "대방", "신길", "영등포", "신도림", "구로", "구일", "개봉", "오류동", "온수", "역곡", "소사", "부천", "중동", "송내", "부개", "부평", "백운", "동암", "간석", "주안", "도화", "제물포", "도원", "동인천", "인천"],
        "branches": {
            "소요산행": (0, 60),
            "인천행": (60, 0),  # 역방향
            "광운대행": (60, 19),  # 역방향
            "청량리행": (60, 24),  # 역방향
        }
    },
    "2호선": {
        "stations": ["시청", "을지로입구", "을지로3가", "을지로4가", "동대문역사문화공원", "신당", "상왕십리", "왕십리", "한양대", "뚝섬", "성수", "건대입구", "구의", "강변", "잠실나루", "잠실", "삼성", "선릉", "역삼", "강남", "교대", "서초", "방배", "사당", "낙성대", "서울대입구", "봉천", "신림", "신대방", "구로디지털단지", "대림", "신도림", "문래", "영등포구청", "당산", "합정", "홍대입구", "신촌", "이대", "아현", "충정로", "시청"],
        "branches": {
            "순환": (0, 41),  # 2호선은 순환선 (시청으로 돌아옴)
        }
    },
    "3호선": {
        "stations": ["대화", "주엽", "정발산", "마두", "백석", "대곡", "화정", "원당", "원흥", "삼송", "지축", "구파발", "연신내", "불광", "녹번", "홍제", "무악재", "독립문", "경복궁", "안국", "종로3가", "을지로3가", "충무로", "동대입구", "약수", "금호", "옥수", "압구정", "신사", "잠원", "고속터미널", "교대", "남부터미널", "양재", "매봉", "도곡", "대치", "학여울", "대청", "일원", "수서", "가락시장", "경찰병원", "오금"],
        "branches": {
            "오금행": (0, 43),
            "대화행": (43, 0),  # 역방향
            "지축행": (43, 10),  # 역방향
        }
    },
    "4호선": {
        "stations": ["당고개", "상계", "노원", "창동", "쌍문", "수유", "미아", "미아사거리", "길음", "성신여대입구", "한성대입구", "혜화", "동대문", "동대문역사문화공원", "충무로", "명동", "회현", "서울역", "숙대입구", "삼각지", "신용산", "이촌", "동작", "총신대입구", "사당", "남태령", "선바위", "경마공원", "대공원", "과천", "정부과천청사", "인덕원", "평촌", "범계", "금정", "산본", "수리산", "대야미", "반월", "상록수", "한대앞", "중앙", "고잔", "초지", "안산", "신길온천", "정왕", "오이도"],
        "branches": {
            "오이도행": (0, 47),
            "당고개행": (47, 0),  # 역방향
            "안산행": (0, 44),
            "남태령행": (47, 25),  # 역방향
        }
    },
}

# 좌석 상태(메모리). 실습용: 좌석 1~14 (위 7개, 아래 7개)
SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
CURRENT_LINE = None  # 현재 호선
CURRENT_DIRECTION = None  # 현재 행선지
CURRENT_STATION_IDX = 0  # 시뮬레이터용 "현재 역 인덱스"
STATIONS = []  # 현재 노선의 역 리스트
START_IDX = 0  # 시작역 인덱스
END_IDX = 0  # 종착역 인덱스
USER_STATE = {"seated_at": None, "waiting_at": None, "standing_count": 0}  # 사용자 상태 (어느 좌석에 앉았는지 or 어느 좌석 앞에서 기다리는지, 서있은 정거장 수)
FUTURE_MODE = True  # 앱 아이디어 반영 모드 (True: 신기능, False: 실제 세계)
STANDING_HISTORY = {"future": [], "real": []}  # 착석 성공 시 서있던 시간 기록 (최대 10개, FIFO)
SUCCESS_MESSAGE = None  # 착석 성공 메시지 (정거장 수)
GAME_MODE = None  # "custom" 또는 "compare"
COMPARISON_DATA = None  # 비교 모드에서 사용할 조건 저장
COMPARISON_PHASE = None  # "future" 또는 "real" (비교 모드의 현재 단계)

# 비교 모드용 미리 정의된 시나리오 (종점까지 약 15정거장 이내)
COMPARISON_SCENARIOS = [
    {"line": "2호선", "direction": "순환", "station": "강남", "max_stops": 15},  # 강남부터 15정거장
    {"line": "3호선", "direction": "대화-오금", "station": "교대", "max_stops": 15},  # 교대부터 15정거장
    {"line": "4호선", "direction": "당고개-오이도", "station": "동대문", "max_stops": 15},  # 동대문부터 15정거장
]

SUCCESS_PAGE = """
<!doctype html>
<title>착석 성공! 🎉</title>
<style>
body {
  font-family: sans-serif;
  max-width: 600px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  overflow: hidden;
}
.success-container {
  text-align: center;
  color: white;
  animation: fadeIn 0.5s ease-in;
}
.success-title {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 20px;
  animation: bounce 1s ease-in-out;
}
.success-message {
  font-size: 32px;
  margin: 20px 0;
}
.success-stats {
  font-size: 20px;
  background: rgba(255,255,255,0.2);
  padding: 20px;
  border-radius: 12px;
  margin: 20px 0;
}
.balloon {
  position: fixed;
  font-size: 48px;
  animation: float 4s ease-in-out infinite;
}
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}
@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-100vh) rotate(360deg); }
}
</style>
<script>
// 풍선 이펙트 생성
function createBalloons() {
  const balloons = ['🎈', '🎉', '🎊', '✨', '🌟', '💫'];
  for (let i = 0; i < 20; i++) {
    setTimeout(() => {
      const balloon = document.createElement('div');
      balloon.className = 'balloon';
      balloon.textContent = balloons[Math.floor(Math.random() * balloons.length)];
      balloon.style.left = Math.random() * 100 + '%';
      balloon.style.animationDelay = Math.random() * 2 + 's';
      balloon.style.animationDuration = (3 + Math.random() * 2) + 's';
      document.body.appendChild(balloon);
      setTimeout(() => balloon.remove(), 5000);
    }, i * 100);
  }
}
createBalloons();

// 3초 후 자동으로 초기화면으로 이동
setTimeout(() => {
  window.location.href = '/continue';
}, 3000);
</script>

<div class="success-container">
  <div class="success-title">🎉 착석 성공! 🎉</div>
  <div class="success-message">축하합니다!</div>
  <div class="success-stats">
    <strong>{{ standing_count }}정거장</strong> 동안 서있었습니다
  </div>
  <p style="font-size: 16px; opacity: 0.9;">3초 후 자동으로 돌아갑니다...</p>
</div>
"""

MODE_SELECT_PAGE = """
<!doctype html>
<title>지하철 좌석 예측 - 모드 선택</title>
<style>
body { font-family: sans-serif; max-width: 800px; margin: 48px auto; }
.mode-container { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 32px; }
.mode-card {
  border: 2px solid #ddd;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}
.mode-card:hover {
  border-color: #2196f3;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.2);
  transform: translateY(-4px);
}
.mode-icon { font-size: 64px; margin-bottom: 16px; }
.mode-title { font-size: 24px; font-weight: bold; margin-bottom: 12px; }
.mode-desc { color: #666; line-height: 1.6; }
button { background: #2196f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; width: 100%; margin-top: 16px; }
button:hover { background: #1976d2; }
</style>

<h1>🚇 지하철 좌석 예측 시스템</h1>
<p>원하는 모드를 선택하세요.</p>

{% if future_history or real_history %}
<div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <h3 style="margin: 0;">📊 비교 모드 착석 기록</h3>
    <form method="post" action="/clear_history" style="margin: 0;">
      <button type="submit" style="background: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; width: auto;">🗑️ 기록 삭제</button>
    </form>
  </div>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
    <div>
      <h4 style="margin: 8px 0; color: #2196f3;">💡 앱 아이디어 반영 모드</h4>
      {% if future_history %}
        <ul style="margin: 8px 0; padding-left: 20px;">
          {% for count in future_history %}
          <li>{{ count }}정거장 서있음</li>
          {% endfor %}
        </ul>
        <p style="color: #666; font-size: 14px; margin: 8px 0;">평균: {{ future_avg }}정거장</p>
      {% else %}
        <p style="color: #999;">기록 없음</p>
      {% endif %}
    </div>

    <div>
      <h4 style="margin: 8px 0; color: #ff9800;">🌍 실제 세계 모드</h4>
      {% if real_history %}
        <ul style="margin: 8px 0; padding-left: 20px;">
          {% for count in real_history %}
          <li>{{ count }}정거장 서있음</li>
          {% endfor %}
        </ul>
        <p style="color: #666; font-size: 14px; margin: 8px 0;">평균: {{ real_avg }}정거장</p>
      {% else %}
        <p style="color: #999;">기록 없음</p>
      {% endif %}
    </div>
  </div>
</div>
{% endif %}

<div class="mode-container">
  <div class="mode-card">
    <div class="mode-icon">🎨</div>
    <div class="mode-title">커스텀 모드</div>
    <div class="mode-desc">
      호선, 행선지, 현재 역을 직접 선택하여<br>
      자유롭게 시뮬레이션을 진행합니다.<br>
      <strong>※ 기록에 포함되지 않습니다</strong>
    </div>
    <form method="post" action="/select_mode">
      <input type="hidden" name="mode" value="custom">
      <button type="submit">커스텀 모드 시작</button>
    </form>
  </div>

  <div class="mode-card">
    <div class="mode-icon">⚖️</div>
    <div class="mode-title">비교 모드</div>
    <div class="mode-desc">
      동일한 조건에서 아이디어 반영 모드와<br>
      현실 세계 모드를 순차적으로 체험하여<br>
      <strong>공정하게 비교</strong>합니다
    </div>
    <form method="post" action="/select_mode">
      <input type="hidden" name="mode" value="compare">
      <button type="submit" style="background: #ff9800;">비교 모드 시작</button>
    </form>
  </div>
</div>
"""

COMPARE_SELECT_PAGE = """
<!doctype html>
<title>비교 모드 - 조건 선택</title>
<style>
body { font-family: sans-serif; max-width: 600px; margin: 48px auto; }
.scenario-card {
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.scenario-card:hover {
  border-color: #ff9800;
  background: #fff3e0;
}
.scenario-title { font-size: 20px; font-weight: bold; margin-bottom: 8px; }
.scenario-detail { color: #666; font-size: 14px; }
button { background: #ff9800; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; width: 100%; margin-top: 8px; }
button:hover { background: #f57c00; }
.back-btn { background: #999; margin-bottom: 24px; }
.back-btn:hover { background: #777; }
</style>

<form method="post" action="/reset" style="margin: 0;">
  <button type="submit" class="back-btn">← 뒤로 가기</button>
</form>

<h1>⚖️ 비교 모드</h1>
<p>비교할 시나리오를 선택하세요. 동일한 조건에서 두 모드를 체험합니다.</p>

{% for idx, scenario in scenarios %}
<div class="scenario-card">
  <div class="scenario-title">시나리오 {{ idx + 1 }}</div>
  <div class="scenario-detail">
    📍 {{ scenario.line }} | {{ scenario.direction }}<br>
    🚉 현재 역: {{ scenario.station }}
  </div>
  <form method="post" action="/start_comparison">
    <input type="hidden" name="scenario_idx" value="{{ idx }}">
    <button type="submit">이 조건으로 시작</button>
  </form>
</div>
{% endfor %}
"""

SETUP_PAGE = """
<!doctype html>
<title>커스텀 모드 - 초기 설정</title>
<style>
body { font-family: sans-serif; max-width: 600px; margin: 48px auto; }
.form-group { margin-bottom: 20px; }
label { display: block; margin-bottom: 8px; font-weight: bold; }
select, input { width: 100%; padding: 8px; font-size: 14px; }
button { background: #2196f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
button:hover { background: #1976d2; }
.back-btn { background: #999; margin-bottom: 24px; }
.back-btn:hover { background: #777; }
</style>

<form method="post" action="/reset" style="margin: 0;">
  <button type="submit" class="back-btn">← 뒤로 가기</button>
</form>

<h1>🎨 커스텀 모드</h1>
<p>호선, 행선지, 현재 역을 선택하여 시작하세요.</p>

{% if future_history or real_history %}
<div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <h3 style="margin: 0;">📊 착석 기록</h3>
    <form method="post" action="/clear_history" style="margin: 0;">
      <button type="submit" style="background: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer;">🗑️ 기록 삭제</button>
    </form>
  </div>

  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
    <div>
      <h4 style="margin: 8px 0; color: #2196f3;">💡 앱 아이디어 반영 모드</h4>
      {% if future_history %}
        <ul style="margin: 8px 0; padding-left: 20px;">
          {% for count in future_history %}
          <li>{{ count }}정거장 서있음</li>
          {% endfor %}
        </ul>
        <p style="color: #666; font-size: 14px; margin: 8px 0;">평균: {{ future_avg }}정거장</p>
      {% else %}
        <p style="color: #999;">기록 없음</p>
      {% endif %}
    </div>

    <div>
      <h4 style="margin: 8px 0; color: #ff9800;">🌍 실제 세계 모드</h4>
      {% if real_history %}
        <ul style="margin: 8px 0; padding-left: 20px;">
          {% for count in real_history %}
          <li>{{ count }}정거장 서있음</li>
          {% endfor %}
        </ul>
        <p style="color: #666; font-size: 14px; margin: 8px 0;">평균: {{ real_avg }}정거장</p>
      {% else %}
        <p style="color: #999;">기록 없음</p>
      {% endif %}
    </div>
  </div>
</div>
{% endif %}

<form method="post" action="/start">
  <div class="form-group">
    <label>호선 선택</label>
    <select name="line" id="line" required onchange="updateStationsAndDirections()">
      <option value="">선택하세요</option>
      {% for line in lines %}
      <option value="{{ line }}">{{ line }}</option>
      {% endfor %}
    </select>
  </div>

  <div class="form-group">
    <label>행선 (열차 방향)</label>
    <select name="direction" id="direction" required onchange="updateCurrentStations()">
      <option value="">호선을 먼저 선택하세요</option>
    </select>
  </div>

  <div class="form-group">
    <label>현재 역</label>
    <select name="current_station" id="current_station" required>
      <option value="">행선을 먼저 선택하세요</option>
    </select>
  </div>

  <div class="form-group" style="background: #f0f0f0; padding: 12px; border-radius: 6px;">
    <label style="display: flex; align-items: center; cursor: pointer;">
      <input type="checkbox" name="future_mode" value="true" checked style="width: auto; margin-right: 8px;">
      <span><strong>💡 앱 아이디어 반영 모드</strong> - 승객들의 목적지와 남은 정거장을 표시합니다</span>
    </label>
    <small style="color: #666; display: block; margin-top: 6px;">
      ⚠️ 체크 해제 시: 실제 지하철처럼 승객들이 어디서 내릴지 알 수 없습니다
    </small>
  </div>

  <button type="submit">🚀 시작하기</button>
</form>

<script>
const lineData = {{ line_data|safe }};

function updateStationsAndDirections() {
  const line = document.getElementById('line').value;
  const directionSelect = document.getElementById('direction');
  const stationSelect = document.getElementById('current_station');

  directionSelect.innerHTML = '<option value="">선택하세요</option>';
  stationSelect.innerHTML = '<option value="">행선을 먼저 선택하세요</option>';

  if (line && lineData[line]) {
    const branches = lineData[line].branches;
    for (const [branchName, range] of Object.entries(branches)) {
      const option = document.createElement('option');
      option.value = branchName;
      option.textContent = branchName;
      directionSelect.appendChild(option);
    }
  }
}

function updateCurrentStations() {
  const line = document.getElementById('line').value;
  const direction = document.getElementById('direction').value;
  const stationSelect = document.getElementById('current_station');

  stationSelect.innerHTML = '<option value="">선택하세요</option>';

  if (line && direction && lineData[line]) {
    const branches = lineData[line].branches;
    const stations = lineData[line].stations;
    const [startIdx, endIdx] = branches[direction];

    // 역방향 처리: startIdx > endIdx인 경우
    if (startIdx > endIdx) {
      // 역방향: startIdx에서 endIdx까지 감소
      for (let i = startIdx; i > endIdx; i--) {
        const option = document.createElement('option');
        option.value = stations[i];
        option.textContent = stations[i];
        stationSelect.appendChild(option);
      }
    } else {
      // 정방향: startIdx에서 endIdx까지 증가
      for (let i = startIdx; i < endIdx; i++) {
        const option = document.createElement('option');
        option.value = stations[i];
        option.textContent = stations[i];
        stationSelect.appendChild(option);
      }
    }
  }
}
</script>
"""

PAGE = """
<!doctype html>
<title>Subway Seat Demo</title>
<style>
body { font-family: sans-serif; max-width: 1200px; margin: 24px auto; }
.info-box { background: #f5f5f5; padding: 16px; border-radius: 8px; margin-bottom: 24px; }
.info-box h3 { margin-top: 0; }
.reset-btn { background: #f44336; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-left: 12px; }

/* 지하철 좌석 레이아웃 */
.subway-container {
  background: #f9f9f9;
  border: 3px solid #333;
  border-radius: 16px;
  padding: 32px 24px;
  margin: 24px 0;
}

.seat-row {
  display: flex;
  justify-content: space-around;
  gap: 16px;
  margin-bottom: 80px;
}

.seat-row:last-child {
  margin-bottom: 0;
}

.seat-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 140px;
}

.seat {
  width: 100%;
  min-height: 120px;
  border: 3px solid #333;
  border-radius: 12px;
  padding: 12px;
  text-align: center;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 6px;
}

.seat.free {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
  border-color: #4caf50;
}

.seat.occupied {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border-color: #ff9800;
}

.seat.soon {
  background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
  border-color: #f44336;
}

.seat.recommended {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  border-color: #2196f3;
  box-shadow: 0 0 20px rgba(33, 150, 243, 0.5);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.seat-number {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

.seat-status {
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.7);
  font-weight: bold;
}

.seat-info {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.wait-button {
  width: 100%;
  padding: 10px 16px;
  background: #ff9800;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.wait-button:hover {
  background: #f57c00;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.wait-button:disabled {
  background: #ccc;
  cursor: not-allowed;
  transform: none;
}

.waiting-indicator {
  width: 100%;
  padding: 8px;
  background: #fff3e0;
  border: 2px solid #ff9800;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  color: #f57c00;
}

.seated-indicator {
  width: 100%;
  padding: 8px;
  background: #e8f5e9;
  border: 2px solid #4caf50;
  border-radius: 6px;
  font-size: 13px;
  font-weight: bold;
  color: #2e7d32;
}

.recommendation-badge {
  position: absolute;
  top: -10px;
  right: -10px;
  font-size: 24px;
  animation: spin 3s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

small { color: #666; }

.next-station-btn {
  background: #2196f3;
  color: white;
  padding: 16px 48px;
  border: none;
  border-radius: 50px;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.4);
  transition: all 0.3s;
}

.next-station-btn:hover {
  background: #1976d2;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(33, 150, 243, 0.6);
}

.next-station-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.4);
}
</style>

<h1>🚇 지하철 좌석 예측 시스템</h1>

<div class="info-box">
  <h3>📍 열차 정보</h3>
  <p><strong>호선:</strong> {{ line }} | <strong>행선지:</strong> {{ direction }}</p>
  <p><strong>현재 역:</strong> {{ current_station }} ({{ cur_idx + 1 }}/{{ total_stations }})</p>
  <p><strong>모드:</strong>
    {% if future_mode %}
      💡 앱 아이디어 반영 (목적지/정거장 표시)
    {% else %}
      🌍 실제 세계 (정보 숨김)
    {% endif %}
  </p>
  {% if is_compare_mode %}
  <div style="background: #e3f2fd; padding: 12px; border-radius: 6px; margin: 12px 0; border-left: 4px solid #2196f3;">
    <strong>⚖️ 비교 모드 진행 중</strong><br>
    <small>
      {% if comparison_phase == 'future' %}
        현재: 1단계 (앱 아이디어 반영 모드) → 착석 성공 시 2단계 (실제 세계 모드)로 진행됩니다
      {% else %}
        현재: 2단계 (실제 세계 모드) → 착석 성공 시 결과 비교 화면으로 이동합니다
      {% endif %}
    </small>
  </div>
  {% endif %}
  <form method="post" action="/reset" style="display: inline;">
    <button class="reset-btn">🔄 처음부터</button>
  </form>
</div>

<div style="background: #fff9c4; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
  <strong>👤 내 상태:</strong>
  {% if user_state.seated_at %}
    {{ user_state.seated_at }}번 좌석에 착석 중
  {% elif user_state.waiting_at %}
    {{ user_state.waiting_at }}번 좌석 앞에서 대기 중 (대기 순서: {{ user_wait_position }}번째)
  {% else %}
    서있음 (좌석 선택 안함)
  {% endif %}
  {% if not user_state.seated_at %}
    <span style="color: #f57c00; margin-left: 12px;">⏱️ <strong>{{ user_state.standing_count }}정거장</strong> 동안 서있음</span>
  {% endif %}
</div>

<h2>좌석 현황</h2>
{% if recommended_seat and future_mode %}
<div style="background: #e3f2fd; padding: 12px; border-radius: 6px; margin-bottom: 16px;">
  <strong>💡 추천 좌석:</strong> {{ recommended_seat }}번 좌석 (가장 빨리 비워질 예정)
</div>
{% endif %}

<div class="subway-container">
  <!-- 위쪽 좌석 (1~7번) -->
  <div class="seat-row">
    {% for sid in range(1, 8) %}
      {% set info = seats[sid] %}
      {% set status_class = 'free' if info.status=='free' else ('soon' if (future_mode and info.stops_left==0) else 'occupied') %}
      {% set is_recommended = (sid == recommended_seat) %}
      <div class="seat-wrapper">
        <!-- 좌석 -->
        <div class="seat {{ status_class }}{% if future_mode and is_recommended %} recommended{% endif %}">
          {% if future_mode and is_recommended %}
          <div class="recommendation-badge">⭐</div>
          {% endif %}
          <div class="seat-number">{{ sid }}번</div>
          <div class="seat-status">
            {% if info.status=='free' %}
              비어있음
            {% elif future_mode and info.stops_left==0 %}
              곧 비움
            {% else %}
              착석중
            {% endif %}
          </div>
          {% if future_mode and info.status != 'free' %}
          <div class="seat-info">
            📍 {{ info.destination or '-' }}<br>
            ⏱️ {{ info.stops_left if info.stops_left is not none else '-' }}정거장
          </div>
          {% endif %}
          {% if info.waiting_queue|length > 0 and 'user' not in info.waiting_queue %}
          <div class="seat-info" style="color: #ff9800;">
            🧍 대기자 있음
          </div>
          {% endif %}
        </div>

        <!-- 버튼/상태 표시 -->
        {% if user_state.seated_at == sid %}
          <div class="seated-indicator">✓ 착석 중</div>
        {% elif user_state.waiting_at == sid %}
          <div class="waiting-indicator">⏳ 대기 중</div>
        {% else %}
          {% if info.status == 'free' and info.waiting_queue|length == 0 %}
            <form method="post" action="/wait" style="width: 100%;">
              <input type="hidden" name="seat_id" value="{{ sid }}">
              <button type="submit" class="wait-button" style="background: #4caf50;">💺 앉기</button>
            </form>
          {% elif info.waiting_queue|length == 0 %}
            <form method="post" action="/wait" style="width: 100%;">
              <input type="hidden" name="seat_id" value="{{ sid }}">
              <button type="submit" class="wait-button">🧍 서기</button>
            </form>
          {% else %}
            <button class="wait-button" disabled>대기 중</button>
          {% endif %}
        {% endif %}
      </div>
    {% endfor %}
  </div>

  <!-- 아래쪽 좌석 (8~14번) -->
  <div class="seat-row">
    {% for sid in range(8, 15) %}
      {% set info = seats[sid] %}
      {% set status_class = 'free' if info.status=='free' else ('soon' if (future_mode and info.stops_left==0) else 'occupied') %}
      {% set is_recommended = (sid == recommended_seat) %}
      <div class="seat-wrapper">
        <!-- 버튼/상태 표시 -->
        {% if user_state.seated_at == sid %}
          <div class="seated-indicator">✓ 착석 중</div>
        {% elif user_state.waiting_at == sid %}
          <div class="waiting-indicator">⏳ 대기 중</div>
        {% else %}
          {% if info.status == 'free' and info.waiting_queue|length == 0 %}
            <form method="post" action="/wait" style="width: 100%;">
              <input type="hidden" name="seat_id" value="{{ sid }}">
              <button type="submit" class="wait-button" style="background: #4caf50;">💺 앉기</button>
            </form>
          {% elif info.waiting_queue|length == 0 %}
            <form method="post" action="/wait" style="width: 100%;">
              <input type="hidden" name="seat_id" value="{{ sid }}">
              <button type="submit" class="wait-button">🧍 서기</button>
            </form>
          {% else %}
            <button class="wait-button" disabled>대기 중</button>
          {% endif %}
        {% endif %}

        <!-- 좌석 -->
        <div class="seat {{ status_class }}{% if future_mode and is_recommended %} recommended{% endif %}">
          {% if future_mode and is_recommended %}
          <div class="recommendation-badge">⭐</div>
          {% endif %}
          <div class="seat-number">{{ sid }}번</div>
          <div class="seat-status">
            {% if info.status=='free' %}
              비어있음
            {% elif future_mode and info.stops_left==0 %}
              곧 비움
            {% else %}
              착석중
            {% endif %}
          </div>
          {% if future_mode and info.status != 'free' %}
          <div class="seat-info">
            📍 {{ info.destination or '-' }}<br>
            ⏱️ {{ info.stops_left if info.stops_left is not none else '-' }}정거장
          </div>
          {% endif %}
          {% if info.waiting_queue|length > 0 and 'user' not in info.waiting_queue %}
          <div class="seat-info" style="color: #ff9800;">
            🧍 대기자 있음
          </div>
          {% endif %}
        </div>
      </div>
    {% endfor %}
  </div>
</div>

<p><small>💡 Tip: {% if future_mode %}추천 좌석 앞에서 대기하면 가장 빨리 앉을 수 있습니다!{% else %}좌석 앞에서 대기하다가 자리가 비면 자동으로 앉습니다!{% endif %}</small></p>

<!-- 다음 역 버튼 (하단 고정) -->
<div style="position: sticky; bottom: 20px; text-align: center; margin: 32px 0;">
  <form method="post" action="/tick">
    <button type="submit" class="next-station-btn">
      ➡️ 다음 역으로 이동
    </button>
  </form>
</div>

<script>
// 페이지 로드 시 저장된 스크롤 위치로 복원
window.addEventListener('load', function() {
  const scrollPos = sessionStorage.getItem('scrollPos');
  if (scrollPos) {
    window.scrollTo(0, parseInt(scrollPos));
    sessionStorage.removeItem('scrollPos');
  }
});

// 폼 제출 전 현재 스크롤 위치 저장
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function() {
    sessionStorage.setItem('scrollPos', window.scrollY);
  });
});
</script>
"""

def nowstr():
    return datetime.now().strftime("%H:%M:%S")

def seat_to_position(seat_id):
    """좌석 번호를 (row, col)로 변환"""
    if seat_id <= 7:
        return (0, seat_id - 1)  # 위쪽 줄 (row=0)
    else:
        return (1, seat_id - 8)  # 아래쪽 줄 (row=1)

def weighted_distance(seat1, seat2):
    """가중치를 부여한 맨하탄 거리 계산
    거리 = 같은줄거리 + (다른줄이면 × 1.5)
    """
    r1, c1 = seat_to_position(seat1)
    r2, c2 = seat_to_position(seat2)

    col_distance = abs(c1 - c2)  # 같은 줄 거리
    row_difference = abs(r1 - r2)  # 다른 줄 여부 (0 또는 1)

    return col_distance + (row_difference * 1.5)

def initialize_seats():
    """모든 좌석에 랜덤 목적지 할당 (모든 좌석 착석 중으로 초기화)"""
    global SEATS
    is_reverse = START_IDX > END_IDX  # 역방향 여부

    for seat_id in SEATS:
        # 정방향과 역방향에 따라 다르게 처리
        if is_reverse:
            # 역방향: CURRENT_STATION_IDX에서 END_IDX로 감소
            if CURRENT_STATION_IDX > END_IDX + 1:
                destination_idx = random.randint(END_IDX + 1, CURRENT_STATION_IDX - 1)
                destination = STATIONS[destination_idx]
                stops_left = CURRENT_STATION_IDX - destination_idx
            else:
                # 남은 역이 부족하면 최소 1정거장
                destination_idx = END_IDX + 1 if END_IDX + 1 < len(STATIONS) else CURRENT_STATION_IDX - 1
                destination = STATIONS[destination_idx]
                stops_left = 1

            SEATS[seat_id] = {
                "stops_left": stops_left,
                "status": "occupied",
                "updated": nowstr(),
                "destination": destination,
                "waiting_queue": []
            }

            # 각 좌석마다 50% 확률로 대기자 1명 추가 (최대 1명)
            if random.random() > 0.5:
                SEATS[seat_id]["waiting_queue"].append(f"person_{seat_id}_0")
        else:
            # 정방향: CURRENT_STATION_IDX에서 END_IDX로 증가
            if CURRENT_STATION_IDX < END_IDX - 1:
                destination_idx = random.randint(CURRENT_STATION_IDX + 1, END_IDX - 1)
                destination = STATIONS[destination_idx]
                stops_left = destination_idx - CURRENT_STATION_IDX
            else:
                # 남은 역이 부족하면 최소 1정거장
                destination_idx = CURRENT_STATION_IDX + 1 if CURRENT_STATION_IDX + 1 < END_IDX else END_IDX - 1
                destination = STATIONS[destination_idx]
                stops_left = 1

            SEATS[seat_id] = {
                "stops_left": stops_left,
                "status": "occupied",
                "updated": nowstr(),
                "destination": destination,
                "waiting_queue": []
            }

            # 각 좌석마다 50% 확률로 대기자 1명 추가 (최대 1명)
            if random.random() > 0.5:
                SEATS[seat_id]["waiting_queue"].append(f"person_{seat_id}_0")

def get_recommended_seat():
    """대기자가 없는 좌석 중 가장 빨리 비워질 좌석 찾기 (앱 아이디어 반영 모드에만 작동)"""
    if not FUTURE_MODE:
        return None

    # 사용자가 현재 대기 중인 좌석의 기대값 계산
    user_expected_wait = None
    if USER_STATE["waiting_at"]:
        waiting_seat = SEATS[USER_STATE["waiting_at"]]
        if waiting_seat["stops_left"] is not None:
            user_expected_wait = waiting_seat["stops_left"]

    # 착석 중이고, 대기자가 없는 좌석만 필터링
    occupied_seats = {sid: info for sid, info in SEATS.items()
                      if info["status"] != "free"
                      and info["stops_left"] is not None
                      and len(info["waiting_queue"]) == 0}

    # 사용자가 대기 중이면, 기대값보다 오래 걸리는 좌석은 제외
    if user_expected_wait is not None:
        occupied_seats = {sid: info for sid, info in occupied_seats.items()
                         if info["stops_left"] < user_expected_wait}

    if not occupied_seats:
        return None

    # 남은 정거장이 가장 적은 좌석 찾기
    min_seat = min(occupied_seats.items(), key=lambda x: x[1]["stops_left"])
    return min_seat[0]

@app.route("/")
def home():
    global SUCCESS_MESSAGE

    # 착석 성공 메시지가 있으면 축하 화면 표시
    if SUCCESS_MESSAGE is not None:
        standing_count = SUCCESS_MESSAGE
        SUCCESS_MESSAGE = None
        return render_template_string(SUCCESS_PAGE, standing_count=standing_count)

    # 게임 모드가 선택되지 않았으면 모드 선택 화면
    if GAME_MODE is None:
        future_avg = sum(STANDING_HISTORY["future"]) / len(STANDING_HISTORY["future"]) if STANDING_HISTORY["future"] else 0
        real_avg = sum(STANDING_HISTORY["real"]) / len(STANDING_HISTORY["real"]) if STANDING_HISTORY["real"] else 0
        return render_template_string(MODE_SELECT_PAGE,
                                     future_history=STANDING_HISTORY["future"],
                                     real_history=STANDING_HISTORY["real"],
                                     future_avg=round(future_avg, 1),
                                     real_avg=round(real_avg, 1))

    # 비교 모드이고 시나리오가 선택되지 않았으면 시나리오 선택 화면
    if GAME_MODE == "compare" and COMPARISON_DATA is None:
        scenarios_with_idx = list(enumerate(COMPARISON_SCENARIOS))
        return render_template_string(COMPARE_SELECT_PAGE, scenarios=scenarios_with_idx)

    # 커스텀 모드이고 호선이 선택되지 않았으면 설정 화면
    if not CURRENT_LINE:
        import json
        # 비교 모드는 기록 표시 안 함
        if GAME_MODE == "compare":
            return render_template_string(SETUP_PAGE,
                                         lines=SUBWAY_LINES.keys(),
                                         line_data=json.dumps(SUBWAY_LINES),
                                         future_history=[],
                                         real_history=[],
                                         future_avg=0,
                                         real_avg=0)
        else:
            # 커스텀 모드는 기록 표시 안 함 (비교 모드 전용)
            return render_template_string(SETUP_PAGE,
                                         lines=SUBWAY_LINES.keys(),
                                         line_data=json.dumps(SUBWAY_LINES),
                                         future_history=[],
                                         real_history=[],
                                         future_avg=0,
                                         real_avg=0)

    current_station = STATIONS[CURRENT_STATION_IDX] if CURRENT_STATION_IDX < len(STATIONS) else "종점"
    recommended = get_recommended_seat()

    is_reverse = START_IDX > END_IDX  # 역방향 여부

    # 현재 역 이후의 남은 역들 (종착역까지만)
    if is_reverse:
        remaining_stations = STATIONS[END_IDX:CURRENT_STATION_IDX] if CURRENT_STATION_IDX > END_IDX else []
        total_in_route = START_IDX - END_IDX
        cur_idx = START_IDX - CURRENT_STATION_IDX
    else:
        remaining_stations = STATIONS[CURRENT_STATION_IDX + 1:END_IDX] if CURRENT_STATION_IDX < END_IDX - 1 else []
        total_in_route = END_IDX - START_IDX
        cur_idx = CURRENT_STATION_IDX - START_IDX

    # 사용자의 대기 순서 계산
    user_wait_position = 0
    if USER_STATE["waiting_at"]:
        seat_id = USER_STATE["waiting_at"]
        queue = SEATS[seat_id]["waiting_queue"]
        if "user" in queue:
            user_wait_position = queue.index("user") + 1

    return render_template_string(PAGE,
                                 seats=SEATS,
                                 cur_idx=cur_idx,
                                 line=CURRENT_LINE,
                                 direction=CURRENT_DIRECTION,
                                 current_station=current_station,
                                 total_stations=total_in_route,
                                 recommended_seat=recommended,
                                 remaining_stations=remaining_stations,
                                 user_state=USER_STATE,
                                 user_wait_position=user_wait_position,
                                 future_mode=FUTURE_MODE,
                                 is_compare_mode=(GAME_MODE == "compare"),
                                 comparison_phase=COMPARISON_PHASE)

@app.post("/start")
def start():
    global CURRENT_LINE, CURRENT_DIRECTION, CURRENT_STATION_IDX, STATIONS, SEATS, START_IDX, END_IDX, FUTURE_MODE

    CURRENT_LINE = request.form.get("line")
    CURRENT_DIRECTION = request.form.get("direction")
    current_station_name = request.form.get("current_station")
    FUTURE_MODE = request.form.get("future_mode") == "true"  # 체크박스 값 읽기

    if CURRENT_LINE in SUBWAY_LINES:
        line_info = SUBWAY_LINES[CURRENT_LINE]
        STATIONS = line_info["stations"]

        # 선택한 행선의 시작/종착 인덱스 가져오기
        if CURRENT_DIRECTION in line_info["branches"]:
            START_IDX, END_IDX = line_info["branches"][CURRENT_DIRECTION]
        else:
            START_IDX = 0
            END_IDX = len(STATIONS)

        # 현재 역 인덱스 찾기
        try:
            CURRENT_STATION_IDX = STATIONS.index(current_station_name)
        except ValueError:
            CURRENT_STATION_IDX = START_IDX

        # 좌석 초기화
        SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
        USER_STATE["seated_at"] = None
        USER_STATE["waiting_at"] = None
        USER_STATE["standing_count"] = 0
        initialize_seats()

    return redirect("/")

@app.post("/reset")
def reset():
    global CURRENT_LINE, CURRENT_DIRECTION, CURRENT_STATION_IDX, STATIONS, SEATS, USER_STATE, FUTURE_MODE, GAME_MODE, COMPARISON_DATA, COMPARISON_PHASE
    CURRENT_LINE = None
    CURRENT_DIRECTION = None
    CURRENT_STATION_IDX = 0
    STATIONS = []
    SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
    USER_STATE = {"seated_at": None, "waiting_at": None, "standing_count": 0}
    FUTURE_MODE = True
    GAME_MODE = None
    COMPARISON_DATA = None
    COMPARISON_PHASE = None
    return redirect("/")

@app.post("/clear_history")
def clear_history():
    global STANDING_HISTORY
    STANDING_HISTORY = {"future": [], "real": []}
    return redirect("/")

@app.route("/continue")
def continue_after_success():
    """착석 성공 후 다음 단계로 이동"""
    global GAME_MODE, COMPARISON_PHASE, COMPARISON_DATA, FUTURE_MODE

    # 비교 모드이고 아이디어 반영 단계였다면 현실 세계 단계로
    if GAME_MODE == "compare" and COMPARISON_PHASE == "future":
        COMPARISON_PHASE = "real"
        FUTURE_MODE = False
        # 동일한 조건으로 다시 시작
        return redirect("/start_comparison_real")

    # 그 외에는 초기화면으로 (게임 모드 초기화)
    GAME_MODE = None
    COMPARISON_DATA = None
    COMPARISON_PHASE = None
    FUTURE_MODE = True
    return redirect("/")

@app.post("/select_mode")
def select_mode():
    """모드 선택"""
    global GAME_MODE
    GAME_MODE = request.form.get("mode")
    return redirect("/")

@app.post("/start_comparison")
def start_comparison():
    """비교 모드 시작 - 시나리오 선택"""
    global COMPARISON_DATA, COMPARISON_PHASE, FUTURE_MODE

    scenario_idx = int(request.form.get("scenario_idx"))
    COMPARISON_DATA = COMPARISON_SCENARIOS[scenario_idx]
    COMPARISON_PHASE = "future"
    FUTURE_MODE = True

    # 선택한 조건으로 게임 시작
    return redirect("/start_comparison_real")

@app.route("/start_comparison_real")
def start_comparison_real():
    """비교 모드 - 조건에 따라 게임 시작"""
    global CURRENT_LINE, CURRENT_DIRECTION, CURRENT_STATION_IDX, STATIONS, SEATS, USER_STATE, START_IDX, END_IDX

    if COMPARISON_DATA is None:
        return redirect("/")

    CURRENT_LINE = COMPARISON_DATA["line"]
    CURRENT_DIRECTION = COMPARISON_DATA["direction"]
    current_station_name = COMPARISON_DATA["station"]
    max_stops = COMPARISON_DATA.get("max_stops", 15)  # 최대 정거장 수

    if CURRENT_LINE in SUBWAY_LINES:
        line_info = SUBWAY_LINES[CURRENT_LINE]
        STATIONS = line_info["stations"]

        # 선택한 행선의 시작/종착 인덱스 가져오기
        if CURRENT_DIRECTION in line_info["branches"]:
            START_IDX, original_end_idx = line_info["branches"][CURRENT_DIRECTION]
        else:
            START_IDX = 0
            original_end_idx = len(STATIONS)

        # 현재 역 인덱스 찾기
        try:
            CURRENT_STATION_IDX = STATIONS.index(current_station_name)
        except ValueError:
            CURRENT_STATION_IDX = START_IDX

        # 비교 모드에서는 현재 역에서 최대 max_stops 정거장까지만
        is_reverse = START_IDX > original_end_idx
        if is_reverse:
            # 역방향: 현재 역에서 max_stops만큼 뒤로
            END_IDX = max(CURRENT_STATION_IDX - max_stops, original_end_idx)
        else:
            # 정방향: 현재 역에서 max_stops만큼 앞으로
            END_IDX = min(CURRENT_STATION_IDX + max_stops + 1, original_end_idx)

        # 좌석 초기화
        SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
        USER_STATE["seated_at"] = None
        USER_STATE["waiting_at"] = None
        USER_STATE["standing_count"] = 0
        initialize_seats()

    return redirect("/")

@app.post("/sit")
def sit():
    seat_id = int(request.form["seat_id"])
    destination_station = request.form.get("destination_station", "")

    if not destination_station or destination_station not in STATIONS:
        return redirect("/")

    # 목적지까지 남은 정거장 계산
    try:
        destination_idx = STATIONS.index(destination_station)
        stops_left = destination_idx - CURRENT_STATION_IDX

        if stops_left <= 0 or destination_idx >= END_IDX:
            return redirect("/")

        SEATS[seat_id]["stops_left"] = stops_left
        SEATS[seat_id]["status"] = "occupied"
        SEATS[seat_id]["updated"] = nowstr()
        SEATS[seat_id]["destination"] = destination_station
    except (ValueError, IndexError):
        pass

    return redirect("/")

@app.post("/wait")
def wait():
    """사용자가 좌석 앞에 서기"""
    global CURRENT_LINE, CURRENT_DIRECTION, CURRENT_STATION_IDX, STATIONS, SEATS, USER_STATE

    seat_id = int(request.form["seat_id"])

    # 이미 다른 곳에서 대기 중이면 제거
    if USER_STATE["waiting_at"]:
        old_seat = USER_STATE["waiting_at"]
        if "user" in SEATS[old_seat]["waiting_queue"]:
            SEATS[old_seat]["waiting_queue"].remove("user")

    # 이미 착석 중이면 취소
    if USER_STATE["seated_at"]:
        USER_STATE["seated_at"] = None

    # 좌석이 비어있고 대기자가 없으면 바로 착석 성공
    if SEATS[seat_id]["status"] == "free" and len(SEATS[seat_id]["waiting_queue"]) == 0:
        global SUCCESS_MESSAGE, GAME_MODE, COMPARISON_DATA, COMPARISON_PHASE, FUTURE_MODE

        # 기록 저장 (비교 모드에서만)
        standing_count = USER_STATE["standing_count"]
        if GAME_MODE == "compare":
            mode_key = "future" if FUTURE_MODE else "real"
            # 기록 추가 (최대 10개, FIFO)
            STANDING_HISTORY[mode_key].append(standing_count)
            if len(STANDING_HISTORY[mode_key]) > 10:
                STANDING_HISTORY[mode_key].pop(0)

        # 성공 메시지 설정
        SUCCESS_MESSAGE = standing_count

        # "처음부터" 버튼과 동일하게 초기화 (기록은 유지)
        # 비교 모드가 아니면 게임 모드 변수도 초기화
        if GAME_MODE != "compare" or COMPARISON_PHASE == "real":
            # 커스텀 모드이거나 비교 모드의 real 단계가 끝나면 모드 초기화
            pass  # continue_after_success에서 처리

        CURRENT_LINE = None
        CURRENT_DIRECTION = None
        CURRENT_STATION_IDX = 0
        STATIONS = []
        SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
        USER_STATE = {"seated_at": None, "waiting_at": None, "standing_count": 0}

        # 초기화면으로 리디렉션 (축하 화면이 먼저 표시됨)
        return redirect("/")
    else:
        # 대기열에 추가 (최대 1명만)
        if "user" not in SEATS[seat_id]["waiting_queue"] and len(SEATS[seat_id]["waiting_queue"]) == 0:
            SEATS[seat_id]["waiting_queue"].append("user")
            USER_STATE["waiting_at"] = seat_id
            USER_STATE["seated_at"] = None

    return redirect("/")

@app.post("/free")
def free():
    seat_id = int(request.form["seat_id"])
    SEATS[seat_id] = {"stops_left": None, "status": "free", "updated": nowstr(), "destination": None, "waiting_queue": SEATS[seat_id]["waiting_queue"]}
    return redirect("/")

@app.post("/tick")
def tick():
    global CURRENT_STATION_IDX, USER_STATE, CURRENT_LINE, CURRENT_DIRECTION, STATIONS, SEATS

    is_reverse = START_IDX > END_IDX  # 역방향 여부

    # 종착역 전까지만 이동
    if is_reverse:
        # 역방향: 인덱스가 감소
        if CURRENT_STATION_IDX > END_IDX + 1:
            CURRENT_STATION_IDX -= 1
    else:
        # 정방향: 인덱스가 증가
        if CURRENT_STATION_IDX < END_IDX - 1:
            CURRENT_STATION_IDX += 1

    # 사용자가 서있으면 카운트 증가
    if not USER_STATE["seated_at"]:
        USER_STATE["standing_count"] += 1

    seated_success = False  # 이번 틱에서 착석 성공 여부

    for seat_id, s in SEATS.items():
        # 1. 착석자의 남은 정거장 감소
        if s["status"] != "free" and s["stops_left"] is not None:
            if s["stops_left"] > 0:
                s["stops_left"] -= 1
                s["updated"] = nowstr()

            # 2. 0이 되면 하차 (좌석 비우기)
            if s["stops_left"] == 0:
                # 사용자가 이 좌석에 앉아있었으면 상태 업데이트
                if USER_STATE["seated_at"] == seat_id:
                    USER_STATE["seated_at"] = None

                s["status"] = "free"
                s["destination"] = None
                s["stops_left"] = None
                s["updated"] = nowstr()

        # 3. 좌석이 비면 전체 대기자 중 가장 가까운 사람이 착석
        # (더 이상 해당 좌석의 대기열만 보지 않음)

    # 모든 좌석을 순회한 후, 비어있는 좌석마다 가장 가까운 대기자 찾기
    for empty_seat_id, s in SEATS.items():
        if s["status"] == "free":
            # 모든 좌석의 대기자 리스트 수집
            all_waiters = []
            for waiter_seat_id, waiter_info in SEATS.items():
                if len(waiter_info["waiting_queue"]) > 0:
                    for person in waiter_info["waiting_queue"]:
                        all_waiters.append({
                            "person": person,
                            "waiting_at": waiter_seat_id,
                            "distance": weighted_distance(empty_seat_id, waiter_seat_id)
                        })

            # 거리 순으로 정렬 (거리 → 좌석 번호 왼쪽 우선)
            if all_waiters:
                all_waiters.sort(key=lambda w: (w["distance"], w["waiting_at"]))
                next_waiter = all_waiters[0]
                next_person = next_waiter["person"]
                from_seat = next_waiter["waiting_at"]

                # 대기열에서 제거
                SEATS[from_seat]["waiting_queue"].remove(next_person)

                if next_person == "user":
                    global SUCCESS_MESSAGE, GAME_MODE, COMPARISON_DATA, COMPARISON_PHASE, FUTURE_MODE

                    # 사용자가 착석 성공 - 기록 저장 (비교 모드에서만)
                    standing_count = USER_STATE["standing_count"]
                    if GAME_MODE == "compare":
                        mode_key = "future" if FUTURE_MODE else "real"
                        # 기록 추가 (최대 10개, FIFO)
                        STANDING_HISTORY[mode_key].append(standing_count)
                        if len(STANDING_HISTORY[mode_key]) > 10:
                            STANDING_HISTORY[mode_key].pop(0)

                    # 성공 메시지 설정
                    SUCCESS_MESSAGE = standing_count

                    # "처음부터" 버튼과 동일하게 초기화 (기록은 유지)
                    # 비교 모드가 아니면 게임 모드 변수도 초기화
                    if GAME_MODE != "compare" or COMPARISON_PHASE == "real":
                        # 커스텀 모드이거나 비교 모드의 real 단계가 끝나면 모드 초기화
                        pass  # continue_after_success에서 처리

                    CURRENT_LINE = None
                    CURRENT_DIRECTION = None
                    CURRENT_STATION_IDX = 0
                    STATIONS = []
                    SEATS = {i: {"stops_left": None, "status": "free", "updated": None, "destination": None, "waiting_queue": []} for i in range(1, 15)}
                    USER_STATE = {"seated_at": None, "waiting_at": None, "standing_count": 0}

                    seated_success = True  # 착석 성공 플래그
                else:
                    # NPC가 착석 - 랜덤 목적지 할당
                    if is_reverse:
                        # 역방향
                        if CURRENT_STATION_IDX > END_IDX + 1:
                            destination_idx = random.randint(END_IDX + 1, CURRENT_STATION_IDX - 1)
                            # 인덱스 범위 검증
                            if destination_idx < len(STATIONS):
                                destination = STATIONS[destination_idx]
                                stops_left = CURRENT_STATION_IDX - destination_idx

                                s["status"] = "occupied"
                                s["stops_left"] = stops_left
                                s["destination"] = destination
                                s["updated"] = nowstr()
                    else:
                        # 정방향
                        if CURRENT_STATION_IDX < END_IDX - 1:
                            # END_IDX가 STATIONS 길이를 초과하지 않도록 제한
                            max_end = min(END_IDX - 1, len(STATIONS) - 1)
                            if CURRENT_STATION_IDX < max_end:
                                destination_idx = random.randint(CURRENT_STATION_IDX + 1, max_end)
                                destination = STATIONS[destination_idx]
                                stops_left = destination_idx - CURRENT_STATION_IDX

                                s["status"] = "occupied"
                                s["stops_left"] = stops_left
                                s["destination"] = destination
                                s["updated"] = nowstr()

        # 4. 각 좌석의 대기열에서 랜덤하게 사람들이 하차 (30% 확률)
        if len(s["waiting_queue"]) > 0:
            new_queue = []
            for person in s["waiting_queue"]:
                if person == "user":
                    new_queue.append(person)  # 사용자는 항상 유지
                else:
                    if random.random() > 0.3:  # 70% 확률로 계속 대기
                        new_queue.append(person)
            s["waiting_queue"] = new_queue

    # 5. NPC가 똑똑하게 대기 좌석 선택 (아이디어 반영 모드) 또는 랜덤 선택 (실제 세계 모드)
    if FUTURE_MODE:
        # 아이디어 반영 모드: NPC가 가장 빨리 비워질 좌석을 선택
        # 대기자가 없는 착석 중인 좌석들 찾기
        available_seats = {sid: info for sid, info in SEATS.items()
                          if info["status"] != "free"
                          and info["stops_left"] is not None
                          and len(info["waiting_queue"]) == 0}

        if available_seats and random.random() > 0.5:  # 50% 확률로 NPC 추가
            # 가장 빨리 비워질 좌석 찾기
            best_seat = min(available_seats.items(), key=lambda x: x[1]["stops_left"])
            best_seat_id = best_seat[0]
            SEATS[best_seat_id]["waiting_queue"].append(f"person_{best_seat_id}_{random.randint(1000, 9999)}")
    else:
        # 실제 세계 모드: 랜덤하게 선택 (착석 중인 좌석에만)
        for seat_id, s in SEATS.items():
            if random.random() > 0.5 and len(s["waiting_queue"]) == 0 and s["status"] != "free":
                s["waiting_queue"].append(f"person_{seat_id}_{random.randint(1000, 9999)}")

    # 착석 성공 시 초기화면으로
    if seated_success:
        return redirect("/")

    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
