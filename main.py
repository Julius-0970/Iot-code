from DAQ_Serial import DaqSerial, RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG
import time

daq_serial = DaqSerial();
daq_serial.open_serial()
daq_serial.set_command(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG)
daq_serial.send_request(RASPI_PROTOCOL_TO_DAQ_CMD_ID_REQ_EMG)

try:
    while True:
        daq_serial.on_ready_read()
        time.sleep(1)
finally:
    daq_serial.close_serial()