import json
import threading
import time
from io import open
import pyautogui

p1_win_condition = '../resources/cvs2/p1_win.png'
p2_win_condition = '../resources/cvs2/p2_win.png'
stream_control_file = "../scoreboard/sc/streamcontrol.json"

# Only allow player info to update once every 10 seconds
player_info_update_window = 30
last_score_update_timestamp = 0


def auto_update_scores():
    print("Auto score updater for CVS2 enabled")
    checker = threading.Thread(target=check_win_conditions, args=(), daemon=True)
    checker.start()


def check_win_conditions():
    while True:
        if pyautogui.locateCenterOnScreen(p1_win_condition, confidence=0.8):
            print("Player 1 Wins!")
            add_to_score("p1Score")
        elif pyautogui.locateCenterOnScreen(p2_win_condition, confidence=0.8):
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


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result

