import time
from collections import deque

import matplotlib.pyplot as plt

from data_analyser import TelemetryParser, TelemetryReader


# ==================================================
# KONFIGURACJA
# ==================================================

PORT = "/dev/ttyACM0"
BAUDRATE = 921600

MAX_SAMPLES = 1000
PLOT_UPDATE_PERIOD = 0.02      # 50 Hz

# Wybierz tutaj, co ma być pokazywane
PLOTS = [
    "angle_pitch",
    # "angle_yaw",

    # "mot1_vel",
    # "mot1_pos",
    # "mot1_A",

    # "mot2_vel",
    # "mot2_pos",
    # "mot2_A",

    # "robot_status",
    # "motor_status",
]


# Nazwy wyświetlane na wykresie
PLOT_LABELS = {
    "angle_pitch": "Pitch",
    "angle_yaw": "Yaw",

    "mot1_vel": "Motor 1 velocity",
    "mot1_pos": "Motor 1 position",
    "mot1_A": "Motor 1 current",

    "mot2_vel": "Motor 2 velocity",
    "mot2_pos": "Motor 2 position",
    "mot2_A": "Motor 2 current",

    "robot_status": "Robot status",
    "motor_status": "Motor status",
}


# ==================================================
# UART
# ==================================================

parser = TelemetryParser()

reader = TelemetryReader(
    port=PORT,
    baudrate=BAUDRATE,
    parser=parser,
)

reader.start()


# ==================================================
# BUFOR DANYCH
# ==================================================

time_data = deque(maxlen=MAX_SAMPLES)

data = {
    name: deque(maxlen=MAX_SAMPLES)
    for name in PLOTS
}


# ==================================================
# WYKRES
# ==================================================

fig, ax = plt.subplots()

lines = {}

for name in PLOTS:

    line, = ax.plot(
        [],
        [],
        label=PLOT_LABELS.get(name, name),
    )

    lines[name] = line


ax.set_xlabel("Time [s]")
ax.set_ylabel("Value")
ax.grid()
ax.legend()


start_time = time.perf_counter()


# ==================================================
# UPDATE
# ==================================================

def update():

    telemetry = reader.get_latest()

    if telemetry is None:
        return

    t = time.perf_counter() - start_time

    time_data.append(t)

    for name in PLOTS:

        value = getattr(telemetry, name)

        data[name].append(value)

        lines[name].set_data(
            time_data,
            data[name]
        )

    ax.relim()
    ax.autoscale_view()

    fig.canvas.draw_idle()


# ==================================================
# MAIN LOOP
# ==================================================

try:

    while plt.fignum_exists(fig.number):

        update()

        plt.pause(PLOT_UPDATE_PERIOD)

finally:

    reader.stop()