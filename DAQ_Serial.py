import serial
from queue import Queue

# 프로토콜 시작 및 종료 코드
RASPI_PROTOCOL_TO_DAQ_SOP = 0xF7  # Start of Packet
RASPI_PROTOCOL_TO_DAQ_EOP = 0xFA  # End of Packet

# 송신 명령어 상수 정의
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_STOP = 0xF1  # 데이터 전송 정지 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG = 0x11   # ECG 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG = 0x21   # EOG 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EOG = 0x31   # EMG 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_NIBP = 0x41    # 혈압 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_SPO2 = 0x51  # 혈중 산소 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_AIR_FLOW = 0x61  # 호흡 데이터 요청
#RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_GLUCOMETER = 0x72
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_GSR = 0x81   # GSR 데이터 요청
#RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_BODY_POSITION = 0x92
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE = 0xA1  # 체온 데이터 요청
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_BPM = 0xB1    # 혈압 데이터 요청

# 수신 명령어 상수 정의
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_ECG = 0x12
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EMG = 0x22
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EOG = 0x32
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_NIBP = 0x42
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_SPO2 = 0x52
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_AIR_FLOW = 0x62
#RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_GLUCOMETER = 0x72
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_GSR = 0x82
#RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_BODY_POSITION = 0x92
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_TEMPERATURE = 0xA2
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_BPM = 0xB2

class DaqSerial:
    def __init__(self):
        # 기본 명령어를 전송 정지로 설정
        self.command = RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_STOP
        # 데이터를 수신할 때 사용할 패킷 버퍼
        self.receive_packet = bytearray()
        # 수신된 패킷을 저장할 큐
        self.data_queue = Queue()

        # 시리얼 포트 설정
        self.serial_port = serial.Serial(
            port='/dev/ttyAMA0',       # 사용할 포트
            baudrate=115200,           # 통신 속도
            bytesize=serial.EIGHTBITS, # 데이터 비트 설정
            parity=serial.PARITY_NONE, # 패리티 비트 없음
            stopbits=serial.STOPBITS_ONE, # 스톱 비트
            timeout=1                   # 타임아웃 설정
        )

    def set_command(self, command):
        """
        전송할 명령어를 설정하고 수신 패킷을 초기화합니다.
        """
        self.command = command
        self.receive_packet.clear()  # 이전 패킷을 비워줌

    def get_command(self):
        """
        현재 설정된 명령어를 반환합니다.
        """
        return self.command

    def open_serial(self):
        """
        시리얼 포트를 여는 함수.
        이미 열려 있으면 상태만 출력하고, 아니라면 열기를 시도합니다.
        """
        if self.serial_port.is_open:
            print("Serial port already open.")
        else:
            self.serial_port.open()
            if self.serial_port.is_open:
                print("Serial port opened successfully.")
            else:
                print("Failed to open serial port.")

    def on_ready_read(self):
        """
        시리얼 포트에서 데이터를 읽어와서 패킷을 수신하고 처리합니다.
        패킷의 SOP와 EOP를 확인하여 유효한 데이터인지 검증하고 명령어 ID에 따라 처리합니다.
        """
        if self.command == RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_STOP:
            # 데이터 전송 정지 상태면 읽지 않음
            return

        while self.serial_port.in_waiting > 0:
            # 수신 대기 중인 모든 데이터를 읽음
            data = self.serial_port.read(self.serial_port.in_waiting)
            self.receive_packet.extend(data)

            # 패킷의 시작(SOP) 위치 찾기
            sop_index = self.receive_packet.find(RASPI_PROTOCOL_TO_DAQ_SOP)
            if sop_index == -1:
                # SOP를 찾지 못하면 패킷 초기화
                self.receive_packet.clear()
                continue

            # 데이터 사이즈를 확인하여 전체 패킷 길이를 체크
            if len(self.receive_packet) >= sop_index + 2:
                data_size = self.receive_packet[sop_index + 2]
                total_length = sop_index + 3 + data_size + 1  # SOP, CMD, SIZE, DATA, EOP
                if len(self.receive_packet) >= total_length:
                    # 패킷이 완료되었고 EOP 위치가 맞는지 확인
                    if self.receive_packet[total_length - 1] == RASPI_PROTOCOL_TO_DAQ_EOP:
                        # 명령어 ID 추출 및 처리
                        command_id = self.receive_packet[sop_index + 1]

                        # 명령어 ID에 따른 데이터 유형 출력
                        if command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_ECG:
                            print("Received ECG data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EMG:
                            print("Received EMG data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EOG:
                            print("Received EOG data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_NIBP:
                            print("Received Blood Pressure data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_SPO2:
                            print("Received SpO2 data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_AIR_FLOW:
                            print("Received Air Flow data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_GLUCOMETER:
                            print("Received Glucometer data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_GSR:
                            print("Received GSR data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_BODY_POSITION:
                            print("Received Body Position data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_TEMPERATURE:
                            print("Received Temperature data")
                        elif command_id == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_BPM:
                            print("Received BPM data")
                        else:
                            print("Unknown data type received")

                        # 수신 패킷 큐에 추가
                        packet = self.receive_packet[sop_index:total_length]
                        self.data_queue.put(packet)
                        self.receive_packet = self.receive_packet[total_length:]

    def send_request(self, command):
        """
        명령어에 따른 패킷을 생성하여 시리얼 포트로 전송합니다.
        """
        packet = bytearray([RASPI_PROTOCOL_TO_DAQ_SOP, command, 0x00, 0x00, 0x00, RASPI_PROTOCOL_TO_DAQ_EOP])
        self.serial_port.write(packet)
        print(f"Sent packet: {packet.hex()}")

    def close_serial(self):
        """
        시리얼 포트를 닫는 함수.
        """
        if self.serial_port.is_open:
            self.serial_port.close()
            print("Serial port closed.")
        else:
            print("Serial port is already closed.")

