import json
import threading
import time
from io import open
import pyautogui
import cv2
import numpy as np

win_condition = '../resources/CPS1/win.png'
stream_control_file = "../data/scoreboard.json"

# Only allow player info to update once every 10 seconds
player_info_update_window = 15
last_score_update_timestamp = 0
has_updated = False

# Get the screen resolution size
screen_width, screen_height = pyautogui.size()
p1_left, p1_top, p1_width, p1_height = int(screen_width * 29 / 100), 150, 150, 85
p2_left, p2_top, p2_width, p2_height = int(screen_width * 65 / 100), 150, 150, 85
check_regions = True


def auto_update_scores():
    print("Auto score updater for CPS1 enabled")
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
        draw_region(screen, p1_left, p1_top, p1_width, p1_height)
        draw_region(screen, p2_left, p2_top, p2_width, p2_height)
        cv2.imshow('Captured Screen', screen)
        cv2.waitKey(0)


def check_win_conditions():
    show_regions()
    while True:
        if pyautogui.locateOnScreen(win_condition, region=(p1_left, p1_top, p1_width, p1_height), confidence=0.8):
            print("Player 1 Wins!")
            add_to_score("p1Score")
        elif pyautogui.locateOnScreen(win_condition, region=(p2_left, p2_top, p2_width, p2_height), confidence=0.8):
            print("Player 2 Wins!")
            add_to_score("p2Score")
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

