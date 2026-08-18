#!/usr/bin/env python3

import os
import sys
import time

try:
    import serial
except Exception as exc:  # pragma: no cover
    print(f"pyserial not available: {exc}", file=sys.stderr)
    sys.exit(1)

paths = [
    "/dev/robot_arduino",
    "/dev/robot_lidar",
    "/dev/robot_camera",
]

for path in paths:
    deadline = time.time() + 30.0
    while time.time() < deadline:
        if not os.path.exists(path):
            time.sleep(0.2)
            continue

        if "tty" in path:
            try:
                port = serial.Serial(path, timeout=0.5)
                port.close()
                print(f"{path}: serial port opened successfully")
                break
            except Exception:
                time.sleep(0.2)
                continue
        else:
            print(f"{path}: device file exists")
            break
    else:
        print(f"ERROR: device not ready in time: {path}", file=sys.stderr)
        sys.exit(1)

print("All robot hardware devices are ready")
