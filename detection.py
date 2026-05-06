import aircv as ac


def locate_image(screenshot, reference, threshold):
    result = ac.find_template(screenshot, ac.imread(f"images/{reference}"), threshold)
    return result['result'][:2] if result else None


def find_value(screenshot, coords, reference, threshold):
    x, y = int(coords[0]), int(coords[1])
    x_start = max(0, x + 100)
    x_end = min(screenshot.shape[1], x + 280)
    y_start = max(0, y - 40)
    y_end = min(screenshot.shape[0], y + 40)

    region = screenshot[y_start:y_end, x_start:x_end]
    result = ac.find_template(region, ac.imread(f"images/{reference}"), threshold)
    return result is not None

