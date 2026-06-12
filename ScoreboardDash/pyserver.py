import json
import threading
from io import open
from flask import Flask, send_from_directory, jsonify
from flask import request
from flask_cors import CORS
import time
try:
    from scripts import AutoScoreUpdaterSt
except Exception as e:
    print(f"AutoScoreUpdaterSt disabled: {e}")
    AutoScoreUpdaterSt = None
try:
    from scripts import AutoScoreUpdaterCvs2
except Exception as e:
    print(f"AutoScoreUpdaterCvs2 disabled: {e}")
    AutoScoreUpdaterCvs2 = None
from scripts import Top8
try:
    from scripts import AutoScoreUpdaterCPS1
except Exception as e:
    print(f"AutoScoreUpdaterCPS1 disabled: {e}")
    AutoScoreUpdaterCPS1 = None
from scripts import startgg_client
import argparse
import socket
import os
import webbrowser
import shutil
import copy
import requests
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
scoreboard_data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/scoreboard.json")
commentators_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/commentators.json")
player_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/player1.txt")
player_2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/player2.txt")
next_player_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/nextplayer1.txt")
next_player_2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/nextplayer2.txt")
result1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/result1.txt")
result2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/result2.txt")
result_name_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/resultname1.txt")
result_name_2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/resultname2.txt")
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


@api.route('/resetBracket', methods=['POST'])
def reset_bracket():
    """Reset the top 8 run but keep the eight seeded players."""
    Top8.reset_bracket()
    return "200"


@api.route('/resetTop8', methods=['POST'])
def reset_top8_data():
    top8.reset()
    return "200"


@api.route('/undoNextRound', methods=['POST'])
def undo_next_round():
    result = top8.restore_snapshot()
    if result is None:
        return "No snapshot available", 400
    return json.dumps(result, ensure_ascii=False), 200


@api.route('/getStartggToken', methods=['GET'])
def get_startgg_token():
    try:
        token = startgg_client.get_token().strip()
        return json.dumps({"token": token}), 200
    except Exception:
        return json.dumps({"token": ""}), 200


def _next_player_id(players):
    """Return next sequential ID like 000001, 000002, etc."""
    existing_ids = []
    for k in players:
        if k.startswith('p_'):
            try:
                existing_ids.append(int(k[2:]))
            except ValueError:
                pass
    next_num = (max(existing_ids) + 1) if existing_ids else 1
    return f"p_{next_num:06d}"

def _read_local_players():
    """Returns dict of {id: {id, name, team, country, social_handle, social_platform}}"""
    try:
        return players_db.get_local_players()
    except Exception as e:
        print(f"_read_local_players error: {e}")
        return {}

def _find_player_by_name(players, name):
    """Find a player record by name (case-sensitive). Returns (id, record) or (None, None)."""
    for pid, p in players.items():
        if p.get("name") == name:
            return pid, p
    return None, None

@api.route('/getLocalPlayers', methods=['GET'])
def get_local_players():
    try:
        players = _read_local_players()
        result = sorted(players.values(), key=lambda p: p.get("name", "").lower())
        return json.dumps(result, ensure_ascii=False), 200
    except Exception:
        return json.dumps([]), 200

