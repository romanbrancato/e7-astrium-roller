import re
import os
import cv2
import aircv as ac
import pytesseract

DEBUG = False  # flip to True if you want to see reroll values or if you have trust issues
# If you have to manually assign path change to whatever your path is
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  

def locate_image(screenshot, reference, threshold):
    result = ac.find_template(screenshot, ac.imread(f"images/{reference}"), threshold)
    return result['result'][:2] if result else None


def _ocr_crop(screenshot, x_start, x_end, y_start, y_end, whitelist=None, psm=7, label=""):
    x_start = max(0, x_start)
    y_start = max(0, y_start)
    x_end = min(screenshot.shape[1], x_end)
    y_end = min(screenshot.shape[0], y_end)
    region = screenshot[y_start:y_end, x_start:x_end]

    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    text = pytesseract.image_to_string(region, config=config).strip()

    if DEBUG:
        print(f"[OCR] {label or (x_start, y_start)} -> raw: {text!r}")
        os.makedirs("debug_crops", exist_ok=True)
        safe_label = (label or f"{x_start}_{y_start}").replace(" ", "_")
        cv2.imwrite(f"debug_crops/{safe_label}.png", region)

    return text


def read_stat_value(screenshot, anchor_x, y, x_offset=(100, 280), row_height=30, label=""):
    """OCR the numeric value portion of a substat row (e.g. '+5', '12%')."""
    return _ocr_crop(
        screenshot,
        anchor_x + x_offset[0], anchor_x + x_offset[1],
        y - row_height // 2, y + row_height // 2,
        whitelist="0123456789+.%",
        label=f"{label}_value" if label else "",
    )


def read_stat_label(screenshot, anchor_x, y, x_offset=(-270, -5), row_height=30, label=""):
    return _ocr_crop(
        screenshot,
        anchor_x + x_offset[0], anchor_x + x_offset[1],
        y - row_height // 2, y + row_height // 2,
        whitelist=None,
        psm=7,
        label=f"{label}_name" if label else "",
    )


def read_row(screenshot, anchor_x, y, label_x_offset=(-270, -5), value_x_offset=(100, 280),
             row_height=30, row_label=""):
    """Reads both the stat name and value for one substat row. Returns (name_text, value_text)."""
    name = read_stat_label(screenshot, anchor_x, y, x_offset=label_x_offset,
                            row_height=row_height, label=row_label)
    value = read_stat_value(screenshot, anchor_x, y, x_offset=value_x_offset,
                             row_height=row_height, label=row_label)
    return name, value


def is_percent(value_text):
    """True if the value text contains a % sign (i.e. it's a percentage stat, not flat)."""
    return "%" in value_text


def find_value(screenshot, coords, target_value, label=""):
    """Kept for the original single-target speed roller: exact-match a numeric
    target at a known (x, y) position, e.g. from locate_image('max_speed.png', ...)."""
    x, y = int(coords[0]), int(coords[1])
    text = read_stat_value(screenshot, x, y, label=label)
    match = re.search(r"\d+", text)
    if not match:
        return False
    return int(match.group()) == target_value
