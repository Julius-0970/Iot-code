from DAQ_Serial import DaqSerial
import time
import asyncio
import websockets


async def send_data_server(uri, packet):
    async with websockets.connect(uri) as websocket:
        await websocket.send(data)
        print(f"Sent data: {data}")

def setup_daq_serial(protocol_id):
    daq_serial = DaqSerial() # DaqSerial 객체 생성
    try:
        daq_serial.open_serial() # 시리얼 포트 열기
        daq_serial.set_command(protocol_id) # 명령 설정 (데이터 요청)
        daq_serial.send_request(protocol_id) # 데이터 요청 전송
    except Exception as e:
        print(f"Error setting up DAQ serial: {e}")
        return None
    return daq_serial

async def read_data(daq_serial, server_uri):
    try:
        # 무한 루프를 통해 데이터 수신 대기
        while True:
            daq_serial.on_ready_read()  # 데이터가 준비되면 읽기
            if not daq_serial.data_queue.empty():
                packet = daq_serial.data_queue.get()\
                """
                data = parsed_data(packet)
                if data :
                    await send_data_server(server_uri, data)
                    """
                await send_data_server(server_uri, data)
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Error in reading data: {e}")
    finally:
        # 시리얼 통신 닫기
        daq_serial.close_serial()  # 종료 시 시리얼 포트 닫기


"""
#데이터 파싱
def parse_data(packet):
    # Placeholder for real parsing logic
    if packet[1] == RASPI_PROTOCOL_TO_DAQ_CMD_ID_RES_TEMPERATURE:
        data_length = packet[2]
        parsing_data = packet[3:3 + data_length]
        # Implement actual data parsing logic here
        return parsed_data
    return None
"""