@api.route('/saveLocalPlayer', methods=['POST'])
def save_local_player():
    body = request.get_json() or {}
    name = body.get("name", "").strip()
    if not name:
        return "400", 400
    try:
        players = _read_local_players()
        pid, existing = _find_player_by_name(players, name)
        if pid is None:
            # New player — assign next ID
            pid = _next_player_id(players)
            existing = {"id": pid, "name": name, "team": "", "country": "", "social_handle": "", "social_platform": "", "is_commentator": False, "characters": {}, "roster": {}}
        # Only overwrite fields that are explicitly provided and non-empty
        if body.get("team"):            existing["team"]            = body["team"]
        if body.get("country"):         existing["country"]         = body["country"]
        if "social_handle"   in body:              existing["social_handle"]   = body["social_handle"]
        if "social_platform" in body:              existing["social_platform"] = body["social_platform"]
        if "is_commentator" in body:        existing["is_commentator"]  = bool(body["is_commentator"])
        if "characters" in body:
            if not isinstance(existing.get("characters"), dict):
                existing["characters"] = {}
            # Per-game merge: each provided game replaces that game's
            # pick list wholesale; unmentioned games are untouched.
            for g, picks in (body["characters"] or {}).items():
                if isinstance(picks, dict):
                    picks = [picks]
                existing["characters"][g] = picks
        if "roster" in body:
            if not isinstance(existing.get("roster"), dict):
                existing["roster"] = {}
            # Same per-game merge: each provided game replaces that
            # game's roster list wholesale
            for g, entries in (body["roster"] or {}).items():
                if isinstance(entries, dict):
                    entries = [entries]
                existing["roster"][g] = entries
        existing["name"] = name
        players[pid] = existing
        players_db.save_local_players(players)
    except Exception as e:
        print(f"saveLocalPlayer error: {e}")
    return "200"

@api.route('/updateLocalPlayer', methods=['POST'])
def update_local_player():
    body = request.get_json() or {}
    pid             = body.get("id", "").strip()
    name            = body.get("name", "").strip()
    team            = body.get("team", "")
    country         = body.get("country", "")
    social_handle   = body.get("social_handle", "")
    social_platform = body.get("social_platform", "")
    is_commentator  = bool(body.get("is_commentator", False))
    if not pid or not name:
        return "400", 400
    try:
        players = _read_local_players()
        if pid not in players:
            return "404", 404
        # Preserve existing characters/roster unless new ones are provided
        existing_chars = players[pid].get("characters", {})
        new_chars = body.get("characters")
        characters = new_chars if new_chars is not None else existing_chars
        existing_roster = players[pid].get("roster", {})
        new_roster = body.get("roster")
        roster = new_roster if new_roster is not None else existing_roster
        players[pid] = {"id": pid, "name": name, "team": team, "country": country,
                        "social_handle": social_handle, "social_platform": social_platform,
                        "is_commentator": is_commentator, "characters": characters,
                        "roster": roster}
        players_db.save_local_players(players)
    except Exception as e:
        print(f"updateLocalPlayer error: {e}")
    return "200"

@api.route('/deleteLocalPlayer', methods=['POST'])
def delete_local_player():
    body = request.get_json() or {}
    pid  = body.get("id", "").strip()
    name = body.get("name", "").strip()
    if not pid and not name:
        return "400", 400
    try:
        players = _read_local_players()
        if pid and pid in players:
            del players[pid]
        elif name:
            found_pid, _ = _find_player_by_name(players, name)
            if found_pid:
                del players[found_pid]
        players_db.save_local_players(players)
    except Exception as e:
        print(f"deleteLocalPlayer error: {e}")
    return "200"



@api.route('/getCharacterPacks', methods=['GET'])
def get_character_packs():
    """List all packs available for a game (subfolders of images/games/<game>/)."""
    game = request.args.get("game", "").strip()
    if not game:
        return jsonify([]), 200
    try:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images/games", game)
        if not os.path.isdir(base):
            return jsonify([]), 200
        packs = sorted([p for p in os.listdir(base)
                        if os.path.isdir(os.path.join(base, p))])
        return jsonify(packs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/getCharacterList', methods=['GET'])
def get_character_list():
    """Return character names + palette paths for a game/pack."""
    game = request.args.get("game", "").strip()
    pack = request.args.get("pack", "").strip()
    if not game or not pack:
        return jsonify({}), 200
    try:
        pack_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "images/games", game, pack)
        if not os.path.isdir(pack_dir):
            return jsonify({}), 200

        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        char_map = {}  # { characterName: [ {palette: N, path: "..."}, ... ] }

        for fname in sorted(os.listdir(pack_dir)):
            stem, ext = os.path.splitext(fname)
            if ext.lower() not in image_exts:
                continue
            if "_" not in stem:
                continue
            char, palette = stem.rsplit("_", 1)
            if not palette.isdigit():
                continue
            # Strip game code prefix (e.g. "ssf2x-ryu" -> "ryu")
            if "-" in char:
                char = char.split("-", 1)[1]
            if char not in char_map:
                char_map[char] = []
            # Path served relative to ScoreboardDash root via Flask static handler
            char_map[char].append({
                "palette": int(palette),
                "file": f"images/games/{game}/{pack}/{fname}"
            })

        # Sort palettes within each character
        for char in char_map:
            char_map[char].sort(key=lambda x: x["palette"])

        return jsonify(char_map), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/getCommentators', methods=['GET'])
