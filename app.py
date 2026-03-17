from tkinter import PhotoImage
import tkinter as tk
from PIL import Image, ImageTk  # 이미지 처리를 위해 PIL 사용
from tkinter import messagebox  # 메시지 박스 사용
from DAQ_Serial import *  # DAQ 시리얼 관련 클래스 임포트
import asyncio  # 비동기 처리를 위해 asyncio 사용
import threading  # 멀티스레드 처리를 위해 threading 사용
# import websockets  # 웹소켓 통신을 위해 websockets 사용
import logging  # 로깅 모듈 추가
import os  # 파일 경로 처리를 위해 os 사용
from getmac import get_mac_address  # MAC 주소를 가져오기 위해 사용

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # 로그를 파일로 저장
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 센서 명령어 매핑
sensor_command_mapping = {
    "AIRFLOW": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_AIR_FLOW,  # 공기 흐름 센서 요청 명령어
    "ECG": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_ECG,  # 심전도 데이터 요청 명령어
    "EOG": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EOG,  # 안구전위 데이터 요청 명령어
    "EMG": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG,  # 근전도 데이터 요청 명령어
    "GSR": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_GSR,  # 피부 전기 반응 데이터 요청 명령어
    "TEMP": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE,  # 온도 데이터 요청 명령어
    "SPO2": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_SPO2,  # 혈중 산소 포화도 데이터 요청 명령어
    "NIBP": RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_NIBP  # 비침습적 혈압 데이터 요청 명령어
}

# MAC 주소를 이용해 장치 ID 가져오기
device_id = get_mac_address()

# 현재 스크립트의 디렉토리 경로 가져오기
script_dir = os.path.dirname(os.path.abspath(__file__))

# GUI 설정
root = tk.Tk()  # Tkinter 창 생성
root.update()  # 창 업데이트
root.title("실시간 데이터 수집")  # 창 제목 설정
root.geometry("1024x600")  # 창 크기 설정

# 비동기 이벤트 루프 실행 함수
def run_asyncio_loop(loop):
    asyncio.set_event_loop(loop)  # 현재 스레드에 이벤트 루프 설정
    loop.run_forever()  # 루프를 무한히 실행

# 새로운 비동기 이벤트 루프 생성 및 스레드에서 실행
asyncio_loop = asyncio.new_event_loop()
asyncio_thread = threading.Thread(target=run_asyncio_loop, args=(asyncio_loop,), daemon=True)
asyncio_thread.start()

# DAQ 시리얼 인스턴스 생성
daq_serial_instance = DaqSerial(event_loop=asyncio_loop)

# 현재 실행 중인 작업 추적 변수
current_task = None  # 현재 실행 중인 비동기 작업
current_sensor = None  # 현재 실행 중인 센서

# 닫기 버튼 눌렀을 때 실행되는 함수
def on_closing():
    if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):  # 종료 확인 메시지 박스
        asyncio_loop.call_soon_threadsafe(asyncio_loop.stop)  # asyncio 루프 중지
        daq_serial_instance.close_serial()  # 시리얼 포트 닫기
        root.destroy()  # Tkinter 창 닫기

# 헤더 프레임 생성 및 설정
header_frame = tk.Frame(root, bg="lightgray", height=50)  # 헤더 영역 설정
header_frame.pack(fill="x")  # 프레임 가로 채우기

# 닫기 버튼 생성 및 배치
close_button = tk.Button(
    header_frame,
    text="✖",  # 닫기 버튼 텍스트
    bg="red",  # 버튼 배경색
    fg="white",  # 버튼 글자색
    font=("Arial", 14, "bold"),  # 버튼 폰트 설정
    command=on_closing,  # 버튼 클릭 시 on_closing 함수 실행
    bd=0,  # 테두리 없앰
    activebackground="darkred",  # 버튼 활성화 시 배경색
    cursor="hand2"  # 마우스 커서 모양 설정
)
close_button.pack(side="right", padx=10, pady=10)  # 버튼을 오른쪽에 배치

# 기본 닫기 이벤트에 on_closing 함수 연결
root.protocol("WM_DELETE_WINDOW", on_closing)

# 사용자 이름 입력 섹션 생성
label = tk.Label(root, text="사용자 Email")  # 사용자 이메일 입력 라벨
label.pack(pady=10)  # 라벨 배치

entry = tk.Entry(root, width=30)  # 사용자 이메일 입력창
entry.pack(pady=5)  # 입력창 배치

