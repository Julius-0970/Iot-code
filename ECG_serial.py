# ECG.serial.py

# DAQ_serial 모듈에서 DaqSerial 클래스와 ECG 데이터 요청 프로토콜 ID 상수 가져오기
from DAQ_Serial import DaqSerial, RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG
import time

# DaqSerial 인스턴스 생성 및 시리얼 통신 열기
daq_serial = DaqSerial()  # DaqSerial 객체 생성
daq_serial.open_serial()  # 시리얼 포트 열기
daq_serial.set_command(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG)  # 명령 설정 (ECG 데이터 요청)
daq_serial.send_request(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG)  # ECG 데이터 요청 전송

try:
    # 무한 루프를 통해 데이터 수신 대기
    while True:
        daq_serial.on_ready_read()  # 데이터가 준비되면 읽기
        time.sleep(1)  # 1초 대기
finally:
    # 시리얼 통신 닫기
    daq_serial.close_serial()  # 종료 시 시리얼 포트 닫기
