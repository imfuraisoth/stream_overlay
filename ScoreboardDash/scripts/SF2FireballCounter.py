import json
import threading
import time
from io import open
import pyautogui
import cv2
import numpy as np


def get_image_to_match(filename):
    image_with_alpha = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    # Convert the image to BGR format without transparency
    image_to_detect = image_with_alpha[:, :, :3]
    # Apply the mask to the template
    template = image_with_alpha[:, :, 3]
    # template = cv2.merge([template, template, template])

    image_to_detect = cv2.bitwise_and(image_to_detect, image_to_detect, mask=template)

    # template = cv2.bitwise_not(template)
    cv2.imwrite('template.png', template)
    cv2.imwrite('image_to_detect.png', image_to_detect)
    image_to_detect = cv2.cvtColor(image_to_detect, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('image_to_detect_gray.png', image_to_detect)
    return image_to_detect, template


KO, KO_mask = get_image_to_match('../resources/hf/KO.png')
KO2, KO2_mask = get_image_to_match('../resources/hf/KO2.png')
hado_left, hado_left_mask = get_image_to_match('../resources/hf/hado_left.png')
hado_right, hado_right_mask = get_image_to_match('../resources/hf/hado_right.png')
# sim_fire_left, sim_left_mask = get_image_to_match('../resources/hf/sim_fire_left.png')
# sim_fire_right, sim_right_mask = get_image_to_match('../resources/hf/sim_fire_right.png')

hado_count_file = "../data/hado_count.txt"
sim_fire_count_file = "../data/sim_fire_count.txt"
tiger_count_file = "../data/tiger_count.txt"

# Only allow player info to update once every 1.5 seconds
player_info_update_window = 1500
last_score_update_timestamp = 0
has_updated = False

# Set a threshold to determine if the image is on the screen
threshold = 0.41  # Adjust this threshold as needed
hado_right_threshold = 0.44
ko_threshold = 0.6


def enable_counter():
    print("Fireball counter enabled")
    checker = threading.Thread(target=check_conditions, args=(), daemon=True)
    checker.start()


def check_conditions():
    while True:
        # Capture the screen as an in-memory image
        screenshot = pyautogui.screenshot()
        screenshot = np.array(screenshot)
        # screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        if not check_image(screenshot, KO, KO_mask, ko_threshold) and not check_image(screenshot, KO2, KO2_mask, ko_threshold):
            time.sleep(0.01)
            print("Not in match")
            continue
        elif check_image(screenshot, hado_left, hado_left_mask, threshold):
            add_to_count(hado_count_file)
            print("Hado left")
        elif check_image(screenshot, hado_right, hado_right_mask, hado_right_threshold):
            add_to_count(hado_count_file)
            print("Hado right")
        time.sleep(0.01)


def check_image(screenshot, image, mask, threshold_to_use):
    return check_image_debug(screenshot, image, mask, threshold_to_use, False)


def check_image_debug(screenshot, image, mask, threshold_to_use, debug):
    # Match the template while ignoring the transparent pixels
    result = cv2.matchTemplate(screenshot, image, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    print(max_val)
    flag = max_val != float("inf") and max_val >= threshold_to_use
    if debug and flag:
        print_output(screenshot, image, mask, result)
    return flag


def print_output(screenshot, image, mask, result):
    loc = np.where(result >= threshold)
    hh, ww = image.shape[:2]
    # draw matches
    result = screenshot.copy()
    for pt in zip(*loc[::-1]):
        cv2.rectangle(result, pt, (pt[0]+ww, pt[1]+hh), (0, 0, 255), 1)
        #print(pt)

    # save results
    cv2.imwrite('bananas_base.png', image)
    cv2.imwrite('bananas_alpha.png', mask)
    cv2.imwrite('game_bananas_matches.jpg', result)

    # cv2.imshow('base', image)
    # cv2.imshow('alpha', mask)
    cv2.imshow('result', result)
    cv2.waitKey(0)


def add_to_count(file_name):
    global last_score_update_timestamp
    current_time = int(time.time() * 1000)
    if current_time - player_info_update_window < last_score_update_timestamp:
        print("Within window")
        return

    count = read_file(file_name) + 1
    last_score_update_timestamp = current_time
    with open(file_name, 'w', encoding="utf-8") as file:
        file.write(json.dumps(count, ensure_ascii=False))


def read_file(file_name):
    with open(file_name) as file:
        line = file.readline()
        if len(line) == 0:
            result = 0
        else:
            result = int(line)
        file.close()
        return result

