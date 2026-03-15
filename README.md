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

```
┌──────────────────┐     UART/Serial      ┌──────────────────────┐
│  Healthcare DAQ  │ ──────────────────►  │    Raspberry Pi      │
│  (C++ Firmware)  │    /dev/ttyAMA0      │                      │
│                  │    115200 baud       │  ┌────────────────┐  │
│  Binary Packet   │                      │  │  DAQ_Serial.py │  │
│  [SOP|CMD|DATA   │                      │  │  - 패킷 파싱    │  │
│      |EOP]       │                      │  │  - 버퍼 관리    │  │
└──────────────────┘                      │  └───────┬────────┘  │
                                          │          │ asyncio   │
                                          │  ┌───────▼────────┐  │
                                          │  │    app.py      │  │
                                          │  │  - Tkinter GUI │  │
                                          │  │  - 센서 선택    │  │
                                          │  └───────┬────────┘  │
                                          └──────────┼───────────┘
                                                     │ WebSocket (wss://)
                                                     ▼
                                          ┌──────────────────────┐
                                          │   FastAPI Server     │
                                          │  /ws/{user}/{sensor} │
                                          └──────────────────────┘
```

<br>

## 📦 패킷 구조

DAQ 장비와의 통신은 다음 바이너리 프로토콜을 따릅니다.

```
┌────────┬──────────┬────────────────┬────────┐
│  SOP   │   CMD    │    DATA        │  EOP   │
│ 0xF7   │  1 byte  │    3 bytes     │ 0xFA   │
└────────┴──────────┴────────────────┴────────┘
```

수신 패킷은 두 가지 길이를 지원합니다.

- **10 bytes** : 정형 데이터 (수치형 센서값)
- **86 bytes** : 비정형 데이터 (파형 데이터 등)

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
├── *.png               # 센서 버튼 이미지 (선택적)
└── app.log             # 실행 로그 (자동 생성)
```

<br>

## 🔍 패킷 파싱 구조

### 1. 송신 패킷 — 센서 요청

GUI에서 센서를 선택하면 아래 구조의 패킷을 DAQ 장비로 전송합니다.

```
Index  [ 0  |  1  |  2  |  3  |  4  |  5  ]
Value  [0xF7| CMD |0x00 |0x00 |0x00 |0xFA ]
        SOP   명령  ←── 예약 필드(3 bytes) ──►  EOP
```

예시 — ECG 요청 시 전송되는 패킷:

```python
packet = bytearray([0xF7, 0x11, 0x00, 0x00, 0x00, 0xFA])
#                   SOP   ECG  data  data  data   EOP
serial_port.write(packet)
```

---

### 2. 수신 패킷 — 센서 응답

DAQ 장비로부터 수신한 데이터는 버퍼에 누적한 뒤, SOP(`0xF7`)와 EOP(`0xFA`)를 기준으로 패킷 경계를 탐지합니다.

```python
# 버퍼에서 SOP 탐색
sop_index = buffer.find(0xF7)

# SOP 이후 EOP 탐색
eop_index = buffer.find(0xFA, sop_index)

# 패킷 추출 및 버퍼에서 제거
packet = buffer[sop_index:eop_index + 1]
del buffer[:eop_index + 1]
```

---

### 3. 패킷 길이에 따른 데이터 분류

수신 패킷은 데이터 종류에 따라 길이가 달라집니다.

```
■ 정형 데이터 (10 bytes) — 수치형 센서값
┌──────┬─────┬──────────────────────┬──────┐
│ 0xF7 │ CMD │   DATA  (7 bytes)    │ 0xFA │
└──────┴─────┴──────────────────────┴──────┘

■ 비정형 데이터 (86 bytes) — ECG/EMG 등 파형 데이터
┌──────┬─────┬──────────────────────┬──────┐
│ 0xF7 │ CMD │   DATA  (83 bytes)   │ 0xFA │
└──────┴─────┴──────────────────────┴──────┘
```

```python
if len(packet) == 10:    # 정형 — NIBP, SPO2, TEMP 등
    await websocket.send(packet)
elif len(packet) == 86:  # 비정형 — ECG, EMG, EOG 등 파형
    await websocket.send(packet)
else:
    logging.warning(f"잘못된 패킷 길이: {len(packet)}")
```

---

### 4. 비동기 수신 흐름

시리얼 수신과 WebSocket 전송은 `asyncio`로 처리하며, Tkinter GUI 블로킹을 방지하기 위해 별도 스레드에서 이벤트 루프를 실행합니다.

```
[ Tkinter Main Thread ]
        │
        │  asyncio.run_coroutine_threadsafe()
        ▼
[ asyncio Event Loop Thread ]
        │
        ├── serial.read()  ──►  buffer에 누적
        │                            │
        │                    SOP/EOP 탐지 및 패킷 추출
        │                            │
        └── websocket.send(packet) ◄─┘
```

<br>

## 🖥️ 사용 방법

```
┌──────────────────────────────────────────────┐
│  실시간 데이터 수집                        [✖] │
├──────────────────────────────────────────────┤
│                                              │
│  사용자 Email  [ user@example.com          ] │
│                                              │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐  │
│  │  ECG   │ │  EMG   │ │  EOG   │ │ NIBP │  │
│  └────────┘ └────────┘ └────────┘ └──────┘  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────┐  │
│  │  SPO2  │ │AIRFLOW │ │  GSR   │ │ TEMP │  │
│  └────────┘ └────────┘ └────────┘ └──────┘  │
│                                              │
│  🔵 ECG 데이터를 전송 중입니다...              │
└──────────────────────────────────────────────┘
```

1. **사용자 Email** 입력
2. 원하는 **센서 버튼** 클릭 → 데이터 수집 및 전송 시작
3. 동일 버튼 재클릭 → 전송 중단
4. 다른 센서 버튼 클릭 → 전환 여부 확인 후 전환

> 센서 이미지 파일(`ecg.png` 등)이 없어도 텍스트 버튼으로 정상 동작합니다.

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
