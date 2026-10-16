# """
# telemetry_frame.py - parser of the STM32 -> PC telemetry frame (TELEMETRY_VERSION = 3)

# Must match TelemetryPacket_t in pc_telemetry.h (little endian, packed, 169 bytes).
# """
# import struct

# START_BYTE = 0xCC
# VERSION = 4

# # (name, struct format) in the exact order of the C struct
# _FIELDS = [
#     # header
#     ("start", "B"), ("version", "B"), ("sequence", "I"), ("timestamp_ms", "I"),
#     # diagnostics
#     ("robot_state", "B"), ("motor_status", "B"), ("motor_error", "B"),
#     ("loop_overrun_count", "H"), ("uart_error_count", "H"), ("feedback_rx_count", "H"),
#     ("feedback_crc_error_count", "H"), ("feedback_lost_count", "H"), ("cmd_drop_count", "H"),
#     ("imu_error_count", "H"), ("telemetry_drop_count", "H"),
#     # STM <-> ESP link (esp_time_us is the ESP clock - not synchronised, use deltas)
#     ("cmd_seq", "H"), ("ack_seq", "H"), ("esp_tx_seq", "H"),
#     ("fb_age_us", "H"), ("rtt_us", "H"),
#     # IMU_Sample_t [g], [deg/s]
#     ("acc_x", "f"), ("acc_y", "f"), ("acc_z", "f"),
#     ("gyro_x", "f"), ("gyro_y", "f"), ("gyro_z", "f"),
#     # ControlState_t (observed)
#     ("pitch", "f"), ("pitch_rate", "f"), ("yaw", "f"), ("yaw_rate", "f"),
#     ("position", "f"), ("velocity", "f"), ("left_wheel_pos", "f"), ("right_wheel_pos", "f"),
#     # wheels
#     ("mot1_vel", "f"), ("mot2_vel", "f"), ("mot1_A", "f"), ("mot2_A", "f"),
#     # TargetState_t
#     ("target_pitch", "f"), ("target_yaw", "f"), ("target_position", "f"), ("target_velocity", "f"),
#     # ControlDebug_t
#     ("position_output", "f"), ("velocity_output", "f"), ("pitch_setpoint", "f"), ("pitch_output", "f"),
#     ("i_position", "f"), ("i_velocity", "f"), ("i_pitch", "f"),
#     # command sent to the motors
#     ("out_l", "f"), ("out_r", "f"),
#     ("checksum", "B"),
# ]
# NAMES = [n for n, _ in _FIELDS]
# _STRUCT = struct.Struct("<" + "".join(f for _, f in _FIELDS))
# FRAME_SIZE = _STRUCT.size
# assert FRAME_SIZE == 164, FRAME_SIZE


# def checksum(frame: bytes) -> int:
#     """XOR of all bytes except the last one (same as calculate_checksum() in the firmware)."""
#     c = 0
#     for b in frame[:-1]:
#         c ^= b
#     return c


# def parse_frame(frame: bytes) -> dict:
#     d = dict(zip(NAMES, _STRUCT.unpack(frame)))
#     if d["checksum"] != checksum(frame):
#         raise ValueError("bad checksum")
#     if d["version"] != VERSION:
#         raise ValueError(f"unsupported telemetry version {d['version']}")
#     return d


# class FrameStream:
#     """Feed it raw bytes from the serial port; returns complete, valid frames.
#     Resynchronises on 0xCC + checksum, so stray ASCII (printf) in the stream is harmless."""

#     def __init__(self):
#         self._buf = bytearray()
#         self.bad_frames = 0

#     def feed(self, data: bytes):
#         self._buf += data
#         out = []
#         while True:
#             i = self._buf.find(bytes([START_BYTE]))
#             if i < 0:
#                 self._buf.clear()
#                 break
#             del self._buf[:i]
#             if len(self._buf) < FRAME_SIZE:
#                 break
#             frame = bytes(self._buf[:FRAME_SIZE])
#             try:
#                 out.append(parse_frame(frame))
#                 del self._buf[:FRAME_SIZE]
#             except ValueError:
#                 self.bad_frames += 1
#                 del self._buf[:1]          # false start byte - slide by one
#         return out


