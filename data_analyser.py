import numpy as np
import matplotlib.pyplot as plt
import serial
import time

from protocol import parse_input

port = "COM4"
baudrate = 115200

try:
    ser = serial.Serial(port,baudrate, timeout=1)
    time.sleep(2)

    print(f"Connected with {port}. Waiting for data...")

    while True:
        if ser.in_waiting > 0: # if there is data in buff
            line = ser.readline().decode('utf-8').rstrip()
            # print(f"Otrzymano: {line}")
            parsed = parse_input(line)
            if parsed:
                print(f"{parsed}")
except serial.SerialException as e:
    print(f"Błąd portu: {e}")
except KeyboardInterrupt:
    print("\nZatrzymano przez użytkownika.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Port zamknięty.")

   