status_label = tk.Label(root, text="", fg="blue")  # 상태 표시 라벨
status_label.pack(pady=10)  # 상태 라벨 배치

sensor_frame = tk.Frame(root)  # 센서 버튼을 담을 프레임 생성
sensor_frame.pack(pady=10, fill="both", expand=True)  # 프레임 배치

# 메시지박스 표시 함수
def show_info(title, message):
    root.after(0, lambda: messagebox.showinfo(title, message))  # 정보 메시지 표시

def show_error(title, message):
    root.after(0, lambda: messagebox.showerror(title, message))  # 오류 메시지 표시

# 센서 버튼 표시 함수
def show_sensor_buttons():
    row, column = 0, 0  # 버튼의 행과 열 초기값
    button_images = {}  # 버튼 이미지 저장용 딕셔너리
    max_columns = 4  # 최대 열 개수

    for sensor_name in sensor_uri_mapping.keys():  # 센서 이름에 대해 반복
        try:
            image_path = os.path.join(script_dir, f"{sensor_name.lower()}.png")  # 이미지 경로 설정
            orig_image = Image.open(image_path)  # 이미지 파일 열기
            resized_image = orig_image.resize((100, 100), Image.ANTIALIAS)  # 이미지 크기 조정
            button_images[sensor_name] = ImageTk.PhotoImage(resized_image)  # 버튼에 사용할 이미지 설정

            sensor_button = tk.Button(
                sensor_frame,
                text=sensor_name,  # 버튼 텍스트 설정
                image=button_images[sensor_name],  # 버튼 이미지 설정
                compound="top",  # 텍스트와 이미지를 함께 표시 (이미지가 위)
                width=180,
                height=120,
                command=lambda name=sensor_name: on_sensor_button_click(name)  # 버튼 클릭 시 센서 데이터 전송 함수 호출
            )
            sensor_button.image = button_images[sensor_name]  # 이미지 참조 유지
        except Exception as e:
            logger.error(f"이미지 로드 실패: {sensor_name}. 오류: {e}")  # 이미지 로드 실패 시 에러 로그
            sensor_button = tk.Button(
                sensor_frame,
                text=sensor_name,  # 버튼 텍스트 설정
                width=25,
                height=10,
                command=lambda name=sensor_name: on_sensor_button_click(name)  # 버튼 클릭 시 센서 데이터 전송 함수 호출
            )
        sensor_button.grid(row=row, column=column, pady=10, padx=10)  # 버튼 그리드에 배치
        column += 1
        if column >= max_columns:  # 최대 열 개수를 초과하면
            column = 0
            row += 1  # 다음 행으로 이동
            
    total_columns = max_columns
    for col in range(total_columns):
        sensor_frame.grid_columnconfigure(col, weight=1)  # 프레임의 열 크기 균등하게 설정

# URI 동적 생성 함수
def generate_sensor_uri(username, sensor_type):
    """
    사용자 이름과 센서 타입을 기반으로 URI 생성.
    """
    base_url = "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws"  # 기본 URL 설정
    return f"{base_url}/{username}/{sensor_type.lower()}"  # 사용자 이름과 센서 타입을 사용해 URI 생성