# if __name__ == "__main__":
#     # usage: python telemetry_frame.py "/dev/ttyACM0"   (pip install pyserial)
#     import sys
#     import serial
#     port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
#     stream = FrameStream()
#     last_seq = None
#     with serial.Serial(port, 115200, timeout=0.1) as ser:
#         while True:
#             for f in stream.feed(ser.read(4096)):
#                 if last_seq is not None and f["sequence"] != last_seq + 1:
#                     print(f"!! gap: {last_seq} -> {f['sequence']}")
#                 last_seq = f["sequence"]
#                 print(f"{f['sequence']:8d} pitch={f['pitch']:7.2f} out=({f['out_l']:6.3f},{f['out_r']:6.3f}) "
#                       f"state={f['robot_state']} err={f['motor_error']}")



#!/usr/bin/env python3
"""
telemetry_frame.py - parser + terminal monitor for the STM32 -> PC telemetry frame.

Must match TelemetryPacket_t in pc_telemetry.h (little endian, packed).
Set HAS_VERSION = True if the struct has the `version` byte (164 B variant).

Usage:
  python telemetry_frame.py /dev/ttyACM0                 # events + 1 s summary (default)
  python telemetry_frame.py /dev/ttyACM0 --live 10       # + full line 10x per second
  python telemetry_frame.py /dev/ttyACM0 --dump          # + all fields at every summary
  python telemetry_frame.py /dev/ttyACM0 --csv run.csv   # log every frame (all fields)
  python telemetry_frame.py --file log.bin               # replay a recording (cat /dev/ttyACM0 > log.bin)
"""
import argparse
import csv
import struct
import time

START_BYTE = 0xCC
HAS_VERSION = True     # True -> frame has a `version` byte after startByte (164 B)
VERSION = 4

# ------------------------------------------------------------------------------------------
# Frame layout: (section, [(name, struct format), ...]) in the exact order of the C struct
# ------------------------------------------------------------------------------------------
_SECTIONS = [
    ("header", [("start", "B")]
               + ([("version", "B")] if HAS_VERSION else [])
               + [("sequence", "I"), ("timestamp_ms", "I")]),
    ("diag", [("robot_state", "B"), ("motor_status", "B"), ("motor_error", "B"),
              ("loop_overrun_count", "H"), ("uart_error_count", "H"), ("feedback_rx_count", "H"),
              ("feedback_crc_error_count", "H"), ("feedback_lost_count", "H"), ("cmd_drop_count", "H"),
              ("imu_error_count", "H"), ("telemetry_drop_count", "H")]),
    ("link", [("cmd_seq", "H"), ("ack_seq", "H"), ("esp_tx_seq", "H"),
              ("fb_age_us", "H"), ("rtt_us", "H")]),
    ("imu", [("acc_x", "f"), ("acc_y", "f"), ("acc_z", "f"),
             ("gyro_x", "f"), ("gyro_y", "f"), ("gyro_z", "f")]),
    ("observed", [("pitch", "f"), ("pitch_rate", "f"), ("yaw", "f"), ("yaw_rate", "f"),
                  ("position", "f"), ("velocity", "f"), ("left_wheel_pos", "f"), ("right_wheel_pos", "f")]),
    ("wheels", [("mot1_vel", "f"), ("mot2_vel", "f"), ("mot1_A", "f"), ("mot2_A", "f")]),
    ("target", [("target_pitch", "f"), ("target_yaw", "f"), ("target_position", "f"),
                ("target_velocity", "f")]),
    ("controller", [("position_output", "f"), ("velocity_output", "f"), ("pitch_setpoint", "f"),
                    ("pitch_output", "f"), ("i_position", "f"), ("i_velocity", "f"), ("i_pitch", "f")]),
    ("output", [("out_l", "f"), ("out_r", "f")]),
    ("tail", [("checksum", "B")]),
]
_FIELDS = [fld for _, flds in _SECTIONS for fld in flds]
NAMES = [n for n, _ in _FIELDS]
_STRUCT = struct.Struct("<" + "".join(f for _, f in _FIELDS))
FRAME_SIZE = _STRUCT.size
EXPECTED_SIZE = 164 if HAS_VERSION else 163
assert FRAME_SIZE == EXPECTED_SIZE, f"parser layout is {FRAME_SIZE} B, C struct is {EXPECTED_SIZE} B"