def get_commentators():
    players = _read_local_players()
    result = {p["name"]: {"name": p["name"], "soc": p.get("social_handle", "")}
              for p in players.values()}
    return json.dumps(result, ensure_ascii=False), 200


@api.route('/getCommentatorPlayers', methods=['GET'])
def get_commentator_players():
    players = _read_local_players()
    result = sorted(
        [p for p in players.values() if p.get("is_commentator")],
        key=lambda p: p.get("name", "").lower()
    )
    return json.dumps(result, ensure_ascii=False), 200


@api.route('/addCommentator', methods=['POST'])
def add_commentator():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return "400", 400
    players = _read_local_players()
    pid, existing = _find_player_by_name(players, name)
    if pid is None:
        pid = _next_player_id(players)
        existing = {"id": pid, "name": name, "team": "", "country": "", "social_handle": "", "social_platform": "", "is_commentator": False}
    if data.get("soc"):
        existing["social_handle"] = data["soc"]
    players[pid] = existing
    players_db.save_local_players(players)
    return "200"


@api.route('/deleteCommentators', methods=['POST'])
def delete_commentator():
    names = request.get_json() or []
    players = _read_local_players()
    for name in names:
        pid, _ = _find_player_by_name(players, name)
        if pid:
            del players[pid]
    players_db.save_local_players(players)
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


@api.route('/getGames', methods=['GET'])
def get_games():
    """All registered games with their character slot counts.

    Folder-scanned games are auto-registered at 1 slot so the result
    always covers everything under images/games/."""
    try:
        players_db.ensure_games(character_image_loader.list_games())
        return jsonify(players_db.get_games()), 200
    except Exception as e:
        print(f"getGames error: {e}")
        return jsonify({}), 200


@api.route('/setGameSlots', methods=['POST'])
def set_game_slots():
    body = request.get_json() or {}
    name = body.get("game", "").strip()
    try:
        slots = int(body.get("char_slots", 1))
    except (TypeError, ValueError):
        return "400", 400
    if not name:
        return "400", 400
    players_db.set_game_slots(name, slots)
    return "200"


@api.route('/getAllGameImageDir', methods=['GET'])
def get_all_game_image_dir():
    global character_image_loader, full_data
    current_game = full_data.get("current_game")
    if not current_game:
        current_game = ""
    games = character_image_loader.list_games()
    players_db.ensure_games(games)
    result = {
        "current_game": current_game,
        "game_list": games
    }
    return jsonify(result), 200


GITHUB_API  = "https://api.github.com/repos/joaorb64/StreamHelperAssets/contents/games"
GITHUB_RAW  = "https://raw.githubusercontent.com/joaorb64/StreamHelperAssets/main/games"
IMAGES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images/games")


@api.route('/streamhelper/games', methods=['GET'])
def streamhelper_list_games():
    """List all games available in StreamHelperAssets."""
    try:
        resp = requests.get(GITHUB_API, timeout=10,
                            headers={"Accept": "application/vnd.github.v3+json"})
        if not resp.ok:
            return jsonify({"error": f"GitHub API error {resp.status_code}"}), 500
        games = [item["name"] for item in resp.json() if item["type"] == "dir"]
        games.sort()
        return jsonify(games), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/streamhelper/packs', methods=['GET'])
