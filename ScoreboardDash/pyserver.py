import json
from io import open
from flask import Flask, send_from_directory, jsonify
from flask import request
from flask_cors import CORS
import time
from scripts import AutoScoreUpdaterSt
from scripts import AutoScoreUpdaterCvs2
from scripts import Top8
from scripts import AutoScoreUpdaterCPS1
from scripts import startgg_client
import argparse
import socket
import os
import webbrowser
import shutil
from datetime import datetime
from scripts import PlayerStats

# Get today's date in YYYY-MM-DD format
today_date = datetime.today().strftime('%Y-%m-%d')

hostname = socket.getfqdn()
server_ip = socket.gethostbyname(hostname)
print("Server IP: " + server_ip)
port = "8080"
server_port = int(port)

server_info = server_ip + ":" + port
config_file = open('../config/serverip.txt', "w")
config_file.write(server_info)
config_file.close()

replay_prefix = "Replay"
replays_folder = "recordings/replays"
saved_replays_folder = "../../clips"
scoreboard_data_file = "../data/scoreboard.json"
commentators_file = "../data/commentators.json"
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
auto_score_updater_st = AutoScoreUpdaterSt
auto_score_updater_cvs2 = AutoScoreUpdaterCvs2
auto_score_updater_cps1 = AutoScoreUpdaterCPS1
top8 = Top8
refresh_client = False
event_name = ""
tournament_info = None
player_stats = PlayerStats


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


full_data = read_file(scoreboard_data_file)


# Serve your webpage files from the same directory
@api.route('/')
def serve_webpage():
    return send_from_directory(os.path.dirname(__file__), 'index.html')


# Serve static files (CSS, JS)
@api.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.dirname(__file__), filename)


@api.route('/registerClientRefresh', methods=['GET'])
def register_client_refresh():
    global refresh_client
    while not refresh_client:
        # Wait and do nothing
        if auto_score_updater_cvs2.has_updated_score():
            break
        elif auto_score_updater_st.has_updated_score():
            break
        elif auto_score_updater_cps1.has_updated_score():
            break
        time.sleep(1)

    refresh_client = False
    return "", 200


@api.route('/getdata', methods=['GET'])
def get_data():
    return json.dumps(read_file(scoreboard_data_file), ensure_ascii=False), 200


@api.route('/getTop8PlayerData', methods=['GET'])
def get_top8_player_data():
    return top8.get_all_player_data(), 200


@api.route('/getTop8CurrentNextData', methods=['GET'])
def get_top8_current_next_data():
    return top8.get_current_next_data(), 200


@api.route('/resetTop8', methods=['POST'])
def reset_top8_data():
    top8.reset()
    return "200"


@api.route('/getCommentators', methods=['GET'])
def get_commentators():
    return json.dumps(read_file(commentators_file), ensure_ascii=False), 200


@api.route('/getNextPlayers', methods=['GET'])
def get_next_players():
    global full_data
    full_data = read_file(scoreboard_data_file)
    current_player_1 = full_data["p1Name"]
    current_player_2 = full_data["p2Name"]
    return startgg_client.get_next_players(current_player_1, current_player_2), 200


@api.route('/setTournamentInfo', methods=['POST'])
def set_tournament_info():
    startgg_client.save_start_gg_info(request.get_json())
    return "200"


@api.route('/fetchStartggTop8Info', methods=['POST'])
def fetch_startgg_tournament_info():
    data = request.get_json()
    player_stats.write_to_file(startgg_client.get_top_8_entrants_for_event(data["tournament"], data["event"]))
    return "200"


@api.route('/addStartggTop8Info', methods=['POST'])
def add_startgg_tournament_info():
    data = request.get_json()
    player_stats.add_to_file(startgg_client.get_top_8_entrants_for_event(data["tournament"], data["event"]))
    return "200"


