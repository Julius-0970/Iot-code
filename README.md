# 🏥 Healthcare DAQ Serial Client

라즈베리파이에서 헬스케어 DAQ 장비의 C++ 패킷을 수신하고, WebSocket을 통해 FastAPI 서버로 실시간 전송하는 Python 클라이언트입니다.

---

## 📌 프로젝트 개요

```
[헬스케어 DAQ 장비] --Serial(UART)--> [Raspberry Pi] --WebSocket--> [FastAPI 서버] ---> 메인 서버 및 웹페이지
```

- DAQ 장비에서 생체신호 데이터를 Serial(UART) 통신으로 수신
- 수신된 바이너리 패킷을 파싱 후 WebSocket으로 서버에 전송
- Tkinter 기반 GUI를 통해 센서 선택 및 사용자 이메일 입력

---

## 📂 파일 구조

```
├── DAQ_Serial.py       # 시리얼 통신 및 WebSocket 전송 클래스
├── main.py             # Tkinter GUI 진입점
├── *.png               # 센서 버튼 이미지 (선택적)
└── app.log             # 실행 로그 (자동 생성)
```

---

## 🔌 지원 센서

| 센서명 | 설명 | 요청 CMD | 응답 CMD |
|--------|------|----------|----------|
| `ECG` | 심전도 | `0x11` | `0x12` |
| `EMG` | 근전도 | `0x21` | `0x22` |
| `EOG` | 안구전위 | `0x31` | `0x32` |
| `NIBP` | 비침습 혈압 | `0x41` | `0x42` |
| `SPO2` | 혈중 산소 포화도 | `0x51` | `0x52` |
| `AIRFLOW` | 공기 흐름 | `0x61` | `0x62` |
| `GSR` | 피부 전기 반응 | `0x81` | `0x82` |
| `TEMP` | 체온 | `0xA1` | `0xA2` |

---

## 📦 패킷 구조

DAQ 장비와의 통신은 다음 바이너리 프로토콜을 따릅니다.

```
[ SOP(0xF7) | CMD | DATA(3 bytes) | EOP(0xFA) ]
```

| 필드 | 값 | 설명 |
|------|----|------|
| SOP | `0xF7` | 패킷 시작 |
| CMD | 명령어 ID | 요청/응답 구분 |
| DATA | 3 bytes | 데이터 페이로드 |
| EOP | `0xFA` | 패킷 종료 |

수신 패킷은 두 가지 길이를 지원합니다:

- **10 bytes** : 정형 데이터 (수치형 센서값)
- **86 bytes** : 비정형 데이터 (파형 데이터 등)

---

## ⚙️ 환경 설정

### 요구사항

- Python 3.8 이상
- Raspberry Pi (또는 `/dev/ttyAMA0` 지원 환경)

### 패키지 설치

```bash
pip install pyserial websockets pillow getmac
```

### 시리얼 포트 설정

`DAQ_Serial.py` 내 시리얼 설정:

```python
port     = '/dev/ttyAMA0'
baudrate = 115200
bytesize = 8 bits
parity   = None
stopbits = 1
```

### WebSocket 서버 URL

`main.py`의 `generate_sensor_uri()` 함수에서 기본 URL을 수정합니다.

```python
base_url = "wss://your-server-url/ws"
# 최종 URI 형태: wss://your-server-url/ws/{username}/{sensor_type}
```

---

## 🚀 실행 방법

```bash
python main.py
```

1. GUI 실행 후 **사용자 Email** 입력
2. 원하는 **센서 버튼** 클릭
3. 데이터 수집 시작 → WebSocket으로 서버에 실시간 전송
4. 동일 버튼 재클릭 시 전송 중단

---

## 🖥️ GUI 구성

```
┌─────────────────────────────────────────┐
│  실시간 데이터 수집                    [✖] │
├─────────────────────────────────────────┤
│  사용자 Email: [___________________]    │
│                                         │
│  [ECG]   [EMG]   [EOG]   [NIBP]        │
│  [SPO2]  [AIRFLOW] [GSR] [TEMP]        │
│                                         │
│  상태: ECG 데이터를 전송 중입니다...      │
└─────────────────────────────────────────┘
```

- 센서 버튼 클릭 → 해당 센서 데이터 수집 시작
- 다른 센서 클릭 시 → 전환 여부 확인 팝업
- 실행 중 동일 센서 클릭 → 중단 여부 확인 팝업

---

## 🔑 장치 식별

장치 고유 ID는 **MAC 주소**를 사용합니다.

```python
from getmac import get_mac_address
device_id = get_mac_address()
```

WebSocket 연결 시 `device_id`와 `user_name`이 서버로 먼저 전송됩니다.

---

## 📋 로깅

실행 중 모든 이벤트는 콘솔과 `app.log` 파일에 동시 기록됩니다.

```
2024-01-01 12:00:00 - INFO - 시리얼 포트 초기화 완료.
2024-01-01 12:00:01 - INFO - ECG 데이터 전송 작업 시작.
2024-01-01 12:00:01 - INFO - 패킷 전송됨: f71100000000fa
```

---

## ⚠️ 주의사항

- `/dev/ttyAMA0` 포트 접근 권한이 필요합니다. (`sudo usermod -aG dialout $USER`)
- 센서 버튼 이미지(`ecg.png`, `emg.png` 등)가 없어도 텍스트 버튼으로 정상 동작합니다.
- WebSocket 서버가 실행 중이어야 데이터 전송이 가능합니다.