# 센서 데이터 전송 함수
def on_sensor_button_click(sensor_name):
    global current_task, current_sensor

    user_name = entry.get().strip()  # 사용자 입력값에서 공백 제거
    serial_command = sensor_command_mapping.get(sensor_name)  # 센서에 해당하는 명령어 가져오기

    if not user_name:
        messagebox.showwarning("경고", "사용자 이름을 입력해주세요.")  # 사용자 이름이 입력되지 않았을 경우 경고 메시지 표시
        return

    # URI 동적 생성 및 검증
    server_uri = generate_sensor_uri(user_name, sensor_name)  # 사용자 이름과 센서 타입으로 URI 생성
    if not server_uri:
        show_error("오류", f"{sensor_name}에 대한 서버 URI를 찾을 수 없습니다.")  # URI 생성 실패 시 오류 메시지 표시
        logger.error(f"{sensor_name}의 URI를 찾을 수 없습니다.")  # 로그 기록
        return

    # 실행 중인 작업이 있는 경우 처리
    if current_task and not current_task.done():
        if current_sensor == sensor_name:
            user_response = messagebox.askyesno(
                "작업 중지 확인",
                f"{sensor_name} 데이터가 이미 전송 중입니다. 작업을 중지하시겠습니까?"
            )
            if user_response:
                current_task.cancel()  # 현재 작업 취소
                try:
                    current_task.result()  # 작업 결과 가져오기
                    logger.info(f"기존 작업({current_sensor}) 중단 완료.")  # 작업 중단 완료 로그
                except asyncio.CancelledError:
                    logger.info(f"기존 작업({current_sensor})이 성공적으로 취소되었습니다.")  # 작업 취소 성공 로그
                except Exception as e:
                    logger.error(f"기존 작업 중단 중 오류 발생: {e}")  # 작업 중단 중 오류 발생 시 로그 기록
                finally:
                    daq_serial_instance.close_serial()  # 시리얼 포트 닫기
                    logger.info("closed serial")  # 시리얼 포트 닫힘 로그
                    current_task = None
                    current_sensor = None
                return
            else:
                return
        else:
            user_response = messagebox.askyesno(
                "작업 전환 확인",
                f"현재 {current_sensor} 데이터를 전송 중입니다. 이를 중단하고 {sensor_name} 데이터를 전송하시겠습니까?"
            )
            if user_response:
                current_task.cancel()  # 현재 작업 취소
                try:
                    current_task.result()  # 작업 결과 가져오기
                    logger.info(f"기존 작업({current_sensor}) 중단 완료.")  # 작업 중단 완료 로그
                except asyncio.CancelledError:
                    logger.info(f"기존 작업({current_sensor})이 성공적으로 취소되었습니다.")  # 작업 취소 성공 로그
                except Exception as e:
                    logger.error(f"기존 작업 중단 중 오류 발생: {e}")  # 작업 중단 중 오류 발생 시 로그 기록
                finally:
                    daq_serial_instance.close_serial()  # 시리얼 포트 닫기
                    logger.info("closed serial")  # 시리얼 포트 닫힘 로그
                    current_task = None
                    current_sensor = None
            else:
                return

    # 중단되지 않은 작업이 있을 경우, 새로운 작업 예약 방지
    if current_task and not current_task.done():
        logger.warning("현재 작업이 완료되지 않았습니다. 새 작업을 시작할 수 없습니다.")  # 로그 경고 메시지
        return

    # 센서 데이터 전송 비동기 함수 정의
    async def send_sensor_data():
        try:
            status_label.config(text=f"{sensor_name} 데이터를 전송 중입니다...", fg="blue")  # 상태 표시 업데이트
            root.update_idletasks()

            daq_serial_instance.open_serial()  # 시리얼 포트 열기
            daq_serial_instance.set_command(serial_command)  # 명령어 설정
            daq_serial_instance.send_request(serial_command)  # 명령어 전송

            await asyncio.wait_for(
                daq_serial_instance.read_and_send(device_id, user_name, serial_command, server_uri),
                timeout=100  # 데이터 전송 시간 제한 설정
            )
            status_label.config(text=f"{sensor_name} 데이터 전송 완료!", fg="green")  # 상태 표시 업데이트
            logger.info(f"{sensor_name} 데이터 전송 완료.")  # 로그 기록
        except asyncio.TimeoutError:
            status_label.config(text=f"{sensor_name} 데이터 전송 시간 초과!", fg="red")  # 시간 초과 시 상태 표시
            show_error("시간 초과", f"{sensor_name} 데이터 전송이 시간 초과되었습니다.")  # 시간 초과 오류 메시지 표시
        except asyncio.CancelledError:
            logger.info(f"{sensor_name} 데이터 전송 작업이 중단되었습니다.")  # 작업 중단 로그 기록
            status_label.config(text=f"{sensor_name} 데이터 전송 중단됨.", fg="orange")  # 작업 중단 상태 표시
        except Exception as e:
            logger.error(f"{sensor_name} 데이터 전송 중 오류: {e}")  # 데이터 전송 중 오류 발생 시 로그 기록
            status_label.config(text=f"{sensor_name} 데이터 전송 오류 발생!", fg="red")  # 오류 상태 표시
        finally:
            global current_task, current_sensor
            current_task = None
            current_sensor = None

    # 새로운 작업 예약 (현재 작업이 없는 경우에만)
    current_task = asyncio.run_coroutine_threadsafe(send_sensor_data(), asyncio_loop)  # 비동기 작업 예약
    current_sensor = sensor_name  # 현재 센서 설정
    logger.info(f"{sensor_name} 데이터 전송 작업 시작.")  # 작업 시작 로그 기록

# 센서 버튼 생성 및 표시
show_sensor_buttons()

# 메인 루프 실행
if __name__ == "__main__":
    root.mainloop()  # Tkinter 메인 이벤트 루프 실행
