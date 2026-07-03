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

If multiple ADB devices are detected, you'll be prompted to select one with the arrow keys. The script will then start rolling — press `Ctrl+C` to stop at any time.

## Troubleshooting

**`TesseractNotFoundError` when running the script**
Tesseract-OCR isn't installed, or it's installed somewhere the script can't find automatically. Follow the manual path step above.

**`ModuleNotFoundError` for a package**
Make sure you're installing into the project's virtual environment, not your system Python:
```
.\venv\Scripts\pip install <package>
```

**Detection seems inconsistent (misses or false-matches values)**
The debug mode in `detection.py` (`DEBUG = True`) prints every OCR reading to the console and saves the exact cropped region it read from to a `debug_crops/` folder. Check those images against what the game actually shows to see whether it's a crop-framing issue or a timing issue (screenshot taken before the UI finished updating).