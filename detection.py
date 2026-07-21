import re
import os
import cv2
import aircv as ac
import pytesseract

DEBUG = True  # flip to False once you trust the readings
pytesseract.pytesseract.tesseract_cmd = r"C:\path\to\tesseract.exe"

def locate_image(screenshot, reference, threshold):
    result = ac.find_template(screenshot, ac.imread(f"images/{reference}"), threshold)
    return result['result'][:2] if result else None


def icon_matches_at(screenshot, reference, x, y, box=18, threshold=0.8, label=""):
    x_start = max(0, x - box)
    y_start = max(0, y - box)
    x_end = min(screenshot.shape[1], x + box)
    y_end = min(screenshot.shape[0], y + box)
    region = screenshot[y_start:y_end, x_start:x_end]
    template = ac.imread(f"images/{reference}")

    raw = ac.find_template(region, template, 0)
    confidence = raw['confidence'] if raw else None

    result = ac.find_template(region, template, threshold)

    if DEBUG:
        safe_label = (label or f"{x}_{y}").replace(" ", "_")
        print(f"[ICON] {safe_label} -> confidence: {confidence!r} "
              f"(threshold {threshold}, region {region.shape[1]}x{region.shape[0]})")
        os.makedirs("debug_crops", exist_ok=True)
        cv2.imwrite(f"debug_crops/{safe_label}_region.png", region)
        cv2.imwrite(f"debug_crops/{safe_label}_template.png", template)

    return result is not None


def _ocr_crop(screenshot, x_start, x_end, y_start, y_end, whitelist=None, psm=7, label="",
               enhance=False, upscale=1, interp=cv2.INTER_NEAREST):
    x_start = max(0, x_start)
    y_start = max(0, y_start)
    x_end = min(screenshot.shape[1], x_end)
    y_end = min(screenshot.shape[0], y_end)
    region = screenshot[y_start:y_end, x_start:x_end]

    ocr_input = region
    if upscale != 1:
        ocr_input = cv2.resize(ocr_input, None, fx=upscale, fy=upscale, interpolation=interp)
    if enhance:
        gray = cv2.cvtColor(ocr_input, cv2.COLOR_BGR2GRAY)
        ocr_input = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"

    text = pytesseract.image_to_string(ocr_input, config=config).strip()

    if DEBUG:
        print(f"[OCR] {label or (x_start, y_start)} -> raw: {text!r} "
              f"(crop box: x={x_start}-{x_end}, y={y_start}-{y_end}, enhance={enhance}, upscale={upscale})")
        os.makedirs("debug_crops", exist_ok=True)
        safe_label = (label or f"{x_start}_{y_start}").replace(" ", "_")
        cv2.imwrite(f"debug_crops/{safe_label}.png", ocr_input)

        context = screenshot.copy()
        cv2.rectangle(context, (x_start, y_start), (x_end, y_end), (0, 0, 255), 2)
        cv2.imwrite(f"debug_crops/{safe_label}_context.png", context)

    return text


def read_stat_value(screenshot, anchor_x, y, x_offset=(100, 280), row_height=30, label="", enhance=False,
                     upscale=1, psm=7, interp=cv2.INTER_NEAREST):
    return _ocr_crop(
        screenshot,
        anchor_x + x_offset[0], anchor_x + x_offset[1],
        y - row_height // 2, y + row_height // 2,
        whitelist="0123456789+.%",
        psm=psm,
        label=f"{label}_value" if label else "",
        enhance=enhance,
        upscale=upscale,
        interp=interp,
    )


def read_stat_label(screenshot, anchor_x, y, x_offset=(-270, -5), row_height=30, label="", enhance=False, upscale=1):
    return _ocr_crop(
        screenshot,
        anchor_x + x_offset[0], anchor_x + x_offset[1],
        y - row_height // 2, y + row_height // 2,
        whitelist=None,
        psm=7,
        label=f"{label}_name" if label else "",
        enhance=enhance,
        upscale=upscale,
    )


def read_row(screenshot, anchor_x, y, label_x_offset=(-270, -5), value_x_offset=(100, 280),
             row_height=30, row_label="", enhance=False, upscale=1, value_psm=7, value_enhance=None,
             value_interp=cv2.INTER_NEAREST):
    if value_enhance is None:
        value_enhance = enhance
    name = read_stat_label(screenshot, anchor_x, y, x_offset=label_x_offset,
                            row_height=row_height, label=row_label, enhance=enhance, upscale=upscale)
    value = read_stat_value(screenshot, anchor_x, y, x_offset=value_x_offset,
                             row_height=row_height, label=row_label, enhance=value_enhance, upscale=upscale,
                             psm=value_psm, interp=value_interp)
    return name, value


def is_percent(value_text):
    return "%" in value_text


def find_value(screenshot, coords, target_value, label=""):
    x, y = int(coords[0]), int(coords[1])
    text = read_stat_value(screenshot, x, y, label=label)
    match = re.search(r"\d+", text)
    if not match:
        return False
    return int(match.group()) == target_value