# ------------------------------------------------------------------------------------------
# Names (must match the firmware enums)
# ------------------------------------------------------------------------------------------
ROBOT_STATES = {0: "STANDBY", 1: "INIT", 2: "IDLE", 3: "BALANCING", 4: "FALLEN", 5: "ERROR"}
CMD_NAMES = {0xFA: "HELLO_MOTOR", 0xAF: "HELLO_MASTER", 0xDD: "START_INIT", 0x01: "INIT",
             0x10: "START", 0x11: "SET_VAL", 0x20: "STOP", 0x50: "CLR_FLT", 0x51: "RESET",
             0x60: "ERROR", 0x00: "NONE"}
ERR_NAMES = {0: "OK", 1: "INIT_FAILED", 2: "COMMUNICATION_ERROR", 3: "INVALID_COMMAND",
             4: "TARGET_IS_NAN", 5: "TIMEOUT", 6: "MOTOR_STALLED", 7: "MOTORS_DESYNC",
             8: "OPPOSITE_SPIN"}
# what the STM state machine (robot_app.c) is waiting for in each state
WAITING_FOR = {
    "STANDBY": "button press (sends START_INIT to the ESP)",
    "INIT": "HELLO_MOTOR from the ESP",
    "IDLE": "START from the ESP (STM keeps sending INIT)",
    "ERROR": "button press (sends CLR_FLT) and CLR_FLT ack from the ESP",
}
COUNTERS = ["loop_overrun_count", "uart_error_count", "feedback_crc_error_count",
            "feedback_lost_count", "cmd_drop_count", "imu_error_count", "telemetry_drop_count"]


def state_name(v):
    return ROBOT_STATES.get(v, f"?{v}")


def cmd_name(v):
    return f"{CMD_NAMES.get(v, '?')}(0x{v:02X})"


def err_name(v):
    return f"{ERR_NAMES.get(v, '?')}({v})"


# ------------------------------------------------------------------------------------------
# Frame parsing
# ------------------------------------------------------------------------------------------
def checksum(frame: bytes) -> int:
    """XOR of all bytes except the last one (same as calculate_checksum() in the firmware)."""
    c = 0
    for b in frame[:-1]:
        c ^= b
    return c


def parse_frame(frame: bytes) -> dict:
    d = dict(zip(NAMES, _STRUCT.unpack(frame)))
    if d["start"] != START_BYTE:
        raise ValueError("bad start byte")
    if d["checksum"] != checksum(frame):
        raise ValueError("bad checksum")
    if HAS_VERSION and d["version"] != VERSION:
        raise ValueError(f"unsupported telemetry version {d['version']}")
    return d


