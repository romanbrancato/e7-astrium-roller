import os
import sys
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from adbutils import adb

from client import Client
from detection import locate_image, find_value
import main as bot  
from full_roll import roll_full_piece, CATEGORY_OPTIONS, get_value_options

THRESHOLD = bot.THRESHOLD
REPLACE_COORDS = bot.REPLACE_COORDS
CHANGE_SUBSTATS_COORDS = bot.CHANGE_SUBSTATS_COORDS


class StdoutRedirector:
    """Routes print() output (including OCR debug lines from detection.py)
    into a thread-safe queue so the GUI log box can display it."""

    def __init__(self, out_queue):
        self.out_queue = out_queue

    def write(self, text):
        if text.strip():
            self.out_queue.put(text if text.endswith("\n") else text + "\n")

    def flush(self):
        pass


class RollerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("E7 Astrium Roller")
        self.root.geometry("680x500")
        self.root.minsize(560, 400)

        self.stop_event = threading.Event()
        self.worker_thread = None
        self.devices = []
        self.out_queue = queue.Queue()

        self._build_widgets()
        self._poll_queue()

    def _build_widgets(self):
        # --- Device row, shared by both modes ---
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Device:").grid(row=0, column=0, sticky="w")
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(top, textvariable=self.device_var, state="readonly", width=25)
        self.device_combo.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Button(top, text="Refresh Devices", command=self.refresh_devices).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Reset ADB Connection", command=self.reset_adb).grid(row=0, column=3, padx=4)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="x", padx=10, pady=(0, 4))

        single_tab = ttk.Frame(notebook, padding=10)
        full_tab = ttk.Frame(notebook, padding=10)
        notebook.add(single_tab, text="Single Target")
        notebook.add(full_tab, text="Full Piece (Priority)")

        # Single-target tab
        ttk.Label(single_tab, text="Target value:").grid(row=0, column=0, sticky="w")
        self.target_var = tk.StringVar(value="5")
        ttk.Entry(single_tab, textvariable=self.target_var, width=5).grid(row=0, column=1, sticky="w", padx=(4, 20))

        self.start_single_btn = ttk.Button(single_tab, text="Start Rolling", command=self.start_rolling)
        self.start_single_btn.grid(row=0, column=2, padx=4)

        self.stop_single_btn = ttk.Button(single_tab, text="Stop", command=self.stop_rolling, state="disabled")
        self.stop_single_btn.grid(row=0, column=3, padx=4)

        self.priority_stat_vars = []
        self.priority_value_vars = []
        for i in range(4):
            ttk.Label(full_tab, text=f"Priority {i + 1}:").grid(row=i, column=0, sticky="w", pady=2)

            stat_var = tk.StringVar(value=CATEGORY_OPTIONS[-1])  # default to wildcard
            stat_combo = ttk.Combobox(full_tab, textvariable=stat_var, state="readonly",
                                       values=CATEGORY_OPTIONS, width=22)
            stat_combo.grid(row=i, column=1, sticky="w", padx=4, pady=2)

            value_var = tk.StringVar(value="Any")
            value_combo = ttk.Combobox(full_tab, textvariable=value_var, state="readonly",
                                        values=["Any"], width=8)
            value_combo.grid(row=i, column=2, sticky="w", padx=4, pady=2)

            # When the stat changes, repopulate the value dropdown with that
            # stat's Epic-grade possible roll amounts (or just "Any" for the
            # generic Flat/Percent/Wildcard categories).
            def on_stat_change(event, sv=stat_var, vv=value_var, vc=value_combo):
                options = get_value_options(sv.get())
                vc["values"] = options
                vv.set("Any")

            stat_combo.bind("<<ComboboxSelected>>", on_stat_change)

            self.priority_stat_vars.append(stat_var)
            self.priority_value_vars.append(value_var)

        self.start_full_btn = ttk.Button(full_tab, text="Start Full Roll", command=self.start_full_roll)
        self.start_full_btn.grid(row=0, column=3, padx=10)

        self.stop_full_btn = ttk.Button(full_tab, text="Stop", command=self.stop_rolling, state="disabled")
        self.stop_full_btn.grid(row=1, column=3, padx=10)

        # --- Log + status, shared ---
        self.log_box = scrolledtext.ScrolledText(self.root, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_var = tk.StringVar(value="Idle. Click 'Refresh Devices' to begin.")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    def log(self, msg):
        self.out_queue.put(msg + "\n")

    def _poll_queue(self):
        try:
            while True:
                msg = self.out_queue.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", msg)
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def refresh_devices(self):
        self.status_var.set("Searching for ADB...")

        def worker():
            try:
                devices = adb.device_list()
            except Exception as e:
                self.log(f"Error querying adb: {e}")
                self.status_var.set("Error querying adb.")
                return
            if not devices:
                self.log("No devices found. Make sure the emulator is running with ADB enabled.")
                self.status_var.set("No devices found.")
                return
            serials = [d.serial for d in devices]
            self.devices = serials
            self.device_combo["values"] = serials
            self.device_var.set(serials[0])
            self.log(f"Found devices: {serials}")
            self.status_var.set("Devices refreshed.")

        threading.Thread(target=worker, daemon=True).start()

    def reset_adb(self):
        self.status_var.set("Resetting ADB connection...")

        def worker():
            self.log("Killing adb.exe...")
            subprocess.run(["taskkill", "/F", "/IM", "adb.exe"], capture_output=True)
            time.sleep(1.5)

            # Mirrors manually running run.bat twice: query, wait, query again.
            # The first device_list() call after a kill often restarts the adb
            # server as a side effect but returns no devices yet; the second
            # call is the one that actually sees them.
            self.log("Querying devices (pass 1)...")
            try:
                adb.device_list()
            except Exception as e:
                self.log(f"Error on pass 1: {e}")
            time.sleep(1.5)

            self.log("Querying devices (pass 2)...")
            try:
                devices = adb.device_list()
            except Exception as e:
                self.log(f"Error on pass 2: {e}")
                self.status_var.set("Error querying adb.")
                return

            if devices:
                serials = [d.serial for d in devices]
                self.devices = serials
                self.device_combo["values"] = serials
                self.device_var.set(serials[0])
                self.log(f"ADB reset succeeded. Devices: {serials}")
                self.status_var.set("ADB reset complete.")
            else:
                self.log(
                    "Still no devices after reset. If this keeps happening, you may "
                    "still need to manually toggle ADB off/on in BlueStacks settings."
                )
                self.status_var.set("Reset failed - check BlueStacks ADB setting.")

        threading.Thread(target=worker, daemon=True).start()

    def _set_running_state(self, running):
        state_running = "disabled" if running else "normal"
        state_stop = "normal" if running else "disabled"
        self.start_single_btn.configure(state=state_running)
        self.start_full_btn.configure(state=state_running)
        self.stop_single_btn.configure(state=state_stop)
        self.stop_full_btn.configure(state=state_stop)

    def start_rolling(self):
        if not self.device_var.get():
            messagebox.showwarning("No device", "Select a device first (click Refresh Devices).")
            return
        try:
            target = int(self.target_var.get())
        except ValueError:
            messagebox.showwarning("Invalid target", "Target value must be a whole number.")
            return

        self.stop_event.clear()
        self._set_running_state(True)
        self.status_var.set("Rolling...")

        def worker():
            client = Client(serial=self.device_var.get())
            roll = 0
            self.log(f"Rolling started, target = {target}. Click Stop to end early.")
            while not self.stop_event.is_set():
                roll += 1
                client.click(REPLACE_COORDS)
                time.sleep(0.8)

                screen = client.capture_screen()
                cancel_pos = locate_image(screen, "cancel.png", THRESHOLD)
                if not cancel_pos:
                    continue

                max_speed_pos = locate_image(screen, "max_speed.png", THRESHOLD)
                if max_speed_pos and find_value(screen, max_speed_pos, target, label="Speed"):
                    self.log(f"Target {target} found on roll {roll}!")
                    break

                client.click(cancel_pos)
                time.sleep(0.3)
                client.click(CHANGE_SUBSTATS_COORDS)
                time.sleep(0.6)

            if self.stop_event.is_set():
                self.status_var.set("Stopped by user.")
            else:
                self.status_var.set("Done - target found!")
            self._set_running_state(False)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def start_full_roll(self):
        if not self.device_var.get():
            messagebox.showwarning("No device", "Select a device first (click Refresh Devices).")
            return

        priorities = []
        for stat_var, value_var in zip(self.priority_stat_vars, self.priority_value_vars):
            category = stat_var.get()
            value_str = value_var.get()
            target_value = None if value_str == "Any" else int(value_str)
            priorities.append((category, target_value))

        self.stop_event.clear()
        self._set_running_state(True)
        self.status_var.set("Rolling full piece...")

        def worker():
            client = Client(serial=self.device_var.get())
            success = roll_full_piece(client, priorities, log=self.log, stop_event=self.stop_event)
            if success:
                self.status_var.set("Full piece complete - all priorities locked and applied!")
            else:
                self.status_var.set("Stopped or hit max rolls without completing.")
            self._set_running_state(False)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def stop_rolling(self):
        self.stop_event.set()
        self.status_var.set("Stopping...")


def main():
    root = tk.Tk()
    app = RollerGUI(root)
    sys.stdout = StdoutRedirector(app.out_queue)  # route print()/OCR debug lines into the log box
    root.mainloop()


if __name__ == "__main__":
    main()
