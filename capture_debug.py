"""
Quick one-off: saves a full-resolution screenshot exactly as the bot sees it
(same resolution client.capture_screen() uses), so you can open it in Paint
(or any editor that shows cursor pixel coordinates) and hover over buttons
to read off exact (x, y) values.

Usage:
    python capture_debug.py

Then run it once for EACH screen you need coordinates from:
  - the base gear screen (with the 4 padlocks + Confirm Equipment button)
  - the Change Substats popup (with Cancel/Apply)

It'll save to debug_crops/full_capture.png (overwritten each run — rename
between screens if you want to keep both, e.g. debug_crops/base_screen.png
and debug_crops/popup_screen.png).
"""

import os
import sys

import cv2
from adbutils import adb

from client import Client

devices = adb.device_list()
if not devices:
    print("No ADB devices found.")
    sys.exit(1)

serial = devices[0].serial
print(f"Using device: {serial}")

client = Client(serial=serial)
screen = client.capture_screen()

os.makedirs("debug_crops", exist_ok=True)
out_path = "debug_crops/full_capture.png"
# capture_screen() returns RGB (from PIL via asarray); cv2.imwrite expects BGR
cv2.imwrite(out_path, cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))
print(f"Saved {out_path}  (size: {screen.shape[1]}x{screen.shape[0]})")