class FrameStream:
    """Feed it raw bytes; returns complete, valid frames.
    Resynchronises on 0xCC + checksum. Bytes that are not part of a frame are kept as
    text (STM printf) - read them with pop_text()."""

    def __init__(self):
        self._buf = bytearray()
        self._garbage = bytearray()
        self.bad_frames = 0

    def feed(self, data: bytes):
        self._buf += data
        out = []
        while True:
            i = self._buf.find(bytes([START_BYTE]))
            if i < 0:
                self._garbage += self._buf
                self._buf.clear()
                break
            if i > 0:
                self._garbage += self._buf[:i]
                del self._buf[:i]
            if len(self._buf) < FRAME_SIZE:
                break
            frame = bytes(self._buf[:FRAME_SIZE])
            try:
                out.append(parse_frame(frame))
                del self._buf[:FRAME_SIZE]
            except ValueError:
                self.bad_frames += 1
                self._garbage.append(self._buf[0])
                del self._buf[:1]          # false start byte - slide by one
        return out

    def pop_text(self):
        """Complete printable lines found between frames (e.g. printf from the STM)."""
        if len(self._garbage) > 4096:
            del self._garbage[:-256]
        text = self._garbage.decode("latin-1")
        if "\n" not in text:
            return []
        head, _, tail = text.rpartition("\n")
        self._garbage = bytearray(tail.encode("latin-1"))
        lines = []
        for line in head.split("\n"):
            line = line.strip("\r\t ")
            if len(line) >= 4 and all(32 <= ord(c) < 127 for c in line):
                lines.append(line)
        return lines


