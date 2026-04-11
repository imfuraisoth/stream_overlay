import json
import threading
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
import copy
from datetime import datetime
from scripts import PlayerStats
from scripts import TTLCache
from scripts import ReplayUtils
from scripts import CharacterImageLoader
from scripts import Countdown
from scripts.FileUtils import FileUtils
from playerinfo import PlayerStatsDB
from scripts import  MessageDataStore


# Get today's date in YYYY-MM-DD format
today_date = datetime.today().strftime('%Y-%m-%d')

replay_prefix = "Replay_"
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
players_list_map = {}
players_db = PlayerStatsDB
countdown = Countdown
message_data_store = MessageDataStore

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
event_name = ""
tournament_info = None
player_stats = PlayerStats
replay_utils = ReplayUtils
character_image_loader = CharacterImageLoader
previous_matches_cache = TTLCache.SimpleTTLCache(1800)  # 30 minutes TTL

full_data_lock = threading.Lock()
full_data = FileUtils.read_file(scoreboard_data_file)


# Serve your webpage files from the same directory
@api.route('/')
def serve_webpage():
    return send_from_directory(os.path.dirname(__file__), 'index.html')


# Serve static files (CSS, JS)
@api.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.dirname(__file__), filename)


@api.route('/getdata', methods=['GET'])
def get_data():
    return json.dumps(FileUtils.read_file(scoreboard_data_file), ensure_ascii=False), 200


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
    return json.dumps(FileUtils.read_file(commentators_file), ensure_ascii=False), 200


@api.route('/addCommentator', methods=['POST'])
def add_commentator():
    commentator_data = request.get_json()
    commentators = FileUtils.read_file(commentators_file)
    commentators[commentator_data.get("name")] = commentator_data
    FileUtils.write_file(commentators_file, commentators)
    return "200"


@api.route('/deleteCommentators', methods=['POST'])
def delete_commentator():
    commentator_names = request.get_json()
    commentators = FileUtils.read_file(commentators_file)
    for name in commentator_names:
        del commentators[name]
    FileUtils.write_file(commentators_file, commentators)
    return "200"


@api.route('/getNextPlayers', methods=['GET'])
def get_next_players():
    global full_data
    full_data = FileUtils.read_file(scoreboard_data_file)
    current_player_1 = full_data["p1Name"]
    current_player_2 = full_data["p2Name"]
    return startgg_client.get_next_players(current_player_1, current_player_2, previous_matches_cache), 200


@api.route('/reportWinnerToStartgg', methods=['POST'])
def report_winner():
    winner_data = request.get_json()
    set_id = winner_data.get("setId", 0)
    winner_id = winner_data.get("winnerId", 0)
    loser_id = winner_data.get("loserId", 0)
    entrant_1_score = winner_data.get("entrant1Score", 0)
    entrant_2_score = winner_data.get("entrant2Score", 0)
    if set_id != 0 and winner_id != 0 and loser_id != 0:
        return str(startgg_client.report_winner(set_id, winner_id, loser_id, entrant_1_score, entrant_2_score)), 200
    return "False", 200


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


@api.route('/getAllPlayersForTournament', methods=['GET'])
def get_all_players_for_tournament():
    global players_list_map
    from_cache = parse_bool(request.args.get("fromCache"), False)
    if from_cache:
        # Return cache value
        return jsonify(players_list_map), 200
    tournament = request.args.get("tournament")
    event = request.args.get("event")
    result = startgg_client.get_all_players_from_tournament(tournament, event)
    if result is None:
        return json.dumps("[]", ensure_ascii=False), 200
    players_list_map[event] = [player.__dict__ for player in result]
    return jsonify(players_list_map), 200


@api.route('/getAllPlayersForEvent', methods=['GET'])
def get_all_players_for_event():
    global players_list_map
    event = request.args.get("event")
    return jsonify(players_list_map.get(event)), 200


@api.route('/getAllEvents', methods=['GET'])
def get_all_events():
    global players_list_map
    return jsonify(list(players_list_map.keys())), 200