@api.route('/getPlayerPlacement', methods=['GET'])
def get_player_placement():
    gamer_tag = request.args.get('gamerTag')
    player = request.args.get('player')
    if not gamer_tag or not player:
        return jsonify({}), 200
    placement = player_stats.get_placement(gamer_tag, player)
    if not placement:
        return jsonify({}), 200
    return jsonify(placement), 200


@api.route('/deletePlayerStats', methods=['POST'])
def delete_player_stats():
    player_stats.delete_stats()
    return "200"


@api.route('/addPlayerStat', methods=['POST'])
def add_player_stat():
    data = request.get_json()
    player_stats.add_player_data(data["gamerTag"], data["event"], data["placement"], data["wins"], data["losses"])
    return "200"


@api.route('/getEventsWithStats', methods=['GET'])
def get_events_with_stats():
    return jsonify(player_stats.get_all_events_with_stats()), 200


@api.route('/setEventForStats', methods=['POST'])
def set_event_for_stats():
    data = request.get_json()
    player_stats.set_current_event(data["event"])
    return "200"


@api.route('/getTournamentInfo', methods=['GET'])
def get_tournament_info():
    result = startgg_client.get_start_gg_info()
    if result is None:
        return json.dumps("{}", ensure_ascii=False), 200
    return result, 200


@api.route('/addPlayer1Score', methods=['POST'])
def add_player1_score():
    add_to_score("p1Score")
    top8.update_current_players_info(full_data)
    global refresh_client
    refresh_client = True
    return "200"


@api.route('/addPlayer2Score', methods=['POST'])
def add_player2_score():
    add_to_score("p2Score")
    top8.update_current_players_info(full_data)
    global refresh_client
    refresh_client = True
    return "200"


@api.route('/subPlayer1Score', methods=['POST'])
def sub_player1_score():
    sub_to_score("p1Score")
    top8.update_current_players_info(full_data)
    global refresh_client
    refresh_client = True
    return "200"


@api.route('/subPlayer2Score', methods=['POST'])
def sub_player2_score():
    sub_to_score("p2Score")
    top8.update_current_players_info(full_data)
    global refresh_client
    refresh_client = True
    return "200"


@api.route('/setNextRound', methods=['POST'])
def set_next_round():
    return top8.set_next_round_override(int(request.form['round']))


@api.route('/reverseNames', methods=['POST'])
def reverse_names():
    top8.set_reverse_names()
    return "200"


@api.route('/getNextRoundData', methods=['GET'])
def get_next_round_data():
    next_round_info = top8.progress_to_next_round()
    global full_data
    full_data = read_file(scoreboard_data_file)
    player1 = next_round_info["player1"]
    player2 = next_round_info["player2"]
    full_data["p1Name"] = player1["name"]
    full_data["p2Name"] = player2["name"]
    full_data["p1Team"] = player1["team"]
    full_data["p2Team"] = player2["team"]
    full_data["p1Country"] = player1["country"]
    full_data["p2Country"] = player2["country"]
    full_data["p1Score"] = "0"
    full_data["p2Score"] = "0"
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    return next_round_info, 200


@api.route('/updatealldata', methods=['POST'])
def update_all_data():
    json_data = request.get_json()
    global full_data
    full_data = json_data
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    return "200"


@api.route('/updatecommdata', methods=['POST'])
def update_comm_data():
    json_data = request.get_json()
    global full_data
    full_data["com1"] = json_data.get("com1", "")
    full_data["soc1"] = json_data.get("soc1", "")
    full_data["com2"] = json_data.get("com2", "")
    full_data["soc2"] = json_data.get("soc2", "")
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    return "200"


