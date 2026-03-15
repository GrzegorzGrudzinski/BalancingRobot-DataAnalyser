import re

'''
Example output:
MOTOR 1: STATE: RUN | RPM: 786.00 | CURR q: 0.19 | CURR d: -0.08
MOTOR 2: STATE: RUN | RPM: 804.00 | CURR q: 0.14 | CURR d: -0.06
ANGLE: -0.92 | PID: 9.02
'''
_pattern_motor_data = re.compile(
    r"MOTOR\s+(?P<id>\d+):\s+STATE:\s+(?P<state>\w+)\s*\|\s*"
    r"RPM:\s*(?P<rpm>[+-]?\d*\.\d+|\d+)\s*\|\s*"
    r"CURR q:\s*(?P<iq_curr>[+-]?\d*\.\d+|\d+)\s*\|\s*"
    r"CURR d:\s*(?P<id_curr>[+-]?\d*\.\d+|\d+)"
) 
_pattern_angle_data = re.compile(
    r"ANGLE:\s*(?P<angle>[+-]?\d*\.\d+|\d+)\s*\|\s*PID:\s*(?P<pid>[+-]?\d*\.\d+|\d+)"
) 


def parse_input(line):
    motor_match = _pattern_motor_data.search(line)
    if motor_match:
        data = motor_match.groupdict()
        return {
            "type": "MOTOR",
            "id": int(data['id']),
            "state": data['state'],
            "rpm": float(data['rpm']),
            "iq_curr": float(data['iq_curr']),
            "id_curr": float(data['id_curr'])
        }

    angle_match = _pattern_angle_data.search(line)
    if angle_match:
        data = angle_match.groupdict()
        return {
            "type": "ANGLE",
            "angle": float(data['angle']),
            "pid": float(data['pid'])
        }

    return None







'''
Another approach - if parsing from printf is too slow, change to original data packets

import struct
MOTOR_PACKET_FORMAT = "<BBfB"    # 1+1+4+1 = 7 bytes
FEEDBACK_PACKET_FORMAT = "<BBfffB" # 1+1+4+4+4+1 = 15 bytes

def calculate_checksum(data_bytes):
    checksum = 0
    for byte in data_bytes:
        checksum ^= byte
    return checksum

    from dataclasses import dataclass

@dataclass
class FeedbackData:
    status: int
    speed: float
    iq: float
    id_curr: float

    @classmethod
    def from_bytes(cls, data_bytes):
        # Rozpakowanie (pomijając startByte i checksum)
        _, status, speed, iq, id_val, _ = struct.unpack("<BBfffB", data_bytes)
        return cls(status, speed, iq, id_val)

# Użycie:
# feedback = FeedbackData.from_bytes(raw_bytes)
# print(feedback.speed)
'''


