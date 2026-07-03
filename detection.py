import re
import os
import cv2
import aircv as ac
import pytesseract


DEBUG = False


def locate_image(screenshot, reference, threshold):
    result = ac.find_template(screenshot, ac.imread(f"images/{reference}"), threshold)
    return result['result'][:2] if result else None


def read_stat_value(screenshot, coords, label="", x_offset=(100, 280), row_height=30):
    x, y = int(coords[0]), int(coords[1])
    x_start = max(0, x + x_offset[0])
    x_end = min(screenshot.shape[1], x + x_offset[1])
    y_start = max(0, y - row_height // 2)
    y_end = min(screenshot.shape[0], y + row_height // 2)

    region = screenshot[y_start:y_end, x_start:x_end]
    text = pytesseract.image_to_string(
        region,
        config="--psm 7 -c tessedit_char_whitelist=0123456789+.%"
    )
    text = text.strip()

    if DEBUG:
        print(f"[OCR] {label or coords} -> raw: {text!r}")
        os.makedirs("debug_crops", exist_ok=True)
        safe_label = label.replace(" ", "_") or f"{x}_{y}"
        cv2.imwrite(f"debug_crops/{safe_label}.png", region)

    return text


def find_value(screenshot, coords, target_value, label=""):
    text = read_stat_value(screenshot, coords, label=label)
    match = re.search(r"\d+", text)
    if not match:
        return False
    return int(match.group()) == target_value