@api.route('/updatedatanoscores', methods=['POST'])
def update_data_no_scores():
    global full_data
    json_data = request.get_json()
    full_data["p1Name"] = json_data.get("p1Name", "")
    full_data["p2Name"] = json_data.get("p2Name", "")
    full_data["p1Team"] = json_data.get("p1Team", "")
    full_data["p2Team"] = json_data.get("p2Team", "")
    full_data["resultscore1"] = json_data.get("resultscore1", "")
    full_data["resultscore2"] = json_data.get("resultscore2", "")
    full_data["resultplayer1"] = json_data.get("resultplayer1", "")
    full_data["resultplayer2"] = json_data.get("resultplayer2", "")
    full_data["p1Country"] = json_data.get("p1Country", "")
    full_data["p2Country"] = json_data.get("p2Country", "")
    full_data["round"] = json_data.get("round", "")
    full_data["nextplayer1"] = json_data.get("nextplayer1", "")
    full_data["nextplayer2"] = json_data.get("nextplayer2", "")
    full_data["nextteam1"] = json_data.get("nextteam1", "")
    full_data["nextteam2"] = json_data.get("nextteam2", "")
    full_data["nextcountry1"] = json_data.get("nextcountry1", "")
    full_data["nextcountry2"] = json_data.get("nextcountry2", "")
    full_data["maxScore"] = json_data.get("maxScore", "99")
    full_data["timestamp"] = json_data.get("timestamp")
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    return "200"


@api.route('/updateP1score', methods=['POST'])
def update_p1_score():
    json_data = request.get_json()

    full_data["p1Score"] = json_data.get("p1Score", "0")
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateP2score', methods=['POST'])
def update_p2_score():
    json_data = request.get_json()

    full_data["p2Score"] = json_data.get("p2Score", "0")
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateCurrentScore', methods=['POST'])
def update_current_scores():
    json_data = request.get_json()
    full_data["p1Score"] = json_data.get("p1Score", "0")
    full_data["p2Score"] = json_data.get("p2Score", "0")
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateCurrentPlayers', methods=['POST'])
def update_current_players():
    json_data = request.get_json()
    full_data["p1Name"] = json_data["p1Name"]
    full_data["p2Name"] = json_data["p2Name"]
    full_data["p1Team"] = json_data["p1Team"]
    full_data["p2Team"] = json_data["p2Team"]
    full_data["p1Country"] = json_data["p1Country"]
    full_data["p2Country"] = json_data["p2Country"]
    full_data["round"] = json_data["round"]
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateResults', methods=['POST'])
def update_results():
    json_data = request.get_json()
    full_data["resultscore1"] = json_data["resultscore1"]
    full_data["resultscore2"] = json_data["resultscore2"]
    full_data["resultplayer1"] = json_data["resultplayer1"]
    full_data["resultplayer2"] = json_data["resultplayer2"]
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    return "200"


@api.route('/updateNextPlayers', methods=['POST'])
def update_next_players():
    json_data = request.get_json()
    full_data["nextplayer1"] = json_data["nextplayer1"]
    full_data["nextplayer2"] = json_data["nextplayer2"]
    full_data["nextteam1"] = json_data["nextteam1"]
    full_data["nextteam2"] = json_data["nextteam2"]
    full_data["nextcountry1"] = json_data["nextcountry1"]
    full_data["nextcountry2"] = json_data["nextcountry2"]
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))
    top8.update_next_players_info(full_data)
    return "200"


@api.route('/updateTop8playerInfo', methods=['POST'])
def update_top8_player_info():
    round_id = request.form['round']
    player_id = request.form['player']
    field_id = request.form['field']
    value = request.form['value']
    top8.update_player_info(round_id, player_id, field_id, value)
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
    global refresh_client
    refresh_client = True
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
    global refresh_client
    refresh_client = True
    return "200"


@api.route('/getreplayvideos', methods=['GET'])
def get_replay_folder():
    videos = [filename for filename in os.listdir(replays_folder) if filename.startswith(replay_prefix)]
    return jsonify(videos), 200


@api.route('/deleteclips', methods=['POST'])
def delete_clips():
    for filename in os.listdir(replays_folder):
        file_path = os.path.join(replays_folder, filename)
        try:
            if filename.startswith(replay_prefix) and os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
    return "200"