def streamhelper_list_packs():
    """List icon packs available for a game (all dirs except base_files)."""
    game = request.args.get("game", "")
    if not game:
        return jsonify({"error": "game required"}), 400
    try:
        # Packs live at game root level, excluding base_files
        url = f"{GITHUB_API}/{game}"
        resp = requests.get(url, timeout=10,
                            headers={"Accept": "application/vnd.github.v3+json"})
        if not resp.ok:
            return jsonify({"error": f"GitHub API error {resp.status_code}"}), 500
        packs = [item["name"] for item in resp.json()
                 if item["type"] == "dir"]
        packs.sort()
        return jsonify(packs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api.route('/streamhelper/download', methods=['POST'])
def streamhelper_download():
    """Download a full icon pack for a game from StreamHelperAssets."""
    body     = request.get_json() or {}
    game     = body.get("game", "").strip()
    pack     = body.get("pack", "").strip()
    if not game or not pack:
        return jsonify({"error": "game and pack required"}), 400

    try:
        # 1. Fetch config.json to get character codenames
        config_url = f"{GITHUB_RAW}/{game}/base_files/config.json"
        config_resp = requests.get(config_url, timeout=10)
        if not config_resp.ok:
            return jsonify({"error": f"Could not fetch config.json: {config_resp.status_code}"}), 500
        config = config_resp.json()

        # character_to_codename maps name → {codename, ...}
        char_map = config.get("character_to_codename", {})
        # Build list of codenames
        codenames = list({v.get("codename", k) if isinstance(v, dict) else v
                          for k, v in char_map.items()})
        if not codenames:
            # Fallback: list files in the pack directory via API
            pack_url = f"{GITHUB_API}/{game}/base_files/{pack}"
            pack_resp = requests.get(pack_url, timeout=10,
                                     headers={"Accept": "application/vnd.github.v3+json"})
            if pack_resp.ok:
                codenames = [item["name"].rsplit(".", 1)[0]
                             for item in pack_resp.json()
                             if item["type"] == "file" and
                             item["name"].lower().endswith((".png",".jpg",".jpeg",".webp",".gif"))]

        # 2. Ensure output directory exists
        out_dir = os.path.join(IMAGES_PATH, game, pack)
        os.makedirs(out_dir, exist_ok=True)

        # 3. Fetch each icon and save with _skin suffix
        downloaded = []
        failed = []
        # Each codename may have multiple skins (named codename_0.png, codename_1.png...)
        # First try to list the pack to get actual filenames
        pack_api_url = f"{GITHUB_API}/{game}/{pack}"
        pack_api_resp = requests.get(pack_api_url, timeout=10,
                                     headers={"Accept": "application/vnd.github.v3+json"})
        # For base_files, recursively collect files from subfolders
        if pack_api_resp.ok:
            items = pack_api_resp.json()
            subdirs = [item["name"] for item in items if item["type"] == "dir"]
            files = [item["name"] for item in items
                     if item["type"] == "file" and
                     item["name"].lower().endswith((".png",".jpg",".jpeg",".webp",".gif"))]
            # If pack has subdirs (like base_files/icon/), collect from each
            for subdir in subdirs:
                sub_url = f"{GITHUB_API}/{game}/{pack}/{subdir}"
                sub_resp = requests.get(sub_url, timeout=10,
                                        headers={"Accept": "application/vnd.github.v3+json"})
                if sub_resp.ok:
                    for item in sub_resp.json():
                        if item["type"] == "file" and                            item["name"].lower().endswith((".png",".jpg",".jpeg",".webp")):
                            files.append(subdir + "/" + item["name"])
        else:
            files = [f"{c}_0.png" for c in codenames]

        for fname in files:
            # Strip subdir prefix if present (e.g. "icon/ryu_0.png" -> "ryu_0.png")
            flat_fname = fname.split("/")[-1]
            stem = flat_fname.rsplit(".", 1)[0]  # e.g. ryu_0
            if "_" not in stem or not stem.rsplit("_", 1)[1].isdigit():
                dest_name = stem + "_0.png"
            else:
                dest_name = flat_fname
            # Route logo files to a Logos subfolder
            is_logo = stem.lower().startswith("logo")
            if is_logo:
                logo_dir = os.path.join(IMAGES_PATH, game, "game_logo")
                os.makedirs(logo_dir, exist_ok=True)
                file_dest_dir = logo_dir
            else:
                file_dest_dir = out_dir

            raw_url = f"{GITHUB_RAW}/{game}/{pack}/{fname}"
            img_resp = requests.get(raw_url, timeout=15)
            if img_resp.ok:
                # Preserve original extension
                orig_ext = os.path.splitext(fname.split("/")[-1])[1]
                dest_name_ext = os.path.splitext(dest_name)[0] + orig_ext
                dest = os.path.join(file_dest_dir, dest_name_ext)
                with open(dest, "wb") as f:
                    f.write(img_resp.content)
                downloaded.append(dest_name)
            else:
                failed.append(fname)

        return jsonify({
            "downloaded": len(downloaded),
            "failed":     len(failed),
            "failed_files": failed[:10],
            "game":       game,
            "pack":       pack,
            "out_dir":    out_dir
        }), 200

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


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
        for key in ["com1", "com2", "soc1", "soc2", "com1Plat", "com2Plat"]:
            if key in json_data:
                temp[key] = json_data[key]
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
        temp["p1SocialHandle"]    = json_data.get("p1SocialHandle",    "")
        temp["p1SocialPlatform"]  = json_data.get("p1SocialPlatform",  "")
        temp["p2SocialHandle"]    = json_data.get("p2SocialHandle",    "")
        temp["p2SocialPlatform"]  = json_data.get("p2SocialPlatform",  "")
        temp["nextSocial1Handle"]   = json_data.get("nextSocial1Handle",   "")
        temp["nextSocial1Platform"] = json_data.get("nextSocial1Platform", "")
        temp["nextSocial2Handle"]   = json_data.get("nextSocial2Handle",   "")
        temp["nextSocial2Platform"] = json_data.get("nextSocial2Platform", "")
        temp["p1Character"]     = json_data.get("p1Character",     "")
        temp["p1CharacterPack"] = json_data.get("p1CharacterPack", "")
        temp["p1Palette"]       = json_data.get("p1Palette",       0)
        temp["p1CharacterFile"] = json_data.get("p1CharacterFile", "")
        temp["p2Character"]     = json_data.get("p2Character",     "")
        temp["p2CharacterPack"] = json_data.get("p2CharacterPack", "")
        temp["p2Palette"]       = json_data.get("p2Palette",       0)
        temp["p2CharacterFile"] = json_data.get("p2CharacterFile", "")
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


@api.route('/updatePlayerCharacters', methods=['POST'])
def update_player_characters():
    """Write one player's character picks into scoreboard.json.

    Used by pages other than the event dashboard (e.g. Top 8) so they
    can update character data without owning the full scoreboard JSON.
    Body: { "player": "1"|"2", "characters": [ {slot, pack, character,
    palette, file}, ... ] }"""
    global full_data
    body = request.get_json() or {}
    player = str(body.get("player", "")).strip()
    if player not in ("1", "2", "1Next", "2Next"):
        return "400", 400
    chars = body.get("characters") or []
    if isinstance(chars, dict):
        chars = [chars]
    if not isinstance(chars, list):
        return "400", 400
    first = next((c for c in chars if isinstance(c, dict) and c.get("file")), None)
    with full_data_lock:
        temp = copy.deepcopy(full_data)
        temp["p" + player + "Characters"]    = chars
        temp["p" + player + "Character"]     = (first or {}).get("character", "")
        temp["p" + player + "CharacterPack"] = (first or {}).get("pack", "")
        temp["p" + player + "Palette"]       = (first or {}).get("palette", 0)
        temp["p" + player + "CharacterFile"] = (first or {}).get("file", "")
        full_data = temp
    FileUtils.write_file(scoreboard_data_file, full_data)
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
    # Set working directory to ScoreboardDash/ so all relative paths resolve correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
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
            open_browser("http://" + server_info, 'open -a /Applications/Google\\ Chrome.app %s')
        elif args.linux:
            open_browser("http://" + server_info, '/usr/bin/google-chrome %s')

        players_db.init_db()
        api.run(host=server_ip, port=server_port)
    except KeyboardInterrupt:
        pass