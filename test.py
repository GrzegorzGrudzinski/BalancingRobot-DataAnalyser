import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time

from protocol import parse_input

# --- TEST ---
''' Generate input strings using variables '''
# Example variables you can change programmatically

class MotorData:
    def __init__(self, motor_id):
        self.id = motor_id
        self.state = "RUN"
        self.rpm = 0.0
        self.curr_q = 0.0
        self.curr_d = 0.0

    def __str__(self):
        return (f"MOTOR {self.id}: STATE: {self.state} | "
                f"RPM: {self.rpm:.2f} | CURR q: {self.curr_q:.2f} | CURR d: {self.curr_d:.2f}")


class Message:
    def __init__(self):
        self.motor1 = MotorData(1)
        self.motor2 = MotorData(2)
        
        self.angle = 0
        self.pid = 0

    def get_data(self):
        return [
            str(self.motor1),
            str(self.motor2),
            f"ANGLE: {self.angle:.2f} | PID: {self.pid:.2f}"
        ]
    


# run mock simulation


message = Message()
normal_speed = 750.0
normal_curr_q = 0.09
normal_curr_d = 0.09
normal_angle = 90.0
normal_pid = 180

# Buffors for data
x_data = []
y1_data = []  # RPM Motor 1
y2_data = []  # RPM Motor 2
# pid_data = [] # PID
angle_data = [];

# Window parameters
MAX_SAMPLES = 100

start_time = time.time()
duration = 10  # s

# --- KONFIGURACJA WYKRESU LIVE ---
# plt.ion()  # Enable 
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Axis settings
ax1.set_title('Live data')
ax1.set_ylabel('Speed [RPM]')
ax1.grid(True)

ax2.set_ylabel('Angle')
ax2.set_xlabel('Time [s]')
ax2.grid(True)

line_m1, = ax1.plot([], [], 'b-', label='RPM M1') # Empty line at the start
line_m2, = ax1.plot([], [], 'g-', label='RPM M2') # Empty line at the start
line_angle, = ax2.plot([], [], 'r-', label='Angle') # Empty line at the start

ax1.legend(loc='upper right')
ax2.legend(loc='upper right')


def update(frame):
    current_t = time.time() - start_time

    # Generate new data (update data)
    message.motor1.state = "RUN"    
    message.motor1.rpm = normal_speed + np.random.uniform(-50,50)
    message.motor1.curr_q = normal_curr_q + np.random.uniform(-0.9,1)
    message.motor1.curr_d = normal_curr_d + np.random.uniform(-0.9,1)

    message.motor2.state = "RUN"    
    message.motor2.rpm = normal_speed + np.random.uniform(-50,50)
    message.motor2.curr_q = normal_curr_q + np.random.uniform(-0.9,1)
    message.motor2.curr_d = normal_curr_d + np.random.uniform(-0.9,1)

    message.angle = normal_angle + np.random.uniform(-45,45)
    message.pid = normal_pid + np.random.uniform(-45,45)

    # Update lists
    x_data.append(current_t)
    y1_data.append(message.motor1.rpm)
    y2_data.append(message.motor2.rpm)
    angle_data.append(message.angle)

    if len(x_data) > MAX_SAMPLES:
        x_data.pop(0)
        y1_data.pop(0)
        y2_data.pop(0)
        angle_data.pop(0)

    # Update data on the plots
    line_m1.set_data(x_data, y1_data)
    line_m2.set_data(x_data, y2_data)
    line_angle.set_data(x_data, angle_data)


    # Dynamic axis scaling

    # X axis
    if len(x_data) > 0:
        ax1.set_xlim(x_data[0], x_data[-1] + 1)
    else:
        ax1.set_xlim(0, 10)

    # Y axis
    ax1.set_ylim(min(min(y1_data, default=0), min(y2_data, default=0)) - 50, 
                 max(max(y1_data, default=1000), max(y2_data, default=1000)) + 50)
    ax2.set_ylim(min(angle_data, default=0) - 20, max(angle_data, default=200) + 20)

    return line_m1, line_m2, line_angle


    # line.set_data(range(frame), np.random.rand(frame))
    # ax.relim()
    # ax.autoscale_view()
    # return line,
 
# ani = animation(fig, update, frames=range(1, 101), blit=True)
ani = animation.FuncAnimation(fig, update, interval=50)
plt.show()


print("Koniec czasu!")