@api.route('/getAllGameImageDir', methods=['GET'])
def get_all_game_image_dir():
    global character_image_loader, full_data
    current_game = full_data.get("current_game")
    if not current_game:
        current_game = ""
    result = {
        "current_game": current_game,
        "game_list": character_image_loader.list_games()
    }
    return jsonify(result), 200


@api.route('/getCharacterImages', methods=['GET'])
def get_character_images():
    global character_image_loader
    game = request.args.get("game")
    return jsonify(character_image_loader.get_character_images(game)), 200


@api.route('/savePlayerCharacterData', methods=['POST'])
def save_player_character_data():
    global players_db
    data = request.get_json()
    players_db.save_player_characters(data)
    return "200"


@api.route('/getPlayerCharacterData', methods=['GET'])
def get_player_character_data():
    global players_db
    player = request.args.get("player")
    game = request.args.get("game")
    if not player:
        return jsonify(players_db.get_last_access_player_info()), 200
    return jsonify(players_db.get_player_characters(player, game)), 200


@api.route('/deletePlayerCharacterData', methods=['POST'])
def delete_player_character_data():
    global players_db
    data = request.get_json()
    player = data["player"]
    players_db.remove_player(player)
    return "200"


@api.route('/clearPlayersList', methods=['POST'])
def clear_players_list_map():
    global players_list_map
    players_list_map = {}
    return "200"


@api.route('/addPlayer1Score', methods=['POST'])
def add_player1_score():
    add_to_score("p1Score")
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/addPlayer2Score', methods=['POST'])
def add_player2_score():
    add_to_score("p2Score")
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/subPlayer1Score', methods=['POST'])
def sub_player1_score():
    sub_to_score("p1Score")
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/subPlayer2Score', methods=['POST'])
def sub_player2_score():
    sub_to_score("p2Score")
    top8.update_current_players_info(full_data)
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
    with full_data_lock:
        temp = FileUtils.read_file(scoreboard_data_file)
        player1 = next_round_info["player1"]
        player2 = next_round_info["player2"]
        temp["p1Name"] = player1["name"]
        temp["p2Name"] = player2["name"]
        temp["p1Team"] = player1["team"]
        temp["p2Team"] = player2["team"]
        temp["p1Country"] = player1["country"]
        temp["p2Country"] = player2["country"]
        temp["p1Score"] = "0"
        temp["p2Score"] = "0"
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    return next_round_info, 200


@api.route('/updatealldata', methods=['POST'])
def update_all_data():
    json_data = request.get_json()
    if json_data.get("current_game") is None:
        print(json.dumps(json_data))
        print("GOT CORRUPT DATA!!!!")
        return "500"
    global full_data
    with full_data_lock:
        full_data = json_data
    add_result_players_to_cache(json_data)
    FileUtils.write_file(scoreboard_data_file, full_data)
    return "200"


@api.route('/updatecommdata', methods=['POST'])
def update_comm_data():
    json_data = request.get_json()
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        if "com1" in json_data:
            temp["com1"] = json_data.get("com1", "")
        if "com2" in json_data:
            temp["com2"] = json_data.get("com2", "")
        if "soc1" in json_data:
            temp["soc1"] = json_data.get("soc1", "")
        if "soc2" in json_data:
            temp["soc2"] = json_data.get("soc2", "")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    return "200"


