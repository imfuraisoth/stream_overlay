import json
import threading
import time
from io import open
import pyautogui
import cv2
import numpy as np


def get_image_to_match(filename):
    image_with_alpha = cv2.imread(filename, cv2.COLOR_BGR2GRAY)
    # Convert the image to BGR format without transparency
    image_to_detect = image_with_alpha[:, :, :3]
    # Apply the mask to the template
    # template = image_with_alpha[:, :, 3]
    # template = cv2.merge([template, template, template])

    image_to_detect = cv2.bitwise_and(image_to_detect, image_to_detect)

    # template = cv2.bitwise_not(template)
    # cv2.imwrite('template.png', template)
    cv2.imwrite('image_to_detect.png', image_to_detect)
    image_to_detect = cv2.cvtColor(image_to_detect, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('image_to_detect_gray.png', image_to_detect)
    return image_to_detect, image_to_detect


p1_win_condition, p1_mask = get_image_to_match('../resources/cvs2/p1_win.png')
# p1_win_1_condition = '../resources/cvs2/p1_win_1.png'
# p1_win_2_condition = '../resources/cvs2/p1_win_2.png'
# p2_win_condition = '../resources/cvs2/p2_win.png'
# p2_win_1_condition = '../resources/cvs2/p2_win_1.png'
p2_win_condition, p2_mask = get_image_to_match('../resources/cvs2/p2_win.png')
# p2_win_s_condition = '../resources/cvs2/p2_win_s.png'

win_condition_1, win_mask_1 = get_image_to_match('../resources/cvs2/1_win_black_bg.png')
win_condition_2, win_mask_2 = get_image_to_match('../resources/cvs2/1_win_blue_bg.png')

stream_control_file = "../data/scoreboard.json"

# Only allow player info to update once every 10 seconds
player_info_update_window = 30
last_score_update_timestamp = 0
has_updated = False
# Set a threshold to determine if the image is on the screen
threshold = 0.8  # Adjust this threshold as needed

# Get the screen resolution size
screen_width, screen_height = pyautogui.size()
# Set the region to capture (left, top, width, height)
p1_region = (screen_width * 44 / 100, 70, 200, 100)  # Update with your desired region
p2_region = (screen_width * 77 / 100, 70, 200, 100)  # Update with your desired region
check_regions = True


def auto_update_scores():
    print("Auto score updater for CVS2 enabled")
    checker = threading.Thread(target=check_win_conditions, args=(), daemon=True)
    checker.start()


def draw_region(image, x, y, width, height):
    cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)  # Draw a green rectangle


def capture_screen(region):
    screenshot = cv2.cvtColor(np.array(pyautogui.screenshot(region=region)), cv2.COLOR_RGB2BGR)
    return screenshot


def show_regions():
    if check_regions:
        capture_region = (0, 0, screen_width, screen_height)
        screen = capture_screen(capture_region)
        draw_region(screen, p1_region[0], p1_region[1], p1_region[2], p1_region[3])
        draw_region(screen, p2_region[0], p2_region[1], p2_region[2], p2_region[3])
        cv2.imshow('Captured Screen', screen)
        cv2.waitKey(0)


def check_win_conditions():
    show_regions()
    while True:
        # Capture the screen as an in-memory image
        screenshot_p1 = pyautogui.screenshot(region=p1_region)
        screenshot = np.array(screenshot_p1)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        if check_image(screenshot, win_condition_1, win_mask_1, threshold):
            print("Player 1 Wins!")
            add_to_score("p1Score")
            time.sleep(1)
            continue
        elif check_image(screenshot, win_condition_2, win_mask_2, threshold):
            print("Player 1 Wins!!")
            add_to_score("p1Score")
            time.sleep(1)
            continue

        screenshot_p2 = pyautogui.screenshot(region=p2_region)
        screenshot = np.array(screenshot_p2)
        # screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        if check_image(screenshot, win_condition_1, win_mask_1, threshold):
            print("Player 2 Wins!")
            add_to_score("p2Score")
            time.sleep(1)
            continue
        elif check_image(screenshot, win_condition_2, win_mask_2, threshold):
            print("Player 2 Wins!!")
            add_to_score("p2Score")

        # elif pyautogui.locateCenterOnScreen(p1_win_2_condition, confidence=0.8):
        #     print("Player 1 Wins!!!")
        #     add_to_score("p1Score")
        # elif pyautogui.locateCenterOnScreen(p2_win_condition, confidence=0.8):
        #     print("Player 2 Wins!")
        #     add_to_score("p2Score")
        # elif pyautogui.locateCenterOnScreen(p2_win_1_condition, confidence=0.8):
        #     print("Player 2 Wins!!")
        #     add_to_score("p2Score")
        # elif pyautogui.locateCenterOnScreen(p2_win_2_condition, confidence=0.8):
        #     print("Player 2 Wins!!!")
        #     add_to_score("p2Score")
        # Check once a second
        time.sleep(1)


def add_to_score(score_key):
    global last_score_update_timestamp
    current_time = time.time()
    if current_time - player_info_update_window < last_score_update_timestamp:
        return

    full_data = read_file(stream_control_file)
    current_score = int(full_data[score_key])
    max_score = int(full_data["maxScore"])
    if current_score >= max_score:
        return

    last_score_update_timestamp = current_time
    full_data[score_key] = str(current_score + 1)
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))
        global has_updated
        has_updated = True


def has_updated_score():
    global has_updated
    if has_updated:
        has_updated = False
        return True    
    return has_updated


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


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
