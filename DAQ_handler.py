from DAQ_Serial import DaqSerial
import time

def setup_daq_serial(protocol_id):
    daq_serial = DaqSerial()  # DaqSerial 객체 생성
    daq_serial.open_serial()  # 시리얼 포트 열기
    daq_serial.set_command(protocol_id)  # 명령 설정 (데이터 요청)
    daq_serial.send_request(protocol_id)  # 데이터 요청 전송
    return daq_serial

def read_data(daq_serial):
    try:
        # 무한 루프를 통해 데이터 수신 대기
        while True:
            daq_serial.on_ready_read()  # 데이터가 준비되면 읽기
            time.sleep(1)  # 1초 대기
    finally:
        # 시리얼 통신 닫기
        daq_serial.close_serial()  # 종료 시 시리얼 포트 닫기