@api.route('/updatedatanoscores', methods=['POST'])
def update_data_no_scores():
    global full_data
    json_data = request.get_json()
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["current_game"] = json_data.get("current_game")
        temp["p1Name"] = json_data.get("p1Name", "")
        temp["p2Name"] = json_data.get("p2Name", "")
        temp["p1Team"] = json_data.get("p1Team", "")
        temp["p2Team"] = json_data.get("p2Team", "")
        temp["resultscore1"] = json_data.get("resultscore1", "")
        temp["resultscore2"] = json_data.get("resultscore2", "")
        temp["resultplayer1"] = json_data.get("resultplayer1", "")
        temp["resultplayer2"] = json_data.get("resultplayer2", "")
        temp["p1Country"] = json_data.get("p1Country", "")
        temp["p2Country"] = json_data.get("p2Country", "")
        temp["round"] = json_data.get("round", "")
        temp["nextplayer1"] = json_data.get("nextplayer1", "")
        temp["nextplayer2"] = json_data.get("nextplayer2", "")
        temp["nextteam1"] = json_data.get("nextteam1", "")
        temp["nextteam2"] = json_data.get("nextteam2", "")
        temp["nextcountry1"] = json_data.get("nextcountry1", "")
        temp["nextcountry2"] = json_data.get("nextcountry2", "")
        temp["maxScore"] = json_data.get("maxScore", "99")
        temp["timestamp"] = json_data.get("timestamp")
        temp["nextRound"] = json_data.get("nextRound", temp["round"])
        temp["p1Seed"] = json_data.get("p1Seed", "")
        temp["p2Seed"] = json_data.get("p2Seed", "")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    return "200"


@api.route('/updateP1score', methods=['POST'])
def update_p1_score():
    json_data = request.get_json()
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["p1Score"] = json_data.get("p1Score", "0")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateP2score', methods=['POST'])
def update_p2_score():
    json_data = request.get_json()
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["p2Score"] = json_data.get("p2Score", "0")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateCurrentScore', methods=['POST'])
def update_current_scores():
    json_data = request.get_json()
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["p1Score"] = json_data.get("p1Score", "0")
        temp["p2Score"] = json_data.get("p2Score", "0")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateCurrentPlayers', methods=['POST'])
def update_current_players():
    global full_data
    json_data = request.get_json()
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["p1Name"] = json_data["p1Name"]
        temp["p2Name"] = json_data["p2Name"]
        temp["p1Team"] = json_data["p1Team"]
        temp["p2Team"] = json_data["p2Team"]
        temp["p1Country"] = json_data["p1Country"]
        temp["p2Country"] = json_data["p2Country"]
        temp["round"] = json_data["round"]
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    top8.update_current_players_info(full_data)
    return "200"


@api.route('/updateResults', methods=['POST'])
def update_results():
    global full_data
    json_data = request.get_json()
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["resultscore1"] = json_data["resultscore1"]
        temp["resultscore2"] = json_data["resultscore2"]
        temp["resultplayer1"] = json_data["resultplayer1"]
        temp["resultplayer2"] = json_data["resultplayer2"]
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
    return "200"


@api.route('/updateNextPlayers', methods=['POST'])
def update_next_players():
    global full_data
    json_data = request.get_json()
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["nextplayer1"] = json_data["nextplayer1"]
        temp["nextplayer2"] = json_data["nextplayer2"]
        temp["nextteam1"] = json_data["nextteam1"]
        temp["nextteam2"] = json_data["nextteam2"]
        temp["nextcountry1"] = json_data["nextcountry1"]
        temp["nextcountry2"] = json_data["nextcountry2"]
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
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


@api.route('/getreplayvideos', methods=['GET'])
def get_replay_videos():
    videos = replay_utils.get_replay_videos(replay_prefix, replays_folder)
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


@api.route('/loadLeagueData', methods=['POST'])
def fetch_league_data():
    global player_stats
    directory = request.form['path']
    if not directory:
        print("Invalid directory")
        return "200"
    player_stats.update_league_stats(directory)
    return "200"


@api.route('/clearLeagueData', methods=['POST'])
def clear_league_data():
    global player_stats
    player_stats.clear_stats()
    return "200"


@api.route('/getMatchData', methods=['GET'])
def get_match_data():
    global player_stats
    p1_name = request.args.get('p1')
    p2_name = request.args.get('p2')
    return jsonify(player_stats.get_match_info(p1_name, p2_name)), 200


@api.route('/getLeagueDirs', methods=['GET'])
def get_league_dirs():
    return jsonify(player_stats.list_league_stats_directories()), 200


@api.route('/setCountdownInfo', methods=['POST'])
def set_countdown_info():
    json_data = request.get_json()
    countdown.set_game(json_data.get("game_name", ""), json_data.get("message", ""), json_data.get("timer", 0))
    return "200"


