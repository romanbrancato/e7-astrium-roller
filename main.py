import msvcrt
import os
import sys
import time
from time import sleep

from adbutils import adb

from client import Client
from detection import locate_image, find_value

THRESHOLD = 0.90

REPLACE_COORDS = (500, 350)
CHANGE_SUBSTATS_COORDS = (360, 480)


def get_key():
    if msvcrt.kbhit():
        key = msvcrt.getch()
        if key == b'\xe0':
            key = msvcrt.getch()
            if key == b'H':
                return 'UP'
            elif key == b'P':
                return 'DOWN'
        elif key == b'\r':
            return 'ENTER'
        elif key == b'q' or key == b'Q':
            return 'QUIT'
    return None


def display_devices(devices, selected_idx):
    os.system('cls')
    print("Available devices:")
    print("------------------")
    for i, device in enumerate(devices):
        prefix = "→ " if i == selected_idx else "  "
        print(f"{prefix} {device.serial}")
    print("\nUse ↑/↓ arrow keys to navigate, Enter to select, q to quit")


def select_device(devices):
    selected_idx = 0
    display_devices(devices, selected_idx)
    while True:
        key = get_key()
        time.sleep(0.1)
        if key == 'UP':
            selected_idx = (selected_idx - 1) % len(devices)
            display_devices(devices, selected_idx)
        elif key == 'DOWN':
            selected_idx = (selected_idx + 1) % len(devices)
            display_devices(devices, selected_idx)
        elif key == 'ENTER':
            return devices[selected_idx].serial
        elif key == 'QUIT':
            print("\nExiting...")
            sys.exit(0)


def run(client):
    roll = 0
    print("Rolling... (press Ctrl+C to stop)")
    while True:
        roll += 1
        client.click(REPLACE_COORDS)
        sleep(0.1)

        screen = client.capture_screen()
        cancel_pos = locate_image(screen, "cancel.png", THRESHOLD)
        if not cancel_pos:
            continue

        max_speed_pos = locate_image(screen, "max_speed.png", THRESHOLD)
        if max_speed_pos and find_value(screen, max_speed_pos, "5.png", THRESHOLD):
            print(f"5 speed found on roll {roll}!")
            return

        client.click(cancel_pos)
        sleep(0.1)
        client.click(CHANGE_SUBSTATS_COORDS)
        sleep(0.4)


def main():
    devices = adb.device_list()
    if not devices:
        print("No devices found. Make sure an emulator or device is connected.")
        sys.exit(1)

    if len(devices) == 1:
        device_serial = devices[0].serial
    else:
        device_serial = select_device(devices)

    client = Client(serial=device_serial)
    run(client)


if __name__ == '__main__':
    main()
