# BalancingRobot-DataAnalyser

PC-side tools for the two-wheeled self-balancing robot: reading the binary telemetry stream sent by the
STM32 main controller over USB, showing it in the terminal and logging it to CSV for later analysis.

Part of the Balancing Robot project (engineering thesis):

| Repository | Role |
| --- | --- |
| [BalancingRobot-Main-Controller](https://github.com/GrzegorzGrudzinski/BalancingRobot-Main-Controller) | STM32 firmware: IMU, control cascade, state machine, telemetry |
| [BalancingRobot-SimpleFOC-Motor-Controller](https://github.com/GrzegorzGrudzinski/BalancingRobot-SimpleFOC-Motor-Controller) | ESP32 + SimpleFOC motor driver |
| [BalancingRobot-simulatior](https://github.com/GrzegorzGrudzinski/BalancingRobot-simulatior) | PyBullet simulator, SiL with the firmware core |
| **BalancingRobot-DataAnalyser** (this repo) | telemetry parser, monitor and logger |

## Files

| File | What it does |
| --- | --- |
| `telemetry_frame.py` | **Main tool.** Parser and terminal monitor of the current telemetry frame (`TelemetryPacket_t`, 168 B, start byte `0xCC`, version byte). Prints state changes, error counters and a periodic summary; can log every frame to CSV or replay a recorded byte stream. |
| `data_analyser.py`, `telemetry_parser.py`, `test_data.py` | Older reader for the first 36 B frame and a live matplotlib plot. Kept for reference, does not match the current firmware frame. |
| `protocol.py`, `test.py` | Oldest text protocol (`MOTOR 1: STATE: ... RPM: ...`) with a generator for testing. Legacy. |
| `Balancing Robot Parser.ssproj` | [Serial Studio](https://serial-studio.github.io/) project file. |
| `comm_diagram.drawio` | Communication diagram (PC ↔ STM32 ↔ ESP32). |
| `log/` | Local recordings and notes (ignored by git, can be large). |

## Requirements

- Python 3.10+
- `pyserial` (all serial tools), `matplotlib` (only `test_data.py` / `test.py`)

```bash
pip install pyserial matplotlib
```

## Usage

Connect the STM32 (Blackpill) over USB; it shows up as a USB CDC port (`/dev/ttyACM0` on Linux).
The baud rate does not matter for USB CDC.

```bash
python telemetry_frame.py /dev/ttyACM0                 # events + 1 s summary (default)
python telemetry_frame.py /dev/ttyACM0 --live 10       # + full data line 10x per second
python telemetry_frame.py /dev/ttyACM0 --dump          # + all fields at every summary
python telemetry_frame.py /dev/ttyACM0 --csv run.csv   # log every frame (all fields) to CSV
python telemetry_frame.py --file log.bin               # replay a recording (cat /dev/ttyACM0 > log.bin)
```

Other options: `--summary S` (summary interval), `--stuck S` (report a robot state that lasts longer
than S seconds). See `python telemetry_frame.py -h`.

The CSV columns are the frame field names; the simulator writes its logs in the same format, so one
set of analysis scripts works for both.

## Keeping the parser in sync with the firmware

`telemetry_frame.py` mirrors the C struct field by field. When the frame changes in the firmware
(`code/Core/Inc/App/core/telemetry/telemetry_pack.h`, `TELEMETRY_VERSION`):

1. update `_SECTIONS` (same order and types as the C struct),
2. update `VERSION` and `EXPECTED_SIZE`,
3. update the enum names (`ROBOT_STATES`, `CMD_NAMES`, `ERR_NAMES`) if the firmware enums changed.

The script asserts the expected frame size at import, so a layout mismatch fails immediately.

## License

MIT, see [LICENSE](LICENSE).