@api.route('/getGamesForCountdown', methods=['GET'])
def get_games_for_countdown():
    return countdown.get_games()


@api.route('/getCountdownInfo', methods=['GET'])
def get_countdown_info():
    first_load_str = request.args.get('firstLoad', 'false')
    first_load = first_load_str.lower() == 'true'
    return countdown.get_as_json(first_load)


@api.route('/getCustomMessages', methods=['GET'])
def get_custom_messages():
    return jsonify(message_data_store.get_message_data()), 200


@api.route('/setCustomMessages', methods=['POST'])
def set_custom_messages():
    json_data = request.get_json()
    message_data_store.save_message_data(json_data)
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
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp[score_key] = str(int(temp[score_key]) + 1)
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)


def sub_to_score(score_key):
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp[score_key] = str(max(int(temp[score_key]) - 1, 0))
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)


def update_player_name(player_name_key, team_name_key, file_name, player_id):
    save_previous_results()
    player_info = get_player_info_from_id_map(player_id)
    global full_data
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp[player_name_key] = player_info[0]
        if len(player_info) > 1:
            # update team name
            temp[team_name_key] = player_info[1]

        # Reset the scores
        temp["p1Score"] = "0"
        temp["p2Score"] = "0"
        full_data = temp
    write_to_file(file_name, player_name_key, full_data)
    FileUtils.write_file(scoreboard_data_file, full_data)


def save_previous_results():
    global full_data
    with full_data_lock:
        write_to_file(result1, "p1Score", full_data)
        write_to_file(result2, "p2Score", full_data)
        write_to_file(result_name_1, "p1Name", full_data)
        write_to_file(result_name_2, "p2Name", full_data)
        temp = copy.deepcopy(full_data)
        temp["resultscore1"] = temp["p1Score"]
        temp["resultscore2"] = temp["p2Score"]
        temp["resultplayer1"] = temp["p1Name"]
        temp["resultplayer2"] = temp["p2Name"]
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)


def write_to_file(file_name, data_key, json_data):
    file = open(file_name, "w", encoding="utf-8")
    file.write(json_data[data_key])
    file.close()


def get_player_info_from_id_map(player_id):
    id_map = FileUtils.read_file("id_map.txt")
    if str(player_id) in id_map:
        return id_map[str(player_id)].split(":")
    print("No name associated with id: " + str(player_id))
    return [str(player_id), ""]


def open_browser(url, chrome_path):
    webbrowser.get(chrome_path).open(url)


def add_result_players_to_cache(json_data):
    global previous_matches_cache
    result_player_1 = json_data.get("resultplayer1", "")
    result_player_2 = json_data.get("resultplayer2", "")
    if all(s.strip() for s in [result_player_1, result_player_2]):
        previous_matches_cache.set(result_player_1, result_player_2)
        previous_matches_cache.set(result_player_2, result_player_1)


def parse_bool(value, default=None):
    if value is None:
        return default
    value = value.strip().lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default   # fallback for unexpected strings


def get_server_info():
    ip = "localhost"
    port = "8080"
    port_num = int(port)
    if args.remote_server:
        hostname = socket.getfqdn()
        ip = socket.gethostbyname(hostname)
    info = ip + ":" + port
    config_file = open('../config/serverip.txt', "w")
    config_file.write(info)
    config_file.close()

    print("Server IP: " + info)
    return ip, port_num, info


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

        parser.add_argument("-r", "--remote", action='store_true', dest='remote_server', help="Uses actual IP instead of localhost")

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

        server_ip, server_port, server_info = get_server_info()

        if args.windows:
            open_browser("http://" + server_info, 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s')
        elif args.mac:
            open_browser("http://" + server_info, 'open -a /Applications/Google\ Chrome.app %s')
        elif args.linux:
            open_browser("http://" + server_info, '/usr/bin/google-chrome %s')

        players_db.init_db()
        api.run(host=server_ip, port=server_port)
    except KeyboardInterrupt:
        pass
