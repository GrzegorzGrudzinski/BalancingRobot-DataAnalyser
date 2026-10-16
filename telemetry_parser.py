
from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class TelemetryData:
    robot_status: int
    motor_status: int

    angle_pitch: float
    angle_yaw: float

    mot1_vel: float
    mot1_pos: float
    mot1_A: float

    mot2_vel: float
    mot2_pos: float
    mot2_A: float

import struct
class TelemetryParser:
    START_BYTE = b'\xCC'
    FEEDBACK_STRUCT = struct.Struct("<BBB8fB") # 1 + 2*1 + 8*4 + 1 = 36 bytes
    FRAME_SIZE = FEEDBACK_STRUCT.size # 36

    def __init__(self):
        self._buffer = bytearray()

        self.invalid_packets = 0
        self.valid_packets = 0

    def parse(self, data_bytes: bytes) -> TelemetryData | None:
        self._buffer.extend(data_bytes)
        latest = None

        while True:
            # Find start of the frame
            start = self._buffer.find(self.START_BYTE)
            if start == -1: # No start byte found
                self._buffer.clear()
                break
            if start > 0:
                # delete everything before the start byte
                del self._buffer[:start]

            # Check length of the frame
            if len(self._buffer) < self.FRAME_SIZE:
                break

            # Check data integrity
            packet = self._buffer[:self.FRAME_SIZE]
            received_checksum = packet[-1]
            calculated_checksum = self.calculate_checksum(packet[:-1])

            if received_checksum != calculated_checksum:
                self.invalid_packets += 1
                del self._buffer[0] # look for the next start byte
                continue

            # Unpack the frame
            values = self.FEEDBACK_STRUCT.unpack(packet)

            telemetry = TelemetryData(
                robot_status=values[1],
                motor_status=values[2],
                
                angle_pitch= values[3],
                angle_yaw=values[4],

                mot1_vel=values[5],
                mot1_pos=values[6],
                mot1_A=values[7],

                mot2_vel=values[8],
                mot2_pos=values[9],
                mot2_A=values[10],        
            )
            self.valid_packets += 1

            del self._buffer[:self.FRAME_SIZE]

            # Save the latest frame
            latest = telemetry
        return latest

    @staticmethod
    def calculate_checksum(data_bytes)->int:
        checksum = 0
        for byte in data_bytes:
            checksum ^= byte
        return checksum

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)

    @property
    def stats(self):
        return {
            "valid": self.valid_packets,
            "invalid": self.invalid_packets,
            "buffered": len(self._buffer),
        }
    