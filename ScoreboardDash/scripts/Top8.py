import json
from io import open

defaultCurrentDataJson = {
    "player1": {
        "name": "",
        "team": "",
        "country": "",
        "score": ""
    },
    "player2": {
        "name": "",
        "team": "",
        "country": "",
        "score": ""
    },
    "nextPlayer1": {
        "name": "",
        "team": "",
        "country": ""
    },
    "nextPlayer2": {
        "name": "",
        "team": "",
        "country": ""
    },
    "currentRound": 1,
    "nextRound": 2,
    "currentRoundName": "Casuals",
    "started": False
}


defaultPlayerData = {
    "r1": {
        "description": "winners 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r2": {
        "description": "winners 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r3": {
        "description": "losers 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r4": {
        "description": "losers 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r5": {
        "description": "losers quarter 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r6": {
        "description": "losers quarter 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r7": {
        "description": "winners semis",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r8": {
        "description": "losers semis",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r9": {
        "description": "losers finals",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": ""
        }
    },
    "r10": {
        "description": "grand finals",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "score2": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "score2": ""
        }
    }
}

player_data_file_name = "../data/top8_players.json"
scoreboard_json_file = "../data/scoreboard.json"

current_next_data = defaultCurrentDataJson.copy()
global_player_data = defaultPlayerData.copy()
rounds = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
global_current_round = 1
next_round_override = -1
winner_round_progression_mapping = {1: "r7:p1", 2: "r7:p2", 3: "r5:p1", 4: "r6:p1", 5: "r8:p1", 6: "r8:p2", 7: "r10:p1", 8: "r9:p1", 9: "r10:p2"}
losers_round_progression_mapping = {1: "r6:p2", 2: "r5:p2", 7: "r9:p2"}
started = False
roundNamesMap = {
    1: "Winners Semis",
    2: "Winners Semis",
    3: "Losers Round 1",
    4: "Losers Round 1",
    5: "Losers Quarters",
    6: "Losers Quarters",
    7: "Winners Finals",
    8: "Losers Semis",
    9: "Losers Finals",
    10: "Grand Finals",
    11: "Grand Finals"
}


def get_all_player_data():
    return read_file(player_data_file_name)


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


def initialize():
    global started
    if started:
        return
    global global_current_round
    global global_player_data
    global_player_data = read_file(player_data_file_name)
    global next_round_override
    if next_round_override > 0:
        global_current_round = next_round_override
        next_round_override = -1

    key = "r" + str(global_current_round)
    p1 = global_player_data[key]["p1"]
    update_current_player_data("player1", p1)
    p2 = global_player_data[key]["p2"]
    update_current_player_data("player2", p2)
    next_round = get_next_round(global_current_round)
    key = "r" + str(next_round)
    n1 = global_player_data[key]["p1"]
    update_next_player_data("nextPlayer1", n1)
    n2 = global_player_data[key]["p2"]
    update_next_player_data("nextPlayer2", n2)
    global current_next_data
    current_next_data["currentRound"] = global_current_round
    current_next_data["nextRound"] = next_round
    global roundNamesMap
    current_next_data["currentRoundName"] = roundNamesMap.get(global_current_round)
    started = True
    current_next_data["started"] = started
    print("Top 8 started!")


def update_current_player_data(player_id, player_data):
    global current_next_data
    current_next_data[player_id]["name"] = player_data["name"]
    current_next_data[player_id]["team"] = player_data["team"]
    current_next_data[player_id]["score"] = player_data["score"]
    current_next_data[player_id]["country"] = player_data["country"]


def update_next_player_data(player_id, player_data):
    global current_next_data
    current_next_data[player_id]["name"] = player_data["name"]
    current_next_data[player_id]["team"] = player_data["team"]
    current_next_data[player_id]["country"] = player_data["country"]


def progress_to_next_round():
    global rounds
    global current_next_data
    if len(rounds) == 0:
        print("No more rounds, please reset top 8 to start over")
        return json.loads(json.dumps(current_next_data, ensure_ascii=False))
    initialize()
    global global_current_round
    result1 = current_next_data["player1"]
    result2 = current_next_data["player2"]
    p1_score_string = result1["score"]
    p2_score_string = result2["score"]
    result1_name = current_next_data["player1"]["name"]
    result2_name = current_next_data["player2"]["name"]
    p1_score = 0
    p2_score = 0
    if len(p1_score_string) > 0:
        p1_score = int(p1_score_string)
    if len(p2_score_string) > 0:
        p2_score = int(p2_score_string)
    if p1_score == p2_score:
        print("Score is tied, cannot proceed to next round!")
        # Can't update the scores, no winner, return current data
        return json.loads(json.dumps(current_next_data, ensure_ascii=False))

    p1_winner = p1_score > p2_score
    global global_player_data
    if global_current_round >= 10:
        return update_final_round(global_player_data, current_next_data, p1_score_string, p2_score_string, global_current_round)

    global winner_round_progression_mapping
    if p1_winner:
        update_winner_player_data(global_player_data, result1, global_current_round)
    else:
        update_winner_player_data(global_player_data, result2, global_current_round)

    global losers_round_progression_mapping
    if losers_round_progression_mapping.get(global_current_round) is not None:
        if p1_winner:
            update_loser_player_data(global_player_data, result2, global_current_round)
        else:
            update_loser_player_data(global_player_data, result1, global_current_round)

    # Update result scores in top 8 data
    key = "r" + str(global_current_round)
    global_player_data[key]["p1"]["score"] = p1_score_string
    global_player_data[key]["p2"]["score"] = p2_score_string

    # Save off top 8 player data to file
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        data_to_write = json.dumps(global_player_data, ensure_ascii=False)
        json_file.write(data_to_write)

    print("Completed round: " + str(global_current_round))
    rounds.remove(global_current_round)

    # Update the current player info in the player data
    global_current_round = get_next_round(global_current_round)
    # Reset any overrides for next round
    global next_round_override
    next_round_override = -1
    key = "r" + str(global_current_round)
    copy_player_data(global_player_data[key]["p1"], current_next_data["player1"])
    copy_player_data(global_player_data[key]["p2"], current_next_data["player2"])
    next_round = get_next_round(global_current_round)
    if next_round <= 10:
        # Stop processing next rounds if on last round
        key = "r" + str(next_round)
        copy_player_data(global_player_data[key]["p1"], current_next_data["nextPlayer1"])
        copy_player_data(global_player_data[key]["p2"], current_next_data["nextPlayer2"])
        current_next_data["nextRound"] = next_round
    else:
        current_next_data["player2"]["name"] = current_next_data["player2"]["name"] + " [L]"
        current_next_data["nextPlayer1"]["name"] = ""
        current_next_data["nextPlayer2"]["name"] = ""
        current_next_data["nextPlayer1"]["team"] = ""
        current_next_data["nextPlayer2"]["team"] = ""
        current_next_data["nextPlayer1"]["country"] = ""
        current_next_data["nextPlayer2"]["country"] = ""

    current_next_data["currentRound"] = global_current_round
    global roundNamesMap
    current_round_name = roundNamesMap.get(global_current_round)
    current_next_data["currentRoundName"] = current_round_name
    update_scoreboard_json(current_next_data, result1_name, result2_name, p1_score_string, p2_score_string, current_round_name)
    return json.loads(json.dumps(current_next_data, ensure_ascii=False))


def update_final_round(global_player_round_data, current_round_data, p1_score, p2_score, current_round):
    global rounds
    if current_round == 10:
        global_player_round_data["r10"]["p1"]["score"] = p1_score
        global_player_round_data["r10"]["p2"]["score"] = p2_score
        if p1_score > p2_score:
            # No more rounds
            rounds = []
        else:
            global global_current_round
            global_current_round = 11
            current_round_data["player1"]["score"] = "0"
            current_round_data["player2"]["score"] = "0"
            current_round_data["player1"]["name"] = current_round_data["player1"]["name"] + " [L]"
            current_round_data["currentRound"] = global_current_round
        print("Completed Round 10")
    else:
        global_player_round_data["r10"]["p1"]["score2"] = p1_score
        global_player_round_data["r10"]["p2"]["score2"] = p2_score
        rounds = []
        print("Completed Round 11")

    # Save off top 8 player data to file
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        data_to_write = json.dumps(global_player_round_data, ensure_ascii=False)
        json_file.write(data_to_write)
    return json.loads(json.dumps(current_round_data, ensure_ascii=False))


def update_scoreboard_json(data, result_name_1, result_name_2, result1, result2, current_round_name):
    scoreboard_data = read_file(scoreboard_json_file)
    scoreboard_data["p1Name"] = data["player1"]["name"]
    scoreboard_data["p1Team"] = data["player1"]["team"]
    scoreboard_data["p1Country"] = data["player1"]["country"]
    scoreboard_data["p1Score"] = data["player1"]["score"]
    scoreboard_data["p2Name"] = data["player2"]["name"]
    scoreboard_data["p2Team"] = data["player2"]["team"]
    scoreboard_data["p2Country"] = data["player2"]["country"]
    scoreboard_data["p2Score"] = data["player2"]["score"]
    scoreboard_data["resultplayer1"] = result_name_1
    scoreboard_data["resultscore1"] = result1
    scoreboard_data["resultplayer2"] = result_name_2
    scoreboard_data["resultscore2"] = result2
    scoreboard_data["round"] = current_round_name
    with open(scoreboard_json_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(scoreboard_data, ensure_ascii=False))


def copy_player_data(source, dest):
    dest["name"] = source["name"]
    dest["team"] = source["team"]
    dest["country"] = source["country"]


def update_winner_player_data(global_player_round_data, player_data, current_round):
    global winner_round_progression_mapping
    next_round_info = winner_round_progression_mapping[current_round].split(":")
    global_player_round_data[next_round_info[0]][next_round_info[1]]["name"] = player_data["name"]
    global_player_round_data[next_round_info[0]][next_round_info[1]]["team"] = player_data["team"]
    global_player_round_data[next_round_info[0]][next_round_info[1]]["score"] = ""
    global_player_round_data[next_round_info[0]][next_round_info[1]]["country"] = player_data["country"]


def update_loser_player_data(global_player_round_data, player_data, current_round):
    global losers_round_progression_mapping
    next_round_info = losers_round_progression_mapping[current_round].split(":")
    global_player_round_data[next_round_info[0]][next_round_info[1]]["name"] = player_data["name"]
    global_player_round_data[next_round_info[0]][next_round_info[1]]["team"] = player_data["team"]
    global_player_round_data[next_round_info[0]][next_round_info[1]]["score"] = ""
    global_player_round_data[next_round_info[0]][next_round_info[1]]["country"] = player_data["country"]


def set_next_round_override(override):
    global rounds
    if override not in rounds:
        print("Trying to set a round that's already finished: " + str(override) + " Ignoring")
        return "500"
    global next_round_override
    print("Next round override set to: " + str(override))
    next_round_override = override
    return "200"


def get_next_round(current_round):
    global next_round_override
    if next_round_override > 0:
        return next_round_override

    global rounds
    for r in rounds:
        if current_round != r:
            return r
    return None


def reset():
    global current_next_data
    current_next_data = defaultCurrentDataJson.copy()
    global global_player_data
    global_player_data = defaultPlayerData.copy()
    global global_current_round
    global_current_round = 1
    global started
    started = False
    global rounds
    rounds = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(defaultPlayerData, ensure_ascii=False))


def update_current_players_info(scoreboard_json):
    global current_next_data
    current_next_data["player1"]["name"] = scoreboard_json["p1Name"]
    current_next_data["player1"]["team"] = scoreboard_json["p1Team"]
    current_next_data["player1"]["score"] = scoreboard_json["p1Score"]
    current_next_data["player1"]["country"] = scoreboard_json["p1Country"]
    current_next_data["player2"]["name"] = scoreboard_json["p2Name"]
    current_next_data["player2"]["team"] = scoreboard_json["p2Team"]
    current_next_data["player2"]["score"] = scoreboard_json["p2Score"]
    current_next_data["player2"]["country"] = scoreboard_json["p2Country"]


def update_next_players_info(scoreboard_json):
    global current_next_data
    current_next_data["nextPlayer1"]["name"] = scoreboard_json["nextplayer1"]
    current_next_data["nextPlayer1"]["team"] = scoreboard_json["nextteam1"]
    current_next_data["nextPlayer2"]["name"] = scoreboard_json["nextplayer2"]
    current_next_data["nextPlayer2"]["team"] = scoreboard_json["nextteam2"]


def update_player_info(round_id, player_id, field, value):
    global global_player_data
    global_player_data[round_id][player_id][field] = value
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(global_player_data, ensure_ascii=False))
