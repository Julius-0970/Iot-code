# 🏥 Healthcare DAQ Serial Client

> 헬스케어 DAQ 장비의 생체신호를 실시간으로 수집하고 WebSocket을 통해 서버로 전송하는 Raspberry Pi 클라이언트

<br>

## 📖 프로젝트 배경

병원 및 연구 환경에서 사용되는 헬스케어 DAQ(Data Acquisition) 장비는 ECG, EMG 등 다양한 생체신호를 측정합니다. 해당 장비의 통신 프로토콜은 원래 C++로 작성되어 있었으나, **C++ 환경 없이 Python만으로 동일한 동작을 구현하기 위해 C++ 바이너리 프로토콜을 직접 분석하고 Python으로 재설계**했습니다.

재구현한 클라이언트는 Raspberry Pi 위에서 동작하며, 수집한 데이터를 WebSocket을 통해 FastAPI 서버로 실시간 전달합니다. 현장에서 의료진이 간편하게 센서를 선택하고 데이터를 즉시 수집할 수 있도록 **Tkinter GUI**도 함께 제공합니다.

<br>

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| Language | Python 3.8+ |
| GUI | Tkinter, Pillow |
| 통신 | PySerial (UART), WebSockets |
| 비동기 처리 | asyncio, threading |
| 하드웨어 | Raspberry Pi, DAQ 장비 |
| 배포 환경 | Raspberry Pi OS |
| 기타 | getmac (장치 식별), logging |

<br>

## 🏗 시스템 아키텍처

![System Architecture](docs/architecture.svg)

```
┌──────────────────┐   UART /dev/ttyAMA0   ┌──────────────────────┐   WebSocket (wss://)   ┌──────────────────────┐
│   Healthcare DAQ │ ─────────────────────► │     Raspberry Pi     │ ──────────────────────► │    FastAPI Server    │
│  (C++ Firmware)  │      115200 baud       │  DAQ_Serial.py       │                         │ /ws/{user}/{sensor}  │
│  [SOP|CMD|DATA   │                        │  app.py (Tkinter)    │                         │                      │
│       |EOP]      │                        │                      │                         │                      │
└──────────────────┘                        └──────────────────────┘                         └──────────────────────┘
```

DAQ 장비에서 출력된 바이너리 패킷은 UART 시리얼 통신(`/dev/ttyAMA0`, 115200 baud)을 통해 Raspberry Pi로 전달됩니다. `DAQ_Serial.py`에서 패킷을 파싱하고, `app.py`의 Tkinter GUI를 통해 사용자가 선택한 센서 데이터를 WebSocket으로 FastAPI 서버에 실시간 전송합니다.

<br>

## 📦 패킷 구조

![Packet Structure](docs/packet_structure.svg)

### 송신 패킷

GUI에서 센서를 선택하면 6바이트 패킷을 DAQ 장비로 전송합니다.

| 필드 | 값 | 설명 |
|------|----|------|
| SOP | `0xF7` | 패킷 시작 마커 |
| CMD | 명령어 ID | 요청할 센서 종류 |
| DATA | `0x00` × 3 | 예약 필드 |
| EOP | `0xFA` | 패킷 종료 마커 |

### 수신 패킷

수신 패킷은 데이터 종류에 따라 길이가 달라집니다.

| 길이 | 구분 | 해당 센서 |
|------|------|----------|
| 10 bytes | 정형 데이터 (수치형) | NIBP, SPO2, TEMP |
| 86 bytes | 비정형 데이터 (파형) | ECG, EMG, EOG, GSR, AIRFLOW |

<br>

## 🔍 패킷 파싱 구조

![Parsing Flow](docs/parsing_flow.svg)

### SOP / EOP 기반 경계 탐지

버퍼에 수신 데이터를 누적한 뒤, SOP(`0xF7`)와 EOP(`0xFA`)를 기준으로 패킷 경계를 탐지하여 추출합니다.

```python
# SOP 탐색
sop_index = buffer.find(0xF7)

# SOP 이후 EOP 탐색
eop_index = buffer.find(0xFA, sop_index)

# 패킷 추출 및 버퍼 정리
packet = buffer[sop_index:eop_index + 1]
del buffer[:eop_index + 1]
```

### 길이 기반 데이터 분류

```python
if len(packet) == 10:    # 정형 — 수치형 센서값
    await websocket.send(packet)
elif len(packet) == 86:  # 비정형 — ECG, EMG 등 파형
    await websocket.send(packet)
else:
    logging.warning(f"잘못된 패킷 길이: {len(packet)}")
```

### 비동기 수신 흐름

Tkinter의 메인 스레드 블로킹을 방지하기 위해 별도 스레드에서 asyncio 이벤트 루프를 실행합니다.

```
[ Tkinter Main Thread ]
        │
        │  asyncio.run_coroutine_threadsafe()
        ▼
[ asyncio Event Loop Thread ]
        │
        ├── serial.read()  ──►  buffer에 누적
        │                            │
        │                    SOP/EOP 탐지 → 패킷 추출
        │                            │
        └── websocket.send(packet) ◄─┘
```

<br>

## 🔌 지원 센서

| 센서 | 설명 | 요청 CMD | 응답 CMD |
|------|------|----------|----------|
| `ECG` | 심전도 | `0x11` | `0x12` |
| `EMG` | 근전도 | `0x21` | `0x22` |
| `EOG` | 안구전위 | `0x31` | `0x32` |
| `NIBP` | 비침습 혈압 | `0x41` | `0x42` |
| `SPO2` | 혈중 산소 포화도 | `0x51` | `0x52` |
| `AIRFLOW` | 공기 흐름 | `0x61` | `0x62` |
| `GSR` | 피부 전기 반응 | `0x81` | `0x82` |
| `TEMP` | 체온 | `0xA1` | `0xA2` |

<br>

## 📂 파일 구조

```
├── app.py              # Tkinter GUI 진입점
├── DAQ_Serial.py       # 시리얼 통신 및 WebSocket 전송 클래스
├── docs/
│   ├── architecture.svg
│   ├── packet_structure.svg
│   └── parsing_flow.svg
├── *.png               # 센서 버튼 이미지 (선택적)
└── app.log             # 실행 로그 (자동 생성)
```

<br>

## 🔑 장치 식별

장치 고유 ID는 **MAC 주소**를 사용하며, WebSocket 연결 시 `device_id`와 `user_name`이 서버로 먼저 전송됩니다.

```python
from getmac import get_mac_address
device_id = get_mac_address()  # e.g. "aa:bb:cc:dd:ee:ff"
```

<br>

## 📋 로깅

모든 이벤트는 콘솔과 `app.log` 파일에 동시 기록됩니다.

```
2024-01-01 12:00:00 - INFO  - 시리얼 포트 초기화 완료.
2024-01-01 12:00:01 - INFO  - ECG 데이터 전송 작업 시작.
2024-01-01 12:00:01 - INFO  - 패킷 전송됨: f71100000000fa
2024-01-01 12:00:05 - INFO  - 정형 데이터 전송됨: f71200...fa
```
