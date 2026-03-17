import serial
from queue import Queue
import asyncio
import websockets
import logging  # 로깅 모듈 추가

# 프로토콜 시작 및 종료 코드
RASPI_PROTOCOL_TO_DAQ_SOP = 0xF7  # 패킷의 시작(SOP)
RASPI_PROTOCOL_TO_DAQ_EOP = 0xFA  # 패킷의 종료(EOP)

# 송신 명령어 상수 정의
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_STOP = 0xF1  # 데이터 전송 정지 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG = 0x11   # ECG 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG = 0x21   # EMG 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EOG = 0x31   # EOG 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_NIBP = 0x41  # NIBP 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_SPO2 = 0x51  # SPO2 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_AIR_FLOW = 0x61  # 공기 흐름 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_GSR = 0x81   # GSR 데이터 요청 명령
RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE = 0xA1  # 체온 데이터 요청 명령

# 수신 명령어 상수 정의
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_ECG = 0x12
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EMG = 0x22
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_EOG = 0x32
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_NIBP = 0x42
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_SPO2 = 0x52
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_AIR_FLOW = 0x62
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_GSR = 0x82
RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_TEMPERATURE = 0xA2

class DaqSerial:
    # 초기화
    def __init__(self, event_loop=None):

        # 기본 명령어를 전송 정지로 설정
        self.command = RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_STOP

        # 데이터를 수신할 때 사용할 패킷 버퍼
        self.receive_packet = bytearray()

        # 이벤트 루프 저장
        self.event_loop = event_loop

        # 시리얼 포트 설정
        try:
            self.serial_port = serial.Serial(
                port='/dev/ttyAMA0',            # 사용할 포트
                baudrate=115200,                # 통신 속도
                bytesize=serial.EIGHTBITS,      # 데이터 비트 설정
                parity=serial.PARITY_NONE,      # 패리티 비트 없음
                stopbits=serial.STOPBITS_ONE    # 스톱 비트 설정
                # timeout=1                      # 타임아웃 설정
            )
            logging.info("시리얼 포트 초기화 완료.")
        except serial.SerialException as e:
            logging.error(f"시리얼 포트 초기화 오류: {e}")
            self.serial_port = None

    # 명령어 설정, 수신 패킷 초기화
    def set_command(self, command):
        self.command = command
        self.receive_packet.clear()  # 이전 패킷을 비워줌
        logging.info(f"명령어 설정됨: {hex(command)}")

    # 설정 명령어(ID) 조회
    def get_command(self):
        logging.debug(f"현재 명령어 조회: {hex(self.command)}")
        return self.command

    # 포트 open
    def open_serial(self):
        if self.serial_port and self.serial_port.is_open:
            logging.info("시리얼 포트가 이미 열려 있습니다.")
        elif self.serial_port:
            try:
                self.serial_port.open()
                if self.serial_port.is_open:
                    logging.info("시리얼 포트가 성공적으로 열렸습니다.")
                else:
                    logging.error("시리얼 포트를 여는 데 실패했습니다.")
            except serial.SerialException as e:
                logging.error(f"시리얼 포트 열기 오류: {e}")
        else:
            logging.error("시리얼 포트가 초기화되지 않았습니다.")

    # 패킷 전송
    def send_request(self, command):
        if self.serial_port and self.serial_port.is_open:
            packet = bytearray([
                RASPI_PROTOCOL_TO_DAQ_SOP,  # SOP 추가
                command,  # 명령어 추가
                0x00,  # 데이터 필드 (예시로 채움)
                0x00,  # 데이터 필드 (예시로 채움)
                0x00,  # 데이터 필드 (예시로 채움)
                RASPI_PROTOCOL_TO_DAQ_EOP  # EOP 추가
            ])
            try:
                self.serial_port.write(packet)  # 시리얼 포트로 패킷 전송
                logging.info(f"패킷 전송됨: {packet.hex()}")
            except serial.SerialException as e:
                logging.error(f"패킷 전송 실패: {e}")
        else:
            logging.error("시리얼 포트가 열려 있지 않아 패킷을 전송할 수 없습니다.")

    # 포트 close
    def close_serial(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()  # 시리얼 포트 닫기
                logging.info("시리얼 포트가 성공적으로 닫혔습니다.")
            except serial.SerialException as e:
                logging.error(f"시리얼 포트 닫기 실패: {e}")
        else:
            logging.warning("시리얼 포트가 이미 닫혀 있습니다.")

    # 비동기 전송 함수 ( 사용자 이름, 명령어 ID, 서버 url )
    async def read_and_send(self, device_id, user_name, req_cmd, server_uri):
        if not device_id:
            logging.warning("디바이스 정보가 넘어오지 않았습니다.")
            return 
        if not user_name:
            logging.warning("사용자 이름이 입력되지 않았습니다.")
            return

        logging.info(f"{device_id} 장비의 {user_name}님이 데이터 수집을 시작했습니다.")
        logging.info(f"요청 명령어: {hex(req_cmd)}")

        # 버퍼 초기화
        buffer = bytearray()

        exit_ = False

        try:
            async with websockets.connect(server_uri) as websocket:
                # 사용자 이름과 장비 정보를 WebSocket 서버로 전송
                await websocket.send(device_id)
                await websocket.send(user_name)
                logging.info(f"사용자 이름 전송됨: {user_name}")
                
                while True:
                    if not self.serial_port:
                        logging.warning("시리얼 포트가 열려 있지 않습니다.")
                        continue

                    # 데이터 수신
                    if self.serial_port and self.serial_port.in_waiting > 0:
                        # 시리얼 포트에서 데이터 읽기
                        data = await self.event_loop.run_in_executor(
                            None, self.serial_port.read, self.serial_port.in_waiting
                        )
                        buffer.extend(data)

                        # sop = 시작, eop = 끝.
                        # 버퍼에서 SOP와 EOP 기준으로 패킷 추출
                        while True:
                            # SOP 위치 찾기
                            sop_index = buffer.find(RASPI_PROTOCOL_TO_DAQ_SOP)
                            if sop_index == -1:
                                # SOP가 없으면 패킷 처리 중단
                                logging.info("SOP를 찾을 수 없습니다.")
                                break

                            # EOP 위치 찾기
                            eop_index = buffer.find(RASPI_PROTOCOL_TO_DAQ_EOP, sop_index)
                            if eop_index == -1:
                                # EOP가 없으면 패킷 처리 중단
                                logging.info("EOP를 찾을 수 없습니다.")
                                break

                            # 패킷 추출 (SOP ~ EOP 포함)
                            packet = buffer[sop_index:eop_index + 1]
                            del buffer[:eop_index + 1]  # 처리한 부분 제거

                            # 패킷 길이 확인
                            if len(packet) == 86:  # 비정형 데이터
                                logging.info(f"수신된 비정형 패킷: {packet.hex()}")
                                await websocket.send(packet)  # 서버로 전송
                                logging.info(f"비정형 데이터 전송됨: {packet.hex()}")
                            elif len(packet) == 10:  # 정형 데이터
                                logging.info(f"수신된 정형 패킷: {packet.hex()}")
                                await websocket.send(packet)  # 서버로 전송
                                logging.info(f"정형 데이터 전송됨: {packet.hex()}")
                            else:
                                logging.warning(f"잘못된 패킷 길이: {len(packet)}, 내용: {packet.hex()}")
                    else:
                        # 충분한 데이터가 없을 경우 잠시 대기
                        await asyncio.sleep(0.01)
        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"WebSocket 연결이 종료되었습니다: {e}")
        except Exception as e:
            logging.error(f"데이터 수집 및 전송 중 오류 발생: {e}")

        logging.info("데이터 수집 및 전송 종료.")
