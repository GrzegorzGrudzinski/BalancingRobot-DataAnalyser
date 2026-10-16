import serial
import time
# import concurrent.futures
import threading

from telemetry_parser import TelemetryParser, TelemetryData
class TelemetryReader:
    def __init__(
            self,
            parser: TelemetryParser,
            port:str, 
            baudrate:int = 115200,
            timeout: float = 0.0,
        ):
        self.parser = parser

        self.ser = serial.Serial(port= port, baudrate = baudrate, timeout=timeout)
        
        self._latest = None

        self._running_flag = False
        self._thread = None
        self._lock = threading.Lock()
    
    def close(self):
        if self.ser.is_open:
            self.ser.close()
    
    def _read(self):
        while self._running_flag:
            try:
                if self.ser.is_open:
                    n = self.ser.in_waiting
                    if n:
                        data = self.ser.read(n)

                        # parse the data, returns: TelemetryData or None
                        result = self.parser.parse(data)
                        if result is not None:
                            with self._lock:
                                self._latest = result

                    else:
                        data = self.ser.read(1)

            except serial.SerialException as e:
                self._running_flag = False
                print(f"Port error: {e}")
                break                
            except Exception as e:
                print(f"Error: {e}")

    def get_latest(self) -> TelemetryData | None:
        with self._lock:
            return self._latest

    def start(self):
        if self._running_flag:
            return
        
        self._running_flag = True
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def stop(self):
        self._running_flag = False
        if self._thread:
            self._thread.join(timeout=0.1)
            self._thread = None

        if self.ser.is_open:
            self.ser.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        