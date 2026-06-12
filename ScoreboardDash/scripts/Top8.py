import json
import threading
from io import open
import copy
from scripts.FileUtils import FileUtils
import os

defaultCurrentDataJson = {
    "player1": {
        "name": "",
        "team": "",
        "country": "",
        "score": "",
        "bracket": ""
    },
    "player2": {
        "name": "",
        "team": "",
        "country": "",
        "score": "",
        "bracket": ""
    },
    "nextPlayer1": {
        "name": "",
        "team": "",
        "country": "",
        "bracket": ""
    },
    "nextPlayer2": {
        "name": "",
        "team": "",
        "country": "",
        "bracket": ""
    },
    "currentRound": 1,
    "nextRound": 2,
    "currentRoundName": "Casuals",
    "started": False,
    "reverseNames": False,
    "nextRoundOverride": False,
    "rounds": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
}

defaultPlayerData = {
    "r1": {
        "description": "winners 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        }
    },
    "r2": {
        "description": "winners 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        }
    },
    "r3": {
        "description": "losers 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        }
    },
    "r4": {
        "description": "losers 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "US",
            "score": "",
            "bracket": ""
        }
    },
    "r5": {
        "description": "winners semis",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        }
    },
    "r6": {
        "description": "losers quarter 1",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        }
    },
    "r7": {
        "description": "losers quarter 2",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        }
    },
    "r8": {
        "description": "losers semis",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        }
    },
    "r9": {
        "description": "losers finals",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "bracket": ""
        }
    },
    "r10": {
        "description": "grand finals",
        "p1": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "score2": "",
            "bracket": ""
        },
        "p2": {
            "name": "",
            "team": "",
            "country": "",
            "score": "",
            "score2": "",
            "bracket": ""
        }
    }
}

_base = os.path.dirname(os.path.abspath(__file__))
player_data_file_name = os.path.join(_base, "../../data/top8_players.json")
scoreboard_json_file = os.path.join(_base, "../../data/scoreboard.json")
current_next_data_file = os.path.join(_base, "../../data/current_next.json")
winner_round_progression_mapping = {1: "r5:p1", 2: "r5:p2", 3: "r6:p1", 4: "r7:p1", 5: "r10:p1", 6: "r8:p1", 7: "r8:p2", 8: "r9:p1", 9: "r10:p2"}
losers_round_progression_mapping = {1: "r7:p2", 2: "r6:p2", 5: "r9:p2"}
roundNamesMap = {
    1: "Winners Semis",
    2: "Winners Semis",
    3: "Losers Round 1",
    4: "Losers Round 1",
    5: "Winners Finals",
    6: "Losers Quarters",
    7: "Losers Quarters",
    8: "Losers Semis",
    9: "Losers Finals",
    10: "Grand Finals",
    11: "Grand Finals"
}


def get_all_player_data():
    return read_file(player_data_file_name)


def read_file(file_name):
    with open(file_name, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


if os.path.exists(current_next_data_file):
    current_next_data = read_file(current_next_data_file)
else:
    current_next_data = copy.deepcopy(defaultCurrentDataJson)
    FileUtils.write_file(current_next_data_file, current_next_data)
current_next_data["started"] = False
if os.path.exists(player_data_file_name):
    global_player_data = read_file(player_data_file_name)
else:
    global_player_data = copy.deepcopy(defaultPlayerData)
    FileUtils.write_file(player_data_file_name, global_player_data)
_undo_snapshot = None
_restoring = False

top8_lock = threading.Lock()


def initialize(skip_scoreboard_update=False):
    global global_player_data
    global current_next_data
    if current_next_data["started"]:
        return

    global_player_data = read_file(player_data_file_name)
    current_round = current_next_data["currentRound"]
    if current_next_data["nextRoundOverride"]:
        current_round = current_next_data["nextRound"]
        current_next_data["nextRoundOverride"] = False

    key = "r" + str(current_round)
    p1 = global_player_data[key]["p1"]
    update_current_player_data("player1", p1)
    p2 = global_player_data[key]["p2"]
    update_current_player_data("player2", p2)
    next_round = get_next_round(current_round)
    key = "r" + str(next_round)
    n1 = global_player_data[key]["p1"]
    update_next_player_data("nextPlayer1", n1)
    n2 = global_player_data[key]["p2"]
    update_next_player_data("nextPlayer2", n2)
    current_next_data["currentRound"] = current_round
    current_next_data["nextRound"] = next_round
    global roundNamesMap
    current_next_data["currentRoundName"] = roundNamesMap.get(current_round)
    started = True
    current_next_data["started"] = started
    if not skip_scoreboard_update:
        update_scoreboard_json(current_next_data, "", "", "", "", current_next_data["currentRoundName"], current_round, "", "")
    FileUtils.write_file(current_next_data_file, current_next_data)
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


_restoring = False


def progress_to_next_round():
    global current_next_data, _restoring
    with top8_lock:
        if len(current_next_data["rounds"]) == 0:
            print("No more rounds, please reset top 8 to start over")
            return json.loads(json.dumps(current_next_data, ensure_ascii=False))
        initialize(skip_scoreboard_update=_restoring)
        _restoring = False
        snapshot_before_next_round()

        result1 = current_next_data["player1"]
        result2 = current_next_data["player2"]
        print(f"[progress_to_next_round] currentRound={current_next_data['currentRound']} p1={result1['name']} p2={result2['name']} p1score={result1['score']} p2score={result2['score']}")
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
        current_round = current_next_data["currentRound"]
        if current_round >= 10:
            return update_final_round(global_player_data, current_next_data, p1_score_string, p2_score_string, current_round)

        if p1_winner:
            update_winner_player_data(global_player_data, result1, current_round)
        else:
            update_winner_player_data(global_player_data, result2, current_round)

        global losers_round_progression_mapping
        if losers_round_progression_mapping.get(current_round) is not None:
            if p1_winner:
                update_loser_player_data(global_player_data, result2, current_round)
            else:
                update_loser_player_data(global_player_data, result1, current_round)

        # Update result scores in top 8 data
        key = "r" + str(current_round)
        if current_next_data["reverseNames"]:
            global_player_data[key]["p1"]["score"] = p2_score_string
            global_player_data[key]["p2"]["score"] = p1_score_string
        else:
            global_player_data[key]["p1"]["score"] = p1_score_string
            global_player_data[key]["p2"]["score"] = p2_score_string

        # Save off top 8 player data to file
        FileUtils.write_file(player_data_file_name, global_player_data)

        print("Completed round: " + str(current_round))
        current_next_data["rounds"].remove(current_round)

        # Update the current player info in the player data
        current_round = get_next_round(current_round)
        if current_next_data["nextRoundOverride"]:
            current_round = current_next_data["nextRound"]
            key = "r" + str(current_round)
            copy_player_data(global_player_data[key]["p1"], current_next_data["nextPlayer1"])
            copy_player_data(global_player_data[key]["p2"], current_next_data["nextPlayer2"])
            current_next_data["nextRoundOverride"] = False

        # Reset any overrides for next round
        copy_player_data(current_next_data["nextPlayer1"], current_next_data["player1"])
        copy_player_data(current_next_data["nextPlayer2"], current_next_data["player2"])
        # New match starts 0-0 in the bracket state too -- otherwise the
        # previous match's scores linger here and a second Next Round
        # click would advance a bogus "winner" before any score is set
        current_next_data["player1"]["score"] = "0"
        current_next_data["player2"]["score"] = "0"
        next_round = get_next_round(current_round)
        if next_round is not None and next_round <= 10:
            # Stop processing next rounds if on last round
            key = "r" + str(next_round)
            copy_player_data(global_player_data[key]["p1"], current_next_data["nextPlayer1"])
            copy_player_data(global_player_data[key]["p2"], current_next_data["nextPlayer2"])
            current_next_data["nextRound"] = next_round
        else:
            current_next_data["player2"]["name"] = current_next_data["player2"]["name"]
            current_next_data["player2"]["bracket"] = "L"
            if not current_next_data["player1"]["bracket"]:
                current_next_data["player1"]["bracket"] = "W"
            current_next_data["nextPlayer1"]["name"] = ""
            current_next_data["nextPlayer2"]["name"] = ""
            current_next_data["nextPlayer1"]["team"] = ""
            current_next_data["nextPlayer2"]["team"] = ""
            current_next_data["nextPlayer1"]["country"] = ""
            current_next_data["nextPlayer2"]["country"] = ""

        add_placeholder_names(next_round)
        current_next_data["currentRound"] = current_round
        global roundNamesMap
        current_round_name = roundNamesMap.get(current_round)
        current_next_data["currentRoundName"] = current_round_name
        update_scoreboard_json(current_next_data, result1_name, result2_name, p1_score_string, p2_score_string, current_round_name, current_round, current_next_data["player1"]["bracket"], current_next_data["player2"]["bracket"])
        current_next_data["reverseNames"] = False
        FileUtils.write_file(current_next_data_file, current_next_data)
        return json.loads(json.dumps(current_next_data, ensure_ascii=False))


def add_placeholder_names(next_round):
    global current_next_data
    if next_round == 8:
        if len(current_next_data["nextPlayer1"]["name"]) == 0:
            current_next_data["nextPlayer1"]["name"] = "Winner"
        else:
            current_next_data["nextPlayer2"]["name"] = "Winner"
        current_next_data["nextRound"] = 8
        current_next_data["nextRoundOverride"] = True
    elif next_round == 9:
        current_next_data["nextPlayer1"]["name"] = "Winner"
        current_next_data["nextRound"] = 9
        current_next_data["nextRoundOverride"] = True
    elif next_round == 10:
        current_next_data["nextPlayer2"]["name"] = "Winner"
        current_next_data["nextRound"] = 10
        current_next_data["nextRoundOverride"] = True


def update_final_round(global_player_round_data, current_round_data, p1_score, p2_score, current_round):
    global current_next_data
    reverse_names = current_round_data["reverseNames"]
    p1_name = current_round_data["player1"]["name"]
    p2_name = current_round_data["player2"]["name"]
    if current_round == 10:
        if reverse_names:
            global_player_round_data["r10"]["p1"]["score"] = p2_score
            global_player_round_data["r10"]["p2"]["score"] = p1_score
        else:
            global_player_round_data["r10"]["p1"]["score"] = p1_score
            global_player_round_data["r10"]["p2"]["score"] = p2_score
        if (not reverse_names and p1_score > p2_score) or (reverse_names and p2_score > p1_score):
            # No more rounds
            current_next_data["rounds"] = []
            current_next_data["started"] = False
        else:
            current_next_data["currentRound"] = 11
            current_round_data["player1"]["score"] = "0"
            current_round_data["player2"]["score"] = "0"
            if reverse_names:
                current_round_data["player2"]["name"] = p2_name
                current_round_data["player2"]["bracket"] = "L"
                if not current_next_data["player1"]["bracket"]:
                    current_round_data["player1"]["bracket"] = "W"
            else:
                current_round_data["player1"]["name"] = p1_name
                current_round_data["player1"]["bracket"] = "L"
                if not current_next_data["player2"]["bracket"]:
                    current_round_data["player2"]["bracket"] = "W"
        print("Completed Round 10")
    else:
        if reverse_names:
            global_player_round_data["r10"]["p1"]["score2"] = p2_score
            global_player_round_data["r10"]["p2"]["score2"] = p1_score
        else:
            global_player_round_data["r10"]["p1"]["score2"] = p1_score
            global_player_round_data["r10"]["p2"]["score2"] = p2_score
        current_next_data["rounds"] = []
        current_next_data["started"] = False
        print("Completed Round 11")

    # Save off top 8 player data to file
    global roundNamesMap
    current_round_name = roundNamesMap.get(current_round)
    current_next_data["currentRoundName"] = current_round_name
    update_scoreboard_json(current_next_data, p1_name, p2_name, str(p1_score), str(p2_score), current_round_name, current_round, current_round_data["player1"]["bracket"], current_round_data["player2"]["bracket"])
    FileUtils.write_file(player_data_file_name, global_player_round_data)
    FileUtils.write_file(current_next_data_file, current_next_data)
    return json.loads(json.dumps(current_round_data, ensure_ascii=False))


def update_scoreboard_json(data, result_name_1, result_name_2, result1, result2, current_round_name, current_round, current_p1_bracket, current_p2_bracket):    
    scoreboard_data = read_file(scoreboard_json_file)
    scoreboard_data["p1Name"] = data["player1"]["name"]
    scoreboard_data["p1Team"] = data["player1"]["team"]
    scoreboard_data["p1Country"] = data["player1"]["country"]
    scoreboard_data["p1Score"] = "0"
    scoreboard_data["p2Name"] = data["player2"]["name"]
    scoreboard_data["p2Team"] = data["player2"]["team"]
    scoreboard_data["p2Country"] = data["player2"]["country"]
    scoreboard_data["p2Score"] = "0"
    scoreboard_data["p1Bracket"] = current_p1_bracket
    scoreboard_data["p2Bracket"] = current_p2_bracket
    # Stop updating next and results when we are at grand finals
    if current_round < 10:
        scoreboard_data["resultplayer1"] = result_name_1
        scoreboard_data["resultscore1"] = result1
        scoreboard_data["resultplayer2"] = result_name_2
        scoreboard_data["resultscore2"] = result2
        scoreboard_data["nextteam1"] = data["nextPlayer1"]["team"]
        scoreboard_data["nextteam2"] = data["nextPlayer2"]["team"]
        scoreboard_data["nextplayer1"] = data["nextPlayer1"]["name"]
        scoreboard_data["nextplayer2"] = data["nextPlayer2"]["name"]
        scoreboard_data["nextcountry1"] = data["nextPlayer1"]["country"]
        scoreboard_data["nextcountry2"] = data["nextPlayer2"]["country"]
    else:
        scoreboard_data["resultplayer1"] = ""
        scoreboard_data["resultscore1"] = ""
        scoreboard_data["resultplayer2"] = ""
        scoreboard_data["resultscore2"] = ""
        scoreboard_data["nextteam1"] = ""
        scoreboard_data["nextteam2"] = ""
        scoreboard_data["nextplayer1"] = ""
        scoreboard_data["nextplayer2"] = ""
        scoreboard_data["nextcountry1"] = ""
        scoreboard_data["nextcountry2"] = ""
    scoreboard_data["round"] = current_round_name
    FileUtils.write_file(scoreboard_json_file, scoreboard_data)


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
    global current_next_data
    global global_player_data
    override_string = str(override)
    with top8_lock:
        if override not in current_next_data["rounds"]:
            print("Trying to set a round that's already finished: " + override_string + " Ignoring")
            return "500"
        print("Next round override set to: " + override_string)
        current_next_data["nextRound"] = override
        current_next_data["nextRoundOverride"] = True
        FileUtils.write_file(current_next_data_file, current_next_data)
    return "200"


def get_next_round(current_round):
    global current_next_data
    for r in current_next_data["rounds"]:
        if current_round != r:
            return r
    return None


def snapshot_before_next_round():
    """Save a snapshot of all mutable state so we can undo the last next_round call."""
    global _undo_snapshot
    import copy
    scoreboard_data = read_file(scoreboard_json_file)
    _undo_snapshot = {
        "current_next_data": copy.deepcopy(current_next_data),
        "global_player_data": copy.deepcopy(global_player_data),
        "p1Score": scoreboard_data.get("p1Score", "0"),
        "p2Score": scoreboard_data.get("p2Score", "0"),
    }


def restore_snapshot():
    """Restore bracket state to before the last next_round call."""
    global _undo_snapshot, current_next_data, global_player_data, _restoring
    print(f"[restore_snapshot] called, snapshot exists: {_undo_snapshot is not None}")
    if _undo_snapshot is None:
        print("[restore_snapshot] No snapshot available")
        return None
    with top8_lock:
        current_next_data = _undo_snapshot["current_next_data"]
        global_player_data = _undo_snapshot["global_player_data"]
        current_next_data["started"] = False
        _restoring = True
        # Write files back to disk
        FileUtils.write_file(player_data_file_name, global_player_data)
        FileUtils.write_file(current_next_data_file, current_next_data)
        # Run initialize so current_next_data has correct player names
        initialize(skip_scoreboard_update=True)
        # Now write the full scoreboard with restored players and original scores
        update_scoreboard_json(
            current_next_data,
            "",  # result names cleared since we're undoing
            "",
            "",
            "",
            current_next_data["currentRoundName"],
            current_next_data["currentRound"],
            "",
            ""
        )
        # Put the scores back (update_scoreboard_json zeros them)
        scoreboard_data = read_file(scoreboard_json_file)
        scoreboard_data["p1Score"] = _undo_snapshot["p1Score"]
        scoreboard_data["p2Score"] = _undo_snapshot["p2Score"]
        FileUtils.write_file(scoreboard_json_file, scoreboard_data)
        # Verify what was written
        verify = read_file(scoreboard_json_file)
        print(f"[restore_snapshot] scoreboard.json after write: p1={verify.get('p1Name')} p2={verify.get('p2Name')} p1Score={verify.get('p1Score')} p2Score={verify.get('p2Score')}")
        print(f"[restore_snapshot] Restored to round={current_next_data['currentRound']} p1={current_next_data['player1']['name']} p2={current_next_data['player2']['name']}")
        _undo_snapshot = None
    return json.loads(json.dumps(current_next_data, ensure_ascii=False))


def reset():
    print("Resetting data..")
    global current_next_data
    global global_player_data
    with top8_lock:
        current_next_data = copy.deepcopy(defaultCurrentDataJson)
        global_player_data = copy.deepcopy(defaultPlayerData)
        FileUtils.write_file(player_data_file_name, global_player_data)
        FileUtils.write_file(current_next_data_file, current_next_data)


def reset_bracket():
    """Restart the top 8 run while keeping the eight seeded players.

    Keeps names/teams/countries in r1-r4 (the seed rounds), clears all
    scores, wipes the derived rounds (r5-r10) completely, and resets
    the run state so Start Top 8 begins again from Winners Semis."""
    print("Resetting bracket (keeping seeds)..")
    global current_next_data
    global global_player_data
    with top8_lock:
        for key, round_data in global_player_data.items():
            for pid in ("p1", "p2"):
                player = round_data.get(pid)
                if not isinstance(player, dict):
                    continue
                player["score"] = ""
                if "score2" in player:
                    player["score2"] = ""
                if key not in ("r1", "r2", "r3", "r4"):
                    player["name"] = ""
                    player["team"] = ""
                    player["country"] = ""
                    player["bracket"] = ""
        current_next_data = copy.deepcopy(defaultCurrentDataJson)
        FileUtils.write_file(player_data_file_name, global_player_data)
        FileUtils.write_file(current_next_data_file, current_next_data)


def update_current_players_info(scoreboard_json):
    global current_next_data
    with top8_lock:
        if not current_next_data["started"]:
            return
        print(f"[update_current_players_info] setting p1={scoreboard_json['p1Name']} p2={scoreboard_json['p2Name']} round={current_next_data['currentRound']}")
        current_next_data["player1"]["name"] = scoreboard_json["p1Name"]
        current_next_data["player1"]["team"] = scoreboard_json["p1Team"]
        current_next_data["player1"]["score"] = scoreboard_json["p1Score"]
        current_next_data["player1"]["country"] = scoreboard_json["p1Country"]
        current_next_data["player2"]["name"] = scoreboard_json["p2Name"]
        current_next_data["player2"]["team"] = scoreboard_json["p2Team"]
        current_next_data["player2"]["score"] = scoreboard_json["p2Score"]
        current_next_data["player2"]["country"] = scoreboard_json["p2Country"]
        FileUtils.write_file(current_next_data_file, current_next_data)


def update_next_players_info(scoreboard_json):
    global current_next_data
    with top8_lock:
        current_next_data["nextPlayer1"]["name"] = scoreboard_json["nextplayer1"]
        current_next_data["nextPlayer1"]["team"] = scoreboard_json["nextteam1"]
        current_next_data["nextPlayer2"]["name"] = scoreboard_json["nextplayer2"]
        current_next_data["nextPlayer2"]["team"] = scoreboard_json["nextteam2"]
        current_next_data["nextPlayer1"]["country"] = scoreboard_json["nextcountry1"]
        current_next_data["nextPlayer2"]["country"] = scoreboard_json["nextcountry2"]
        FileUtils.write_file(current_next_data_file, current_next_data)


def update_player_info(round_id, player_id, field, value):
    global global_player_data
    with top8_lock:
        global_player_data[round_id][player_id][field] = value
        FileUtils.write_file(player_data_file_name, global_player_data)


def set_reverse_names():
    global current_next_data
    with top8_lock:
        current_next_data["reverseNames"] = not current_next_data["reverseNames"]
        FileUtils.write_file(current_next_data_file, current_next_data)


def get_current_next_data():
    return read_file(current_next_data_file)