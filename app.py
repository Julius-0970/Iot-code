import tkinter as tk
from tkinter import messagebox, ttk
from DAQ_Serial import DaqSerial, RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE
import asyncio
import threading
import websockets
import logging  # 로깅 모듈 추가
import os

# 로깅 설정 (모듈 최상단에 위치)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # 로그를 파일로 저장
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)
logger = logging.getLogger(__name__)

# 센서 데이터에 따른 서버 URI 매핑
sensor_uri_mapping = {
    "TEMP": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/body_temp",
    "NIBP": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/nibp",
    "SPO2": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/spo2",
    "ECG": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/ecg",
    "EOG": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/eog",
    "EMG": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/emg",
    "GSR": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/gsr",
    "AIRFLOW": "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/airflow"
}

username_validation_uri = "wss://port-0-iot-healthcare-1272llwukgaeg.sel5.cloudtype.app/ws/validate_user"

# 비동기 이벤트 루프 실행 함수
def run_asyncio_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# 새로운 asyncio 이벤트 루프 생성
asyncio_loop = asyncio.new_event_loop()
asyncio_thread = threading.Thread(target=run_asyncio_loop, args=(asyncio_loop,), daemon=True)
asyncio_thread.start()

daq_serial_instance = DaqSerial(event_loop=asyncio_loop)

# 사용자 이름 검증 함수
async def validate_username(user_name):
    try:
        async with websockets.connect(username_validation_uri) as websocket:
            await websocket.send(user_name)
            logger.debug(f"Sent username: {user_name}")
            response = await websocket.recv()
            logger.debug(f"Received response: {response}")
            return response == "valid"
    except Exception as e:
        logger.error(f"검증 실패: {e}")
        return False

# 메시지박스 표시 함수 (스레드 안전하게)
def show_info(title, message):
    root.after(0, lambda: messagebox.showinfo(title, message))

def show_error(title, message):
    root.after(0, lambda: messagebox.showerror(title, message))

# 센서 버튼 생성 함수
def create_sensor_button(sensor_name, button_images, row, column, parent):
    image_path = os.path.join("images", f"{sensor_name.lower()}.png")
    try:
        if os.path.exists(image_path):
            button_images[sensor_name] = tk.PhotoImage(file=image_path).subsample(3,3)
            sensor_button = tk.Button(
                parent,
                text=sensor_name,
                image=button_images[sensor_name],
                compound="top",
                width=200,
                height=230,
                command=lambda name=sensor_name: on_sensor_button_click(name)
            )
            sensor_button.image = button_images[sensor_name]  # 참조 유지
        else:
            raise FileNotFoundError(f"Image file not found: {image_path}")
    except Exception as e:
        logger.error(f"이미지를 로드할 수 없습니다: {sensor_name}. 오류: {e}")
        sensor_button = tk.Button(
            parent,
            text=sensor_name,
            width=25,
            height=10,
            command=lambda name=sensor_name: on_sensor_button_click(name)
        )
    sensor_button.grid(row=row, column=column, pady=10, padx=10)
    return row, column

# 센서 버튼 표시
def show_sensor_buttons():
    sensor_frame.pack(fill="both", expand=True)  # 센서 버튼 프레임 표시
    row, column = 0, 0
    button_images = {}

    if getattr(show_sensor_buttons, "sensors_displayed", False):
        logger.debug("센서 버튼이 이미 표시되었습니다.")
        return

    for sensor_name in sensor_uri_mapping.keys():
        row, column = create_sensor_button(sensor_name, button_images, row, column, scrollable_frame)
        column += 1
        if column >= 4:
            column = 0
            row += 1

    show_sensor_buttons.sensors_displayed = True
    logger.debug("센서 버튼이 표시되었습니다.")

# 확인 버튼 클릭 이벤트
def on_validate_click():
    user_name = entry.get()
    if not user_name:
        messagebox.showwarning("경고", "사용자 이름을 입력해주세요.")
        return

    logger.info(f"사용자 '{user_name}' 검증 시도 중...")
    status_label.config(text="검증 중입니다...", fg="blue")

    async def validate_and_show_buttons():
        is_valid = await validate_username(user_name)
        if is_valid:
            logger.info(f"사용자 검증 성공: {user_name}")
            show_info("확인", "사용자 이름이 확인되었습니다. 센서 버튼을 활성화합니다.")
            status_label.config(text="사용자 검증 성공!", fg="green")
            show_sensor_buttons()
        else:
            logger.warning(f"사용자 검증 실패: {user_name}")
            show_error("오류", "사용자 이름이 유효하지 않습니다.")
            status_label.config(text="사용자 검증 실패!", fg="red")

    # 비동기 작업 실행
    asyncio.run_coroutine_threadsafe(validate_and_show_buttons(), asyncio_loop)

# 센서 데이터 전송 로직
def on_sensor_button_click(sensor_name):
    user_name = entry.get()
    server_uri = sensor_uri_mapping.get(sensor_name)
    if not server_uri:
        show_error("오류", f"{sensor_name}에 대한 서버 URI를 찾을 수 없습니다.")
        logger.error(f"{sensor_name}에 대한 서버 URI를 찾을 수 없습니다.")
        return

    logger.info(f"{sensor_name} 데이터 전송 시도 중...")
    status_label.config(text=f"{sensor_name} 데이터 전송 중...", fg="blue")
    
    async def send_sensor_data():
        try:
            daq_serial_instance.open_serial()
            daq_serial_instance.set_command(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE)
            daq_serial_instance.send_request(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE)
            await daq_serial_instance.read_and_send(user_name, RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_TEMPERATURE, server_uri)
            show_info("성공", f"{sensor_name} 데이터가 성공적으로 전송되었습니다.")
            logger.info(f"{sensor_name} 데이터가 성공적으로 전송되었습니다.")
            status_label.config(text=f"{sensor_name} 데이터 전송 완료!", fg="green")
        except Exception as e:
            show_error("오류", f"{sensor_name} 데이터 전송 오류: {e}")
            logger.error(f"{sensor_name} 데이터 전송 오류: {e}")
            status_label.config(text=f"{sensor_name} 데이터 전송 실패!", fg="red")
        finally:
            # 시리얼 포트 닫기
            daq_serial_instance.close_serial()

    asyncio.run_coroutine_threadsafe(send_sensor_data(), asyncio_loop)

