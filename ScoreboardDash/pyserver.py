import json
from io import open
from flask import Flask
from flask import request
from flask_cors import CORS
import time
from scripts import AutoScoreUpdater

server_info = open('../config/serverip.txt', 'r').readline().split(':')

hostName = server_info[0]
serverPort = server_info[1]

stream_control_file = "../scoreboard/sc/streamcontrol.json"
player_1 = "../data/player1.txt"
player_2 = "../data/player2.txt"
next_player_1 = "../data/nextplayer1.txt"
next_player_2 = "../data/nextplayer2.txt"
result1 = "../data/result1.txt"
result2 = "../data/result2.txt"
result_name_1 = "../data/resultname1.txt"
result_name_2 = "../data/resultname2.txt"

api = Flask(__name__)
CORS(api)

previous_player_1 = (0, 0.0)
previous_player_2 = (0, 0.0)
# Only allow player info to update once a second
player_info_update_window = 1
auto_score_updater = AutoScoreUpdater


@api.route('/getdata', methods=['GET'])
def get_data():
    return json.dumps(read_file(stream_control_file), ensure_ascii=False), 200


@api.route('/updatealldata', methods=['POST'])
def update_all_data():
    json_data = request.get_json()
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(json_data))
    write_to_file(player_1, "p1Name", json_data)
    write_to_file(player_2, "p2Name", json_data)
    write_to_file(next_player_1, "nextplayer1", json_data)
    write_to_file(next_player_2, "nextplayer2", json_data)
    write_to_file(result1, "resultscore1", json_data)
    write_to_file(result2, "resultscore2", json_data)
    write_to_file(result_name_1, "resultplayer1", json_data)
    write_to_file(result_name_2, "resultplayer2", json_data)
    return "200"


@api.route('/updateplayer1', methods=['POST'])
def update_player1():
    global previous_player_1
    json_data = request.get_json()
    player_id = json_data["id"]

    previous_id, previous_timestamp = previous_player_1
    current_time = time.time()
    if previous_id != player_id:
        update_player_name("p1Name", "p1Team", player_1, player_id)
        previous_player_1 = (player_id, current_time)
    elif previous_id == player_id and (current_time - player_info_update_window) > previous_timestamp:
        add_to_score("p1Score")
        previous_player_1 = (player_id, current_time)

    return "200"


@api.route('/updateplayer2', methods=['POST'])
def update_player2():
    global previous_player_2
    json_data = request.get_json()
    player_id = json_data["id"]

    previous_id, previous_timestamp = previous_player_2
    current_time = time.time()
    if previous_id != player_id:
        update_player_name("p2Name", "p2Team", player_2, player_id)
        previous_player_2 = (player_id, current_time)
    elif previous_id == player_id and (current_time - player_info_update_window) > previous_timestamp:
        add_to_score("p2Score")
        previous_player_2 = (player_id, current_time)

    return "200"


def add_to_score(score_key):
    full_data = read_file(stream_control_file)
    full_data[score_key] = str(int(full_data[score_key]) + 1)
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))


def update_player_name(player_name_key, team_name_key, file_name, player_id):
    full_data = read_file(stream_control_file)
    save_previous_results(full_data)
    player_info = get_player_info_from_id_map(player_id)
    full_data[player_name_key] = player_info[0]
    if len(player_info) > 1:
        # update team name
        full_data[team_name_key] = player_info[1]

    # Reset the scores
    full_data["p1Score"] = "0"
    full_data["p2Score"] = "0"
    write_to_file(file_name, player_name_key, full_data)
    with open(stream_control_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))


def save_previous_results(full_data):
    write_to_file(result1, "p1Score", full_data)
    write_to_file(result2, "p2Score", full_data)
    write_to_file(result_name_1, "p1Name", full_data)
    write_to_file(result_name_2, "p2Name", full_data)
    full_data["resultscore1"] = full_data["p1Score"]
    full_data["resultscore2"] = full_data["p2Score"]
    full_data["resultplayer1"] = full_data["p1Name"]
    full_data["resultplayer2"] = full_data["p2Name"]


def write_to_file(file_name, data_key, json_data):
    file = open(file_name, "w")
    file.write(json_data[data_key])
    file.close()


def get_player_info_from_id_map(player_id):
    id_map = read_file("id_map.txt")
    if str(player_id) in id_map:
        return id_map[str(player_id)].split(":")
    print("No name associated with id: " + str(player_id))
    return [str(player_id), ""]


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


if __name__ == "__main__":
    try:
        print("Now we talk'n, server started ...")
        # Experimental
        auto_score_updater.auto_update_scores()

        api.run(host=hostName, port=serverPort)
    except KeyboardInterrupt:
        pass
