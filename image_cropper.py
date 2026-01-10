import os
import sys
import time
import cv2
import pyautogui
import numpy as np
from pathlib import Path

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return str(os.path.join(base_path, "templates/" + relative_path))

APPDATA = Path(os.getenv("APPDATA")) / "AutoLootBot"
screenx, screeny = pyautogui.size()

def crop_screen(img, x1, y1, x2, y2):
    return img[y1:y2, x1:x2]

def find_icon_img(img, template_path, region=(0, 0, int(screenx), int(screeny)), threshold=0.8):
    template = cv2.imread(resource_path(template_path))

    # Crop region
    x, y, w, h = region
    cropped = img[y:y + h, x:x + w]
    # cv2.imwrite("debug_cropped.png", cropped)

    # Template match
    result = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    # If match too weak → return None
    if max_val < threshold:
        return None, None

    # Convert local coords → global screen coords
    template_h, template_w = template.shape[:2]
    match_x = x + max_loc[0] + template_w // 2
    match_y = y + max_loc[1] + template_h // 2

    # Return center of detected icon + confidence
    return match_x, match_y

def find_all_icon_img(img, template_path, region=(0, 0, screenx, screeny), text=False, threshold=0.85):
    template = cv2.imread(resource_path(template_path))

    # Region crop
    x, y, w, h = region
    cropped = img[y:y + h, x:x + w]
    if text:
        # 1. Convert to Grayscale
        cropped_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 2. Apply Top-Hat Transform
        # This filter subtracts the local background, leaving only bright features (text)
        # The kernel size (9,9) should be roughly the size of a single letter stroke thickness
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))

        cropped_processed = cv2.morphologyEx(cropped_gray, cv2.MORPH_TOPHAT, kernel)
        template_processed = cv2.morphologyEx(template_gray, cv2.MORPH_TOPHAT, kernel)

        # 3. (Optional) Small blur to smooth out JPEG artifacts
        # This helps fuse the pixels back together so they aren't "grainy"
        cropped_processed = cv2.GaussianBlur(cropped_processed, (3, 3), 0)
        template_processed = cv2.GaussianBlur(template_processed, (3, 3), 0)

        # Debug: Check these images! They should look like glowing text on black void.
        cv2.imwrite("debug_cropped_tophat.png", cropped_processed)
        cv2.imwrite("debug_template_tophat.png", template_processed)

        # 4. Match
        # We use CCOEFF_NORMED because we are now matching "intensity blobs"
        result = cv2.matchTemplate(cropped_processed, template_processed, cv2.TM_CCOEFF_NORMED)
        yloc, xloc = (result >= threshold).nonzero()
    else:
        # Normal template matching on color images
        result = cv2.matchTemplate(cropped, template, cv2.TM_CCOEFF_NORMED)
        yloc, xloc = (result >= threshold).nonzero()

    th, tw = template.shape[:2]

    points = []
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    for (px, py) in zip(xloc, yloc):
        cx = px + tw // 2
        cy = py + th // 2

        screen_x = x + cx
        screen_y = y + cy

        points.append((screen_x, screen_y))

    filtered = []
    radius = min(tw, th) // 2  # distance threshold

    for pt in points:
        if all(((pt[0] - f[0])**2 + (pt[1] - f[1])**2)**0.5 > radius for f in filtered):
            filtered.append(pt)

    return filtered


def exact_color_fraction(img, target_bgr=(112, 119, 224), tolerance=3, save=False):
    if img is None:
        raise ValueError("Could not load image")

    # Convert target to int16 to prevent overflow/underflow (e.g. 0 - 10 wrapping to 246)
    target = np.array(target_bgr, dtype=np.int16)

    lower = np.clip(target - tolerance, 0, 255).astype(np.uint8)
    upper = np.clip(target + tolerance, 0, 255).astype(np.uint8)

    # Returns a mask where 255 is a match and 0 is not
    mask = cv2.inRange(img, lower, upper)

    if save:
        debug_img = img.copy()
        # Apply highlight where mask is white (255)
        debug_img[mask > 0] = (255, 0, 255)
        cv2.imwrite("debug.png", debug_img)

    matched_pixels = cv2.countNonZero(mask)
    total_pixels = img.shape[0] * img.shape[1]

    if total_pixels == 0:
        return 0.0

    return matched_pixels / total_pixels


# print(find_all_icon_img("templates/wall.png",(800, 200, 400, 800), text=True, threshold=0.70))

# print(find_all_icon_img(resource_path("templates/testing.png"), (1000, 1000, 1000, 500), text=False, threshold=0.85))

# print(detect_by_saturation(1523, 792, 1628, 813))

# print(detect_brightest(1393, 496, 1456, 530))
# print(detect_brightest(1405, 422, 1465, 456))