# GUI 설정
root = tk.Tk()
root.title("실시간 데이터 수집")
root.geometry("1024x600")

# 전체 스크롤을 위한 Canvas와 Scrollbar 생성
main_canvas = tk.Canvas(root, borderwidth=0)
main_scrollbar = ttk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
main_canvas.configure(yscrollcommand=main_scrollbar.set)

main_scrollbar.pack(side="right", fill="y")
main_canvas.pack(side="left", fill="both", expand=True)

# 전체 Frame 생성
main_frame = tk.Frame(main_canvas)
main_canvas.create_window((0, 0), window=main_frame, anchor='nw')

# 전체 Frame의 크기가 변경될 때 스크롤 영역을 업데이트
def on_main_frame_configure(event):
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))

main_frame.bind("<Configure>", on_main_frame_configure)

# 마우스 휠 스크롤 바인딩 (운영체제별로 다르게 처리)
def _on_mousewheel(event):
    if os.name == 'nt':  # Windows
        delta = int(-1*(event.delta/120))
        main_canvas.yview_scroll(delta, "units")
    elif os.name == 'darwin':  # MacOS
        delta = int(-1*(event.delta))
        main_canvas.yview_scroll(delta, "units")
    else:  # Linux
        if event.num == 4:
            main_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            main_canvas.yview_scroll(1, "units")

# 마우스 휠 이벤트 바인딩
main_canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows 및 MacOS
main_canvas.bind_all("<Button-4>", _on_mousewheel)    # Linux 스크롤 업
main_canvas.bind_all("<Button-5>", _on_mousewheel)    # Linux 스크롤 다운

# 헤더 프레임 생성 (닫기 버튼 포함)
header_frame = tk.Frame(main_frame)
header_frame.pack(fill="x")

# 닫기 버튼 생성 및 배치
close_button = tk.Button(
    header_frame,
    text="✖",  # 유니코드 X 문자
    bg="red",
    fg="white",
    font=("Arial", 14, "bold"),
    command=lambda: on_closing(),
    bd=0,  # 테두리 없애기
    activebackground="darkred",
    cursor="hand2"
)
close_button.pack(side="right", padx=10, pady=10)

# 사용자 이름 입력 섹션
label = tk.Label(main_frame, text="사용자 이름: ")
label.pack(pady=10)

entry = tk.Entry(main_frame, width=30)
entry.pack(pady=5)

# 상태 레이블
status_label = tk.Label(main_frame, text="", fg="blue")
status_label.pack(pady=10)

# 센서 버튼들을 담을 프레임 (초기에는 숨겨진 상태)
sensor_frame = tk.Frame(main_frame)
sensor_frame.pack(pady=20, fill="both", expand=True)
sensor_frame.pack_forget()  # 초기에는 숨김

# 스크롤 가능한 센서 프레임 생성
sensor_canvas = tk.Canvas(sensor_frame)
sensor_scrollbar = ttk.Scrollbar(sensor_frame, orient="vertical", command=sensor_canvas.yview)
sensor_canvas.configure(yscrollcommand=sensor_scrollbar.set)

sensor_scrollbar.pack(side="right", fill="y")
sensor_canvas.pack(side="left", fill="both", expand=True)

scrollable_frame = tk.Frame(sensor_canvas)

# 스크롤 가능한 프레임 구성
scrollable_frame.bind(
    "<Configure>",
    lambda e: sensor_canvas.configure(scrollregion=sensor_canvas.bbox("all"))
)
sensor_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
sensor_canvas.configure(yscrollcommand=sensor_scrollbar.set)

# 마우스 휠 스크롤 지원 (센서 프레임)
def _on_sensor_mousewheel(event):
    if os.name == 'nt':  # Windows
        delta = int(-1*(event.delta/120))
        sensor_canvas.yview_scroll(delta, "units")
    elif os.name == 'darwin':  # MacOS
        delta = int(-1*(event.delta))
        sensor_canvas.yview_scroll(delta, "units")
    else:  # Linux
        if event.num == 4:
            sensor_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            sensor_canvas.yview_scroll(1, "units")

sensor_canvas.bind_all("<MouseWheel>", _on_sensor_mousewheel)  # Windows 및 MacOS
sensor_canvas.bind_all("<Button-4>", _on_sensor_mousewheel)    # Linux 스크롤 업
sensor_canvas.bind_all("<Button-5>", _on_sensor_mousewheel)    # Linux 스크롤 다운

# 확인 버튼 생성
validate_button = tk.Button(main_frame, text="확인", command=on_validate_click)
validate_button.pack(pady=10)

# GUI 종료 시 클린업 작업
def on_closing():
    if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):
        # 비동기 루프를 종료
        asyncio_loop.call_soon_threadsafe(asyncio_loop.stop)
        # 시리얼 포트 닫기
        daq_serial_instance.close_serial()
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# GUI 이벤트 루프 실행
if __name__ == "__main__":
    root.mainloop()