# ------------------------------------------------------------------------------------------
# Monitor: turns frames into readable events
# ------------------------------------------------------------------------------------------
class Monitor:
    def __init__(self, summary_s=1.0, stuck_s=3.0, live_hz=0.0, dump=False):
        self.summary_s = summary_s
        self.stuck_s = stuck_s
        self.live_period = (1.0 / live_hz) if live_hz > 0 else None
        self.dump = dump
        self.prev = None
        self.t0 = None
        self.state_since = None
        self.last_stuck = None
        self.last_summary = None
        self.last_live = None
        self.sum_base = None            # frame at the start of the summary interval
        self.stuck_base = None          # frame at the previous stuck report
        self.frames = 0

    @staticmethod
    def _counter_delta(new, old):
        return (new - old) & 0xFFFF

    def _hint(self, f, base):
        s = state_name(f["robot_state"])
        rx = self._counter_delta(f["feedback_rx_count"], base["feedback_rx_count"]) if base else None
        crc = self._counter_delta(f["feedback_crc_error_count"], base["feedback_crc_error_count"]) if base else 0
        if rx == 0:
            return ("no valid feedback from the ESP in this interval: check wiring/baud (COMM_BAUD vs USART2), "
                    "ESP powered/not rebooting, FeedbackPacket_t = same size on both sides")
        if 0 < crc < 0x8000:
            return ("feedback checksum errors are increasing: FeedbackPacket_t layout/size differs between "
                    "ESP and STM, or the UART is noisy")
        if f["motor_error"] != 0 and s in ("INIT", "IDLE"):
            return (f"the ESP reports {err_name(f['motor_error'])} but the STM does not react to errors in {s} "
                    f"-> it waits forever (add an error check for INIT/IDLE in RobotUpdate)")
        if s == "IDLE" and f["motor_status"] == 0xFA:
            return "the ESP still says HELLO_MOTOR: it is not seeing CMD_INIT (MotorPacket_t layout? ESP state?)"
        if s == "IDLE" and f["motor_status"] in (0x10, 0x11):
            return "the ESP already runs (START/SET_VAL) - the STM should leave IDLE; check the condition in robot_app.c"
        return ""

    def _summary(self, f, tag, t):
        b = self.sum_base
        dt = max(t - b["_t"], 1e-6)
        n_frames = self.frames - b["_frames"]
        fb = self._counter_delta(f["feedback_rx_count"], b["feedback_rx_count"])
        lines = [
            f"{tag} {n_frames / dt:5.1f} fr/s | {state_name(f['robot_state'])} {t - self.state_since:.1f}s "
            f"| ESP {cmd_name(f['motor_status'])} err={err_name(f['motor_error'])} "
            f"| fb/s={fb / dt:5.1f} age={f['fb_age_us']}us rtt={f['rtt_us']}us "
            f"| cmd_seq={f['cmd_seq']} ack={f['ack_seq']} esp_tx={f['esp_tx_seq']}",
            f"       totals: crc={f['feedback_crc_error_count']} lost={f['feedback_lost_count']} "
            f"cmd_drop={f['cmd_drop_count']} uart_err={f['uart_error_count']} imu_err={f['imu_error_count']} "
            f"overrun={f['loop_overrun_count']} tlm_drop={f['telemetry_drop_count']}",
        ]
        if self.dump:
            for title, flds in _SECTIONS:
                if title in ("header", "tail"):
                    continue
                vals = []
                for n, _ in flds:
                    v = f[n]
                    vals.append(f"{n}={v:.3f}" if isinstance(v, float) else f"{n}={v}")
                lines.append(f"       {title:10s} " + " ".join(vals))
        self.sum_base = dict(f, _t=t, _frames=self.frames)
        return lines

    @staticmethod
    def _live(f, tag):
        return (f"{tag} {state_name(f['robot_state']):9s} {cmd_name(f['motor_status'])} "
                f"| pitch={f['pitch']:7.2f} rate={f['pitch_rate']:7.1f} pos={f['position']:6.3f} vel={f['velocity']:6.3f} "
                f"| tgt p={f['target_pitch']:5.2f} pos_out={f['position_output']:6.3f} vel_out={f['velocity_output']:6.3f} "
                f"pitch_sp={f['pitch_setpoint']:6.2f} pitch_out={f['pitch_output']:6.3f} "
                f"I={f['i_position']:.2f}/{f['i_velocity']:.2f}/{f['i_pitch']:.2f} "
                f"| out L={f['out_l']:6.3f} R={f['out_r']:6.3f} "
                f"| wheel v={f['mot1_vel']:6.2f}/{f['mot2_vel']:6.2f} A={f['mot1_A']:5.2f}/{f['mot2_A']:5.2f} "
                f"| age={f['fb_age_us']}us rtt={f['rtt_us']}us")

    def process(self, f):
        out = []
        t = f["timestamp_ms"] / 1000.0          # STM clock - works the same live and for replays
        if self.t0 is None:
            self.t0 = t
        self.frames += 1
        p = self.prev
        tag = f"[{t - self.t0:8.3f}s #{f['sequence']}]"

        if p is None:
            out.append(f"{tag} first frame: STM={state_name(f['robot_state'])} ESP={cmd_name(f['motor_status'])} "
                       f"err={err_name(f['motor_error'])}")
            self.state_since = self.last_stuck = self.last_summary = t
            self.sum_base = dict(f, _t=t, _frames=self.frames)
            self.stuck_base = dict(f)
        else:
            gap = (f["sequence"] - p["sequence"]) & 0xFFFFFFFF
            if gap == 0 or gap > 100000:
                out.append(f"{tag} !! sequence jump {p['sequence']} -> {f['sequence']} (STM reset?)")
                self.state_since = self.last_stuck = t
            elif gap > 1:
                out.append(f"{tag} !! {gap - 1} telemetry frame(s) missing (USB busy / host too slow)")

            if f["robot_state"] != p["robot_state"]:
                out.append(f"{tag} STATE {state_name(p['robot_state'])} -> {state_name(f['robot_state'])}")
                self.state_since = self.last_stuck = t
                self.stuck_base = dict(f)
            if f["motor_status"] != p["motor_status"]:
                out.append(f"{tag} ESP status {cmd_name(p['motor_status'])} -> {cmd_name(f['motor_status'])}")
            if f["motor_error"] != p["motor_error"]:
                mark = "!!" if f["motor_error"] else "ok"
                out.append(f"{tag} {mark} ESP error {err_name(p['motor_error'])} -> {err_name(f['motor_error'])}")
            for c in COUNTERS:
                d = self._counter_delta(f[c], p[c])
                if 0 < d < 0x8000:
                    out.append(f"{tag} !! {c} +{d} (now {f[c]})")

        sname = state_name(f["robot_state"])
        if sname in WAITING_FOR and t - self.state_since >= self.stuck_s and t - self.last_stuck >= self.stuck_s:
            self.last_stuck = t
            out.append(f"{tag} .. STUCK in {sname} for {t - self.state_since:.1f}s - waiting for: {WAITING_FOR[sname]}")
            out.append(f"       ESP says: status={cmd_name(f['motor_status'])} error={err_name(f['motor_error'])} | "
                       f"cmd_seq={f['cmd_seq']} ack_seq={f['ack_seq']} esp_tx_seq={f['esp_tx_seq']} "
                       f"fb_rx={f['feedback_rx_count']} crc_err={f['feedback_crc_error_count']} "
                       f"lost={f['feedback_lost_count']}")
            h = self._hint(f, self.stuck_base)
            if h:
                out.append(f"       hint: {h}")
            self.stuck_base = dict(f)

        if t - self.last_summary >= self.summary_s:
            self.last_summary = t
            out.extend(self._summary(f, tag, t))

        if self.live_period is not None and (self.last_live is None or t - self.last_live >= self.live_period):
            self.last_live = t
            out.append(self._live(f, tag))

        self.prev = f
        return out