@api.route('/saveclips', methods=['POST'])
def save_clips():
    # Check if the directory exists, if not, create it
    destination = saved_replays_folder + "/" + today_date
    if not os.path.exists(destination):
        os.makedirs(destination)
        print(f"Directory '{destination}' created successfully.")

    move_files(replays_folder, destination)
    return "200"


def move_files(src_dir, dst_dir):
    # Get a list of all files in the source directory
    files = os.listdir(src_dir)

    # Iterate over each file and move it to the destination directory
    for file in files:
        if file.startswith(replay_prefix):
            src_file_path = os.path.join(src_dir, file)
            dst_file_path = os.path.join(dst_dir, file)
            shutil.move(src_file_path, dst_file_path)


def add_to_score(score_key):
    full_data[score_key] = str(int(full_data[score_key]) + 1)
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))


def sub_to_score(score_key):
    full_data[score_key] = str(max(int(full_data[score_key]) - 1, 0))
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))


def update_player_name(player_name_key, team_name_key, file_name, player_id):
    save_previous_results()
    player_info = get_player_info_from_id_map(player_id)
    full_data[player_name_key] = player_info[0]
    if len(player_info) > 1:
        # update team name
        full_data[team_name_key] = player_info[1]

    # Reset the scores
    full_data["p1Score"] = "0"
    full_data["p2Score"] = "0"
    write_to_file(file_name, player_name_key, full_data)
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data, ensure_ascii=False))


def save_previous_results():
    write_to_file(result1, "p1Score", full_data)
    write_to_file(result2, "p2Score", full_data)
    write_to_file(result_name_1, "p1Name", full_data)
    write_to_file(result_name_2, "p2Name", full_data)
    full_data["resultscore1"] = full_data["p1Score"]
    full_data["resultscore2"] = full_data["p2Score"]
    full_data["resultplayer1"] = full_data["p1Name"]
    full_data["resultplayer2"] = full_data["p2Name"]
    with open(scoreboard_data_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(full_data))


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


def open_browser(url, chrome_path):
    webbrowser.get(chrome_path).open(url)


if __name__ == "__main__":
    try:
        print("Now we talk'n, server started ...")
        parser = argparse.ArgumentParser(description = 'Scoreboard server')
        parser.add_argument("-a", "--AutoScore", action='store_true', dest='AutoScore', help="Enable auto scoring")
        parser.add_argument("-st", "--St", action='store_true', dest='St', help="Enables ST")
        parser.add_argument("-cvs2", "--Cvs2", action='store_true', dest='Cvs2', help="Enables CVS2")
        parser.add_argument("-cps1", "--CPS1", action='store_true', dest='CPS1', help="Enables CPS1")

        parser.add_argument("-w", "--windows", action='store_true', dest='windows', help="Open browser for Windows")
        parser.add_argument("-m", "--mac", action='store_true', dest='mac', help="Open browser for Mac")
        parser.add_argument("-l", "--linux", action='store_true', dest='linux', help="Open browser for Linux")

        # Read arguments from command line
        args = parser.parse_args()
        if args.AutoScore:
            # Experimental
            if args.St:
                auto_score_updater_st.auto_update_scores()
            elif args.Cvs2:
                auto_score_updater_cvs2.auto_update_scores()
            elif args.CPS1:
                auto_score_updater_cps1.auto_update_scores()
            else:
                print("Auto scoring enabled but no game defined. Please choose with options [-st, -cvs2]")

        if args.windows:
            open_browser("http://" + server_info, 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s')
        elif args.mac:
            open_browser("http://" + server_info, 'open -a /Applications/Google\ Chrome.app %s')
        elif args.linux:
            open_browser("http://" + server_info, '/usr/bin/google-chrome %s')

        api.run(host=server_ip, port=server_port)
    except KeyboardInterrupt:
        pass
