import re
from time import sleep

import cv2

from detection import locate_image, read_row, is_percent, icon_matches_at

THRESHOLD = 0.85
CHANGE_SUBSTATS_COORDS = (360, 480)    

ROW_Y = [243, 274, 305, 336]           
ROW_ANCHOR_X = 403                     

LABEL_X_OFFSET = (0, 130)              
VALUE_X_OFFSET = (100, 280)            

LOCK_BUTTON_COORDS = [(267, 177), (267, 219), (267, 251), (267, 287)]

APPLY_COORDS = (558, 447)              
CONFIRM_EQUIPMENT_COORDS = (800, 470)  
REPLACE_COORDS = (500, 350)            

LOCKED_ICON_THRESHOLD = 0.9

BASE_ROW_ANCHOR_X = 300
BASE_LABEL_X_OFFSET = (-8, 100)
BASE_VALUE_X_OFFSET = (100, 280)

WILDCARD = "Any (accept anything)"
FLAT = "Any Flat Stat"
PERCENT = "Any % Stat"

KNOWN_STATS = [
    "Speed",
    "Attack", "Attack%",
    "Defense", "Defense%",
    "Health", "Health%",
    "Critical Hit Chance%",
    "Critical Hit Damage%",
    "Effectiveness%",
    "Effect Resistance%",
]

CATEGORY_OPTIONS = KNOWN_STATS + [FLAT, PERCENT, WILDCARD]

EPIC_RANGES = {
    "Speed": list(range(2, 6)),                   # 2-5
    "Attack": list(range(33, 47)),                 # 33-46
    "Attack%": list(range(4, 9)),                   # 4-8
    "Defense": list(range(28, 36)),                 # 28-35
    "Defense%": list(range(4, 9)),
    "Health": list(range(157, 203)),                # 157-202
    "Health%": list(range(4, 9)),
    "Critical Hit Chance%": list(range(3, 6)),      # 3-5
    "Critical Hit Damage%": list(range(4, 8)),      # 4-7
    "Effectiveness%": list(range(4, 9)),
    "Effect Resistance%": list(range(4, 9)),
}


def get_value_options(category):
    if category in EPIC_RANGES:
        return ["Any"] + [str(v) for v in EPIC_RANGES[category]]
    return ["Any"]


def _extract_int(value_text):
    match = re.search(r"\d+", value_text)
    return int(match.group()) if match else None


def category_matches(category, label_text, value_text, target_value=None):
    if category == WILDCARD:
        return True
    if category == FLAT:
        return not is_percent(value_text)
    if category == PERCENT:
        return is_percent(value_text)

    base_name = category.replace("%", "").strip().lower()
    label_clean = label_text.strip().lower()
    if base_name not in label_clean:
        return False
    if category.endswith("%") and not is_percent(value_text):
        return False
    if not category.endswith("%") and is_percent(value_text):
        return False

    if target_value is not None:
        return _extract_int(value_text) == target_value
    return True


def detect_existing_locks(client, log=print):
    screen = client.capture_screen()
    locked = [False, False, False, False]
    for i, coord in enumerate(LOCK_BUTTON_COORDS):
        if icon_matches_at(screen, "locked_icon.png", *coord, threshold=LOCKED_ICON_THRESHOLD, label=f"lock_slot{i}"):
            locked[i] = True

    lock_count = sum(locked)
    if lock_count:
        for i, (_, y) in enumerate(LOCK_BUTTON_COORDS):
            if not locked[i]:
                continue
            name, value = read_row(
                screen, BASE_ROW_ANCHOR_X, y,
                label_x_offset=BASE_LABEL_X_OFFSET, value_x_offset=BASE_VALUE_X_OFFSET,
                row_height=26, row_label=f"existing_row{i}", enhance=True, upscale=3,
                value_psm=8, value_enhance=False, value_interp=cv2.INTER_CUBIC,
            )
            log(f"Detected existing lock at slot {i}: '{name.strip()} {value.strip()}'")
        log(f"Resuming from priority #{lock_count + 1} ({lock_count} already locked).")
    return locked, lock_count


MAX_LOCKS = 2  


def roll_full_piece(client, priorities, max_rolls=3000, log=print, stop_event=None):
    assert len(priorities) == 4, "Priority list must have exactly 4 entries."

    locked, lock_count = detect_existing_locks(client, log=log)   
    next_priority_idx = lock_count                                 
    roll = 0

    log(f"Starting full-piece roll. Priorities: {priorities}")

    while roll < max_rolls:
        if stop_event is not None and stop_event.is_set():
            log(f"Stopped by user after {roll} rolls.")
            return False
        roll += 1

        client.click(CHANGE_SUBSTATS_COORDS)
        sleep(0.9)
        client.click(REPLACE_COORDS)
        sleep(0.9)

        screen = client.capture_screen()
        cancel_pos = locate_image(screen, "cancel.png", THRESHOLD)
        if not cancel_pos:
            log(f"Roll {roll}: popup not detected after clicking Change Substats "
                f"(cancel.png not found) — retrying.")
            sleep(0.9)
            continue

        rows = {}
        for i, y in enumerate(ROW_Y):
            if locked[i]:
                continue
            name, value = read_row(
                screen, ROW_ANCHOR_X, y,
                label_x_offset=LABEL_X_OFFSET, value_x_offset=VALUE_X_OFFSET,
                row_label=f"row{i}",
            )
            rows[i] = (name, value)

        if lock_count < MAX_LOCKS:
            matched = []  
            claimed_rows = set()
            check_idx = next_priority_idx
            while check_idx < 4 and lock_count + len(matched) < MAX_LOCKS:
                category, target_value = priorities[check_idx]
                found_row = None
                for i, (name, value) in rows.items():
                    if i in claimed_rows:
                        continue
                    if category_matches(category, name, value, target_value=target_value):
                        found_row = i
                        break
                if found_row is None:
                    break  
                matched.append((found_row, check_idx))
                claimed_rows.add(found_row)
                check_idx += 1

            if matched:
                client.click(APPLY_COORDS)
                sleep(0.9)
                for row_i, p_idx in matched:
                    category, target_value = priorities[p_idx]
                    target_desc = target_value if target_value is not None else "any"
                    name, value = rows[row_i]
                    log(f"Roll {roll}: locking row {row_i} ('{name.strip()} {value.strip()}') "
                        f"for priority #{p_idx + 1} ('{category}' = {target_desc})")
                    client.click(LOCK_BUTTON_COORDS[row_i])
                    sleep(0.9)
                    locked[row_i] = True
                    lock_count += 1
                    next_priority_idx = p_idx + 1
                continue  

            client.click(cancel_pos)
            sleep(0.9)
            continue

        else:
            remaining_priority_idxs = [2, 3]
            available_rows = list(rows.keys())
            match_ok = True
            for p_idx in remaining_priority_idxs:
                category, target_value = priorities[p_idx]
                found = None
                for i in available_rows:
                    name, value = rows[i]
                    if category_matches(category, name, value, target_value=target_value):
                        found = i
                        break
                if found is None:
                    match_ok = False
                    break
                available_rows.remove(found)

            if match_ok:
                log(f"Roll {roll}: remaining unlocked rows satisfy priorities #3 and #4. Finalizing...")
                client.click(APPLY_COORDS)
                sleep(0.9)
                client.click(CONFIRM_EQUIPMENT_COORDS)
                return True

            client.click(cancel_pos)
            sleep(0.9)
            continue

    log(f"Stopped after {roll} rolls without satisfying all priorities (max_rolls reached).")
    return False
