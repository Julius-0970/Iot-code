# NIBP_serial.py

# DAQ_serial 모듈에서 DaqSerial 클래스와 혈압 데이터 요청 프로토콜 ID 상수 가져오기
from DAQ_Serial import DaqSerial, RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_NIBP
from daq_handler import setup_daq_serial, read_data

# DaqSerial 인스턴스 생성 및 시리얼 통신 열기
daq_serial = setup_daq_serial(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_NIBP)
# 실제로 데이터를 읽어오는 로직
read_data(daq_serial)


# 단일 값이 두개만 들어와서 이부분은 추후 체크가 필요함