# ------------------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="STM32 telemetry monitor")
    ap.add_argument("port", nargs="?", default="/dev/ttyACM0")
    ap.add_argument("--file", help="replay a recorded byte stream instead of opening the port")
    ap.add_argument("--live", type=float, default=0.0, metavar="HZ", help="print a full data line HZ times per second")
    ap.add_argument("--summary", type=float, default=1.0, metavar="S", help="summary interval [s] (default 1)")
    ap.add_argument("--stuck", type=float, default=3.0, metavar="S", help="report a state that lasts longer than S seconds")
    ap.add_argument("--dump", action="store_true", help="print every field with each summary")
    ap.add_argument("--csv", metavar="FILE", help="log every frame (all fields) to a CSV file")
    args = ap.parse_args()

    mon = Monitor(args.summary, args.stuck, args.live, args.dump)
    stream = FrameStream()
    csv_file = csv_writer = None
    if args.csv:
        csv_file = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(NAMES)

    if args.file:
        src = open(args.file, "rb")
        read = lambda: src.read(4096)
    else:
        import serial
        ser = serial.Serial(args.port, 115200, timeout=0.05)   # baud is ignored by USB CDC
        read = lambda: ser.read(4096)
        print(f"listening on {args.port}, frame = {FRAME_SIZE} B (Ctrl+C to stop)")

    bytes_total = frames_total = 0
    t_start = last_rx = time.monotonic()
    warned_silent = warned_layout = False
    try:
        while True:
            data = read()
            now = time.monotonic()
            if args.file and not data:
                break
            if data:
                bytes_total += len(data)
                last_rx = now
                warned_silent = False
            frames = stream.feed(data)
            frames_total += len(frames)
            for line in stream.pop_text():
                print(f"[STM text] {line}")
            for f in frames:
                for line in mon.process(f):
                    print(line)
                if csv_writer:
                    csv_writer.writerow([f[n] for n in NAMES])
            if not args.file:
                if not warned_silent and now - last_rx > 2.0:
                    print(f".. no bytes from {args.port} for 2 s (robot off? wrong port? telemetry starts only "
                          f"after the STM control loop runs)")
                    warned_silent = True
                if not warned_layout and bytes_total > 500 and frames_total == 0 and now - t_start > 2.0:
                    print(f".. {bytes_total} bytes received but 0 valid frames (rejected={stream.bad_frames}): "
                          f"parser expects {FRAME_SIZE} B - compare with sizeof(TelemetryPacket_t) / HAS_VERSION")
                    warned_layout = True
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n{frames_total} frames, {bytes_total} bytes, {stream.bad_frames} rejected candidates")
        if csv_file:
            csv_file.close()


if __name__ == "__main__":
    main()