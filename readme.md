## Requirements

- Python 3
- An Android emulator with ADB enabled (LDPlayer, MuMu, BlueStacks, or NoxPlayer) (960 x 540 resolution with 160dpi)
- **Tesseract-OCR** (used to read substat values off the screen — see setup below)

## Setup

1. Clone the repo and run `run.bat`. On first run, it creates a virtual environment and installs everything in `requirements.txt` automatically.

2. **Install Tesseract-OCR** — this is a separate system program, not something `pip` can install on its own:
   - Download the installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Run it. During install, check **"Add to PATH"** if the option is offered — this lets the script find it automatically with no extra configuration.
   - If you skip that option (or the installer doesn't offer it), you'll need to manually point the script at your install location. Open `detection.py` and add this line near the top, right after the imports:
     ```python
     pytesseract.pytesseract.tesseract_cmd = r"C:\path\to\tesseract.exe"
     ```
     Replace the path with wherever the installer actually put `tesseract.exe` (commonly `C:\Program Files\Tesseract-OCR\tesseract.exe`, but check your own install).

3. Make sure your emulator is running with ADB enabled before launching `run.bat`.

## Running

```
run.bat
```

This launches the GUI (`gui.py`). Click **Refresh Devices** to detect your emulator, then pick a device from the dropdown.

There are two tabs:

- **Single Target** — the original mode. Rolls a single stat (e.g. Speed) until it hits a target value, then stops. Enter the target value and click **Start Rolling**.
- **Full Piece (Priority)** — rolls and locks an entire piece's 4 substats according to a ranked priority list. For each of the 4 priority slots, pick a stat category (a specific stat like "Speed", a generic "Any Flat Stat"/"Any % Stat", or the wildcard "Any (accept anything)"), and optionally an exact value if you want a specific roll amount. Priorities are filled strictly in order — priority #2 is never locked ahead of priority #1. Click **Start Full Roll**.

Click **Stop** at any time to halt either mode early. The log box at the bottom shows live progress, including OCR debug output if `DEBUG = True` in `detection.py`.

## How Full Piece (Priority) mode works

Make sure to have what you want prioritized at #1 because nothing else will lock until prio #1 is hit most people will choose to have Speed 5 at this priority. 
Will continuously reroll until priority #1 conditions are met and locked then move onto priority #2 and do the same, then when priority #3 and #4 are matched in the same reroll
confirm the equipement choice.  


**`TesseractNotFoundError` when running the script**
Tesseract-OCR isn't installed, or it's installed somewhere the script can't find automatically. Follow the manual path step above.

**`ModuleNotFoundError` for a package**
Make sure you're installing into the project's virtual environment, not your system Python:
```
.\venv\Scripts\pip install <package>
```

**Detection seems inconsistent (misses or false-matches values)**
The debug mode in `detection.py` (`DEBUG = True`) prints every OCR reading to the console and saves the exact cropped region it read from to a `debug_crops/` folder, plus a `*_context.png` showing that crop box drawn on the full screenshot. Check those against what the game actually shows to see whether it's a crop-framing issue or a timing issue (screenshot taken before the UI finished updating).

**Full Piece mode isn't locking/applying even though a match is clearly on screen**
Almost always a timing issue — the screenshot was taken before the popup/animation finished rendering, so the OCR read a stale or half-drawn screen. Try increasing the `sleep()` calls in `roll_full_piece` (in `full_roll.py`) after each click, especially after Change Substats/Replace.
