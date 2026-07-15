import json
import threading
from io import open
from flask import Flask, send_from_directory, jsonify, Response
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
from scripts import parry_client
from scripts import MatchHistory
from scripts import SeedingRank
from scripts import DataTransfer
from scripts import LocationResolve
import argparse
import socket
import os
import webbrowser
import shutil
import copy
import requests
import re
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
crewbattle_data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/crewbattle.json")
station_announcement_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/station_announcement.json")
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
# Cap request bodies at 20MB. Flask rejects anything larger with a 413 BEFORE
# reading it into memory, which protects the import endpoints from a huge or
# malicious bundle exhausting RAM. Real payloads (scoreboard state, player
# edits, data bundles) are kilobytes to low-KB; a real export is well under 1MB,
# so 20MB is comfortably future-proof while still stopping a runaway file.
api.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024


@api.errorhandler(413)
def _too_large(e):
    # Return JSON (not the default HTML error page) so the import page shows a
    # clear message instead of failing to parse the response.
    return jsonify({"ok": False,
                    "message": "That file is too large (limit is 20 MB). A normal "
                               "backup is well under 1 MB, so this looks wrong."}), 413

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



# ════════════════════════════════════════════════════════════════
# LIVE SYNC (server-sent events)
# Pages subscribe to /events; the server publishes a channel name
# whenever data changes. Channels: scoreboard, top8, players,
# commentators. Publishing is driven by write hooks in FileUtils and
# PlayerStatsDB, so every mutation path is covered automatically.
# ════════════════════════════════════════════════════════════════
import queue as _queue

_sse_clients = []
_sse_lock = threading.Lock()

_SSE_FILE_CHANNELS = {
    "scoreboard.json": "scoreboard",
    "current_next.json": "top8",
    "top8_players.json": "top8",
    "commentators.json": "commentators",
}


def _sse_publish(channel):
    with _sse_lock:
        clients = list(_sse_clients)
    for q in clients:
        try:
            q.put_nowait(channel)
        except _queue.Full:
            pass


def _sse_on_file_write(file_path):
    channel = _SSE_FILE_CHANNELS.get(os.path.basename(str(file_path)))
    if channel:
        _sse_publish(channel)


FileUtils.on_write = _sse_on_file_write
players_db.on_change = lambda: _sse_publish("players")


@api.route('/events')
def sse_events():
    def stream():
        q = _queue.Queue(maxsize=100)
        with _sse_lock:
            _sse_clients.append(q)
        try:
            yield "retry: 2000\n\n"
            while True:
                try:
                    channel = q.get(timeout=25)
                    yield "data: " + channel + "\n\n"
                except _queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _sse_lock:
                try:
                    _sse_clients.remove(q)
                except ValueError:
                    pass
    return Response(stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache',
                             'X-Accel-Buffering': 'no'})


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
    """Resolve by display name or alias, case-insensitive."""
    if not name:
        return None, None
    n = name.strip().lower()
    for pid, p in players.items():
        if p.get("name", "").strip().lower() == n:
            return pid, p
    for pid, p in players.items():
        for alias in (p.get("aliases") or []):
            if alias.strip().lower() == n:
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

def _default_team(name):
    return {"name": name, "players": [], "current": 0,
            "captainLabel": "Captain", "viceLabel": "Vice",
            "remainingLabel": "left", "plateColor": ""}


def _norm_player(p):
    """Normalize a player entry, preserving optional character pick."""
    p = p or {}
    out = {"name": p.get("name", "")}
    # Optional pre-picked character (from the selected game's roster).
    # Stored: pack, character name, palette, and the art file for the overlay.
    if p.get("character") or p.get("characterFile") or p.get("pack"):
        out["pack"] = p.get("pack", "")
        out["character"] = p.get("character", "")
        try:
            out["palette"] = int(p.get("palette", 0))
        except (TypeError, ValueError):
            out["palette"] = 0
        out["characterFile"] = p.get("characterFile", "")
    return out


def _norm_team(t, fallback_name):
    """Normalize an incoming team object, filling defaults."""
    t = t or {}
    players = [_norm_player(p) for p in (t.get("players", []) or [])]
    try:
        current = int(t.get("current", 0))
    except (TypeError, ValueError):
        current = 0
    # clamp pointer to [0, len] (len == whole team wiped out)
    if current < 0:
        current = 0
    if current > len(players):
        current = len(players)
    return {
        "name": (t.get("name") or fallback_name),
        "players": players,
        "current": current,
        "captainLabel": t.get("captainLabel", "Captain"),
        "viceLabel": t.get("viceLabel", "Vice"),
        "remainingLabel": t.get("remainingLabel", "left"),
        "plateColor": (t.get("plateColor") or "").strip(),
    }


@api.route('/getCrewBattle', methods=['GET'])
def get_crew_battle():
    """Return the current East-vs-West crew battle state."""
    data = FileUtils.read_file(crewbattle_data_file)
    if not data:
        data = {"team1": _default_team("East"), "team2": _default_team("West"),
                "pageSize": 12, "game": ""}
    return json.dumps(data, ensure_ascii=False), 200


@api.route('/getStationAnnouncement', methods=['GET'])
def get_station_announcement():
    """Return the current stations-page announcement text (e.g. 'Please
    report match scores to...'). Shown above the station/stream queue lists
    on both the main Stations page and its popout. Server-persisted (not
    localStorage) so it reaches a popout running on a separate venue
    machine/TV, not just the TO's own browser."""
    data = FileUtils.read_file(station_announcement_file)
    return json.dumps({"text": (data or {}).get("text", "")}, ensure_ascii=False), 200


@api.route('/saveStationAnnouncement', methods=['POST'])
def save_station_announcement():
    body = request.get_json() or {}
    text = (body.get("text") or "").strip()[:300]   # generous cap, plain display text
    try:
        with open(station_announcement_file, "w", encoding="utf-8") as f:
            json.dump({"text": text}, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True, "text": text}), 200
    except Exception as e:
        print("saveStationAnnouncement error: " + str(e))
        return jsonify({"ok": False, "message": str(e)}), 500


@api.route('/saveCrewBattle', methods=['POST'])
def save_crew_battle():
    """Persist the crew battle state. Body is the full state object:
       { team1: {name, players:[{name}], current, captainLabel, viceLabel},
         team2: {...} }.
    'current' is the active-player pointer: players before it are defeated,
    the one at it is up, those after are waiting. The last two players get
    the captain/vice role labels prefixed on the overlay."""
    body = request.get_json() or {}
    try:
        page_size = int(body.get("pageSize", 12))
    except (TypeError, ValueError):
        page_size = 12
    if page_size < 1:
        page_size = 1
    state = {
        "team1": _norm_team(body.get("team1"), "Team 1"),
        "team2": _norm_team(body.get("team2"), "Team 2"),
        "pageSize": page_size,
        "game": (body.get("game") or "").strip(),
    }
    try:
        with open(crewbattle_data_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True}), 200
    except Exception as e:
        print("saveCrewBattle error: " + str(e))
        return jsonify({"ok": False, "message": str(e)}), 500


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
            existing = {"id": pid, "name": name, "team": "", "country": "", "state": "", "social_handle": "", "social_platform": "", "is_commentator": False, "characters": {}, "roster": {}, "aliases": []}
        # Only overwrite fields that are explicitly provided and non-empty
        if body.get("team"):            existing["team"]            = body["team"]
        if body.get("country"):         existing["country"]         = body["country"]
        if "state" in body:             existing["state"]           = body["state"]   # allow clearing
        if "city" in body:              existing["city"]            = body["city"]    # allow clearing
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
        if "aliases" in body and isinstance(body["aliases"], list):
            existing["aliases"] = body["aliases"]
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
    state           = body.get("state", "")
    city            = body.get("city", "")
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
        existing_aliases = players[pid].get("aliases", [])
        new_aliases = body.get("aliases")
        aliases = new_aliases if new_aliases is not None else existing_aliases
        # Preserve the auto-pulled state_id when the state TEXT is unchanged;
        # if the TO edited the state, the text becomes authoritative and the
        # old canonical id no longer applies. (Without this, every manual
        # profile edit silently wiped state_id.)
        old_state = (players[pid].get("state") or "").strip()
        state_id = players[pid].get("state_id") if (state or "").strip() == old_state else None
        players[pid] = {"id": pid, "name": name, "team": team, "country": country,
                        "state": state, "state_id": state_id, "city": city,
                        "social_handle": social_handle, "social_platform": social_platform,
                        "is_commentator": is_commentator, "characters": characters,
                        "roster": roster, "aliases": aliases}
        players_db.save_local_players(players)
    except Exception as e:
        print(f"updateLocalPlayer error: {e}")
    return "200"

@api.route('/mergePlayers', methods=['POST'])
def merge_players():
    """Merge one player record into another.

    Body: { "primary_id": "p_000001", "duplicate_id": "p_000005" }
    The duplicate's name and aliases become aliases of the primary."""
    body = request.get_json() or {}
    primary_id = body.get("primary_id", "")
    duplicate_id = body.get("duplicate_id", "")
    if not primary_id or not duplicate_id:
        return jsonify({"ok": False, "message": "Both players required"}), 400
    try:
        ok, message = players_db.merge_players(primary_id, duplicate_id)
        return jsonify({"ok": ok, "message": message}), (200 if ok else 400)
    except Exception as e:
        print(f"mergePlayers error: {e}")
        return jsonify({"ok": False, "message": str(e)}), 500


# ════════════════════════════════════════════════════════════════
# MATCH HISTORY IMPORT (start.gg -> per-event JSON + all-time rollup)
# ════════════════════════════════════════════════════════════════
def _parse_event_slug(raw, source="startgg"):
    """Return (tournament_slug, event_slug) from a URL or slug pair.

    start.gg: full URL or 'tournament/.../event/...'.
    parry.gg: a parry.gg event URL, or a 'tournamentSlug/eventSlug' pair.
    parry URLs look like:
      parry.gg/<tournament-slug>/<event-slug>/<extra...>
    (e.g. .../super-street-fighter-ii-turbo-arcade/_standings or
     .../main/bracket), so we take the FIRST two path segments.
    """
    s = (raw or "").strip()
    if source == "parry":
        # Strip a parry.gg host if present, plus query/hash.
        s = re.sub(r"^https?://(www\.)?parry\.gg/", "", s)
        s = s.split("?")[0].split("#")[0].strip("/")
        parts = [p for p in re.split(r"[\s/]+", s) if p]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None, None
    # start.gg
    m = re.search(r"tournament/([^/]+)/event/([^/?#]+)", s)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _alias_map_for_rollup():
    """Identity map is 1:1 today (merge already rewrites ids in the DB),
    so the rollup needs no remap. Kept as a seam for future use."""
    return {}


def _build_assignments(players):
    """Map start.gg keys -> local player id for auto-matching.

    Keys: 'u:<user_id>' (from a stored alias like 'sgg:12345') and the
    raw tag (resolved by name/alias). Tag match is case-insensitive via
    the player maps."""
    assignments = {}
    by_name = {}
    for pid, p in players.items():
        by_name[p["name"].strip().lower()] = pid
        for a in (p.get("aliases") or []):
            a = a.strip()
            by_name[a.lower()] = pid
            # Aliases of the form 'sgg:<userid>' tie a start.gg account
            if a.lower().startswith("sgg:"):
                assignments["u:" + a.split(":", 1)[1]] = pid
            # Aliases of the form 'pgg:<uuid>' tie a parry.gg account.
            # parry user ids are UUIDs, so they share the 'u:' namespace
            # with start.gg numeric ids without collision.
            elif a.lower().startswith("pgg:"):
                assignments["u:" + a.split(":", 1)[1]] = pid
    return assignments, by_name


@api.route('/importStartggEvent', methods=['POST'])
def import_startgg_event():
    """Fetch an event's completed sets and write the per-event file.

    Body: { "slug": "<url or slug>" }
    Auto-matches entrants to local players by start.gg user id (via
    'sgg:<id>' aliases) and by tag/alias name. Returns the import
    summary plus the list of entrants still needing reconciliation."""
    body = request.get_json() or {}
    source = (body.get("source") or "startgg").strip().lower()
    tournament, event = _parse_event_slug(body.get("slug", ""), source)
    series = (body.get("series") or "").strip()
    game = (body.get("game") or "").strip()
    if not tournament or not event:
        return jsonify({"ok": False, "message": "Could not parse an event slug from that input"}), 400
    if not game:
        return jsonify({"ok": False, "message": "A game must be selected for every import."}), 400

    # Fetch from the chosen source. Both clients return the SAME normalized
    # shape, so everything downstream is source-agnostic.
    if source == "parry":
        sets, perr = parry_client.get_completed_matches(tournament, event)
        if perr:
            print("import parry fetch error: " + str(perr))
            return jsonify({"ok": False, "message": "parry.gg fetch failed: " + str(perr)}), 502
        standings, serr = parry_client.get_event_standings(tournament, event)
        if serr:
            print("import parry standings warning: " + str(serr))
            standings = None
        uid_prefix = "u:"
    else:
        try:
            sets = startgg_client.get_completed_sets(tournament, event)
        except Exception as e:
            print("importStartggEvent fetch error: " + str(e))
            return jsonify({"ok": False, "message": "start.gg fetch failed: " + str(e)}), 502
        try:
            standings = startgg_client.get_event_standings(tournament, event)
        except Exception as e:
            print("importStartggEvent standings warning: " + str(e))
            standings = None
        # DQ hygiene: get_completed_sets now skips DQ sets, so an entrant who
        # appears in ZERO remaining sets never actually played -- a full DQ.
        # Drop their placement so they don't earn seeding points for an event
        # they didn't compete in. (Partial DQs -- played real sets, then DQ'd
        # out -- keep their placement; only their DQ sets are skipped.)
        if standings and sets:
            played_uids = set()
            played_tags = set()
            for s in sets:
                for side in ("p1", "p2"):
                    ent = s.get(side) or {}
                    if ent.get("user_id"):
                        played_uids.add(str(ent["user_id"]))
                    if ent.get("tag"):
                        played_tags.add(ent["tag"].strip().lower())
            before = len(standings)
            standings = [st for st in standings
                         if (st.get("user_id") is not None and str(st["user_id"]) in played_uids)
                         or ((st.get("tag") or "").strip().lower() in played_tags)]
            dropped = before - len(standings)
            if dropped:
                print("importStartggEvent: dropped %d placement(s) for entrant(s) "
                      "with no played sets (full DQ)" % dropped)
        uid_prefix = "u:"
    if not sets:
        return jsonify({"ok": False, "message": "No completed sets found for that event"}), 404

    players = players_db.get_local_players()
    assignments, by_name = _build_assignments(players)
    # Also resolve by tag name where user-id didn't match
    for s in sets:
        for side in ("p1", "p2"):
            ent = s[side]
            uid_key = (uid_prefix + str(ent["user_id"])) if ent.get("user_id") else None
            if uid_key and uid_key in assignments:
                continue
            pid = by_name.get((ent.get("tag") or "").strip().lower())
            if pid:
                assignments[ent.get("tag")] = pid

    # Capture the real event date. start.gg exposes startAt (a Unix timestamp);
    # convert to a YYYY-MM-DD string. parry has no equivalent here, so it's left
    # blank for the TO to set manually on the Match Imports page.
    event_date = ""
    if source != "parry":
        try:
            ts = startgg_client.get_event_start_at(tournament, event)
            if ts:
                event_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception as e:
            print("importStartggEvent startAt warning: " + str(e))

    event_slug = "tournament/" + tournament + "/event/" + event
    event_name = sets[0].get("event_name") or event
    tourn_name = sets[0].get("tournament_name") or tournament
    count = MatchHistory.save_event_import(
        event_slug, event_name, tourn_name, sets,
        datetime.now().isoformat(timespec="seconds"), assignments, standings,
        series if series else None, game,
        event_date if event_date else None)
    MatchHistory.rebuild_alltime(_alias_map_for_rollup())
    unassigned = MatchHistory.collect_unassigned(event_slug)
    print("Imported %d sets from '%s' (%s) -- %d player(s) need reconciling"
          % (count, event_name, event_slug, len(unassigned)))
    return jsonify({"ok": True, "event_slug": event_slug, "event_name": event_name,
                    "tournament_name": tourn_name, "set_count": count,
                    "unassigned": unassigned}), 200


@api.route('/listImportedEvents', methods=['GET'])
def list_imported_events():
    return jsonify(MatchHistory.list_events()), 200


@api.route('/setEventDate', methods=['POST'])
def set_event_date():
    """Manually set (or correct) an imported event's real date.

    Body: { event_slug, event_date }  -- event_date is 'YYYY-MM-DD' or ''.
    Used to date parry imports and bulk-imported old events so seeding's
    recency/absence ordering reflects when the event actually happened."""
    body = request.get_json() or {}
    slug = (body.get("event_slug") or "").strip()
    date = (body.get("event_date") or "").strip()
    if not slug:
        return jsonify({"ok": False, "message": "event_slug is required"}), 400
    ok = MatchHistory.set_event_date(slug, date)
    if not ok:
        return jsonify({"ok": False, "message": "Event not found"}), 404
    return jsonify({"ok": True, "event_slug": slug, "event_date": date}), 200


# ── DATA BACKUP / TRANSFER ────────────────────────────────────────────
# Export the player DB and/or match history as a single JSON bundle, so a
# setup prepared on one machine can be moved to another. Import (Replace /
# Merge) is added in later steps; export comes first.

@api.route('/exportData', methods=['GET'])
def export_data():
    """Download a JSON bundle of the player DB and/or match history.

    Query params: players=1/0, history=1/0 (default both). Returns the
    bundle as a file download."""
    inc_players = request.args.get("players", "1") != "0"
    inc_history = request.args.get("history", "1") != "0"
    if not inc_players and not inc_history:
        return jsonify({"ok": False, "message": "Select at least one of players or history."}), 400
    bundle = DataTransfer.build_bundle(players_db, MatchHistory,
                                       include_players=inc_players,
                                       include_history=inc_history)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    parts = "-".join(bundle["contents"]) or "empty"
    fname = "scoreboarddash-%s-%s.json" % (parts, stamp)
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    resp = Response(payload, mimetype="application/json")
    resp.headers["Content-Disposition"] = "attachment; filename=" + fname
    return resp


@api.route('/importDataInspect', methods=['POST'])
def import_data_inspect():
    """Validate an uploaded bundle and return a summary (what it contains)
    WITHOUT applying anything. Lets the page show the user what they're about
    to import before they commit."""
    bundle = request.get_json(silent=True)
    if bundle is None:
        return jsonify({"ok": False, "message": "Could not read that file as JSON."}), 400
    ok, msg = DataTransfer.validate_bundle(bundle)
    if not ok:
        return jsonify({"ok": False, "message": msg}), 400
    return jsonify({"ok": True, "summary": DataTransfer.bundle_summary(bundle)}), 200


@api.route('/importData', methods=['POST'])
def import_data():
    """Import a bundle. Body: { bundle: {...}, mode: 'replace',
    players: bool, history: bool }.

    Always takes an auto-backup of the CURRENT data first (reversible), then
    replaces the selected sections. (Merge mode is added in a later step.)"""
    body = request.get_json(silent=True) or {}
    bundle = body.get("bundle")
    mode = body.get("mode", "replace")
    do_players = body.get("players", True)
    do_history = body.get("history", True)

    if bundle is None:
        return jsonify({"ok": False, "message": "No bundle provided."}), 400
    ok, msg = DataTransfer.validate_bundle(bundle)
    if not ok:
        return jsonify({"ok": False, "message": msg}), 400
    if mode not in ("replace", "merge"):
        return jsonify({"ok": False, "message": "Unknown import mode."}), 400

    # Can only import a section the bundle actually contains.
    has_players = bundle.get("players") is not None
    has_history = bundle.get("events") is not None
    do_players = do_players and has_players
    do_history = do_history and has_history
    if not do_players and not do_history:
        return jsonify({"ok": False, "message": "Nothing to import (check your selections vs. the bundle contents)."}), 400

    # 1) Auto-backup current state (always, before touching anything).
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/backups")
    try:
        backup_path = DataTransfer.write_auto_backup(players_db, MatchHistory, backup_dir)
    except Exception as e:
        return jsonify({"ok": False, "message": "Auto-backup failed, import aborted: %s" % e}), 500

    # 2) Apply.
    try:
        if mode == "replace":
            result = {"players_imported": 0, "events_imported": 0}
            if do_players:
                result["players_imported"] = DataTransfer.restore_players(players_db, bundle)
            if do_history:
                result["events_imported"] = DataTransfer.restore_history_replace(MatchHistory, bundle)
                MatchHistory.rebuild_alltime(_alias_map_for_rollup())
        else:  # merge
            resolutions = body.get("resolutions") or {}
            result = DataTransfer.apply_merge(players_db, MatchHistory, bundle, resolutions,
                                              do_players=do_players, do_history=do_history,
                                              next_id_fn=_next_player_id)
            if do_history:
                MatchHistory.rebuild_alltime(_alias_map_for_rollup())
    except Exception as e:
        return jsonify({"ok": False,
                        "message": "Import failed after backup (your data may be partially changed; "
                                   "the pre-import backup is at %s): %s" % (backup_path, e)}), 500

    return jsonify({"ok": True, "mode": mode,
                    "backup_path": os.path.basename(backup_path),
                    **result}), 200


@api.route('/mergeAnalyze', methods=['POST'])
def merge_analyze():
    """Analyze a bundle against the current player DB for merge, returning
    which incoming players auto-merge, auto-add, or need a decision. Does not
    change anything -- drives the resolution UI."""
    body = request.get_json(silent=True) or {}
    bundle = body.get("bundle")
    if bundle is None:
        return jsonify({"ok": False, "message": "No bundle provided."}), 400
    ok, msg = DataTransfer.validate_bundle(bundle)
    if not ok:
        return jsonify({"ok": False, "message": msg}), 400
    if bundle.get("players") is None:
        return jsonify({"ok": True, "plan": {"confident": [], "new": [], "ambiguous": []}}), 200
    dest = players_db.get_local_players()
    plan = DataTransfer.analyze_merge(dest, bundle)
    return jsonify({"ok": True, "plan": plan}), 200


@api.route('/reconcileImport', methods=['POST'])
def reconcile_import():
    """Attach an unmatched start.gg entrant to a local player.

    Body: { "event_slug", "tag", "user_id" (optional),
             "action": "existing"|"new", "player_id" (for existing) }
    For 'existing': records the tag (and 'sgg:<user_id>' if present) as
    aliases of the chosen player, so future imports auto-match. For
    'new': creates a player from the tag with those same aliases.
    Then re-stamps the event file and rebuilds the rollup."""
    body = request.get_json() or {}
    event_slug = body.get("event_slug", "")
    tag = (body.get("tag") or "").strip()
    user_id = body.get("user_id")
    action = body.get("action")
    source = (body.get("source") or "startgg").strip().lower()
    if not event_slug or not tag or action not in ("existing", "new"):
        return jsonify({"ok": False, "message": "Missing event_slug, tag, or action"}), 400

    players = players_db.get_local_players()
    new_aliases = [tag]
    if user_id:
        # Tag the account alias by source so future imports auto-match.
        prefix = "pgg:" if source == "parry" else "sgg:"
        new_aliases.append(prefix + str(user_id))

    if action == "existing":
        pid = body.get("player_id", "")
        if pid not in players:
            return jsonify({"ok": False, "message": "Unknown player_id"}), 400
        existing = set(a.lower() for a in players[pid].get("aliases", []))
        for a in new_aliases:
            if a.lower() != players[pid]["name"].lower() and a.lower() not in existing:
                players[pid].setdefault("aliases", []).append(a)
                existing.add(a.lower())
    else:  # new
        pid = _next_player_id(players)
        players[pid] = {"id": pid, "name": tag, "team": "", "country": "",
                        "social_handle": "", "social_platform": "",
                        "is_commentator": False, "characters": {}, "roster": {},
                        "aliases": [a for a in new_aliases if a.lower() != tag.lower()]}
    players_db.save_local_players(players)

    # Re-stamp this event with refreshed assignments, then rebuild rollup
    players = players_db.get_local_players()
    assignments, by_name = _build_assignments(players)
    data = MatchHistory.load_event(event_slug)
    if data:
        raw_sets = []
        for s in data.get("sets", {}).values():
            raw_sets.append({
                "set_id": s["set_id"], "full_round_text": s.get("round_name", ""),
                "round": s.get("round"), "completed_at": s.get("completed_at"),
                "event_name": data.get("event_name"), "tournament_name": data.get("tournament_name"),
                "p1": {"tag": s["p1"]["tag"], "team": s["p1"].get("team", ""),
                       "user_id": s["p1"].get("user_id"), "entrant_id": s["p1"].get("entrant_id"), "country": "US"},
                "p2": {"tag": s["p2"]["tag"], "team": s["p2"].get("team", ""),
                       "user_id": s["p2"].get("user_id"), "entrant_id": s["p2"].get("entrant_id"), "country": "US"},
                "p1_score": s.get("p1_score"), "p2_score": s.get("p2_score"),
                "winner_entrant_id": s.get("winner_entrant_id"), "winner_user_id": s.get("winner_user_id"),
            })
        # name-tag resolution pass
        for s in raw_sets:
            for side in ("p1", "p2"):
                ent = s[side]
                uid_key = ("u:" + str(ent["user_id"])) if ent.get("user_id") else None
                if uid_key and uid_key in assignments:
                    continue
                p = by_name.get((ent.get("tag") or "").strip().lower())
                if p:
                    assignments[ent.get("tag")] = p
        MatchHistory.save_event_import(event_slug, data.get("event_name"),
                                       data.get("tournament_name"), raw_sets,
                                       data.get("imported_at"), assignments)
    MatchHistory.rebuild_alltime(_alias_map_for_rollup())
    unassigned = MatchHistory.collect_unassigned(event_slug)
    return jsonify({"ok": True, "player_id": pid, "unassigned": unassigned}), 200


@api.route('/deleteImportedEvent', methods=['POST'])
def delete_imported_event():
    """Remove an imported event's data and rebuild the rollup.

    Body: { "event_slug": "..." }. Players/aliases are left intact."""
    body = request.get_json() or {}
    event_slug = body.get("event_slug", "")
    if not event_slug:
        return jsonify({"ok": False, "message": "event_slug required"}), 400
    removed = MatchHistory.delete_event(event_slug)
    MatchHistory.rebuild_alltime(_alias_map_for_rollup())
    if removed:
        print("Removed imported event '%s'" % event_slug)
    return jsonify({"ok": True, "removed": removed}), 200


@api.route('/listSeries', methods=['GET'])
def list_series():
    return jsonify(MatchHistory.list_series()), 200


# ── SEEDING SUGGESTION ────────────────────────────────────────────────
# Pull a tournament's entrants, match them to local players, and rank the
# matched-with-history group by placement points (with optional decay) so a
# TO can read the suggested seed order and enter it into start.gg manually.
# Read-only: this never writes seeds back to start.gg.

# Cache the last-fetched entrant list per event so changing decay settings
# doesn't re-hit the start.gg API each time.
_seeding_entrant_cache = {}


def _scoped_events(scope_type, scope_value):
    """Return event dicts (with placements) in the chosen scope.

    scope_type: 'all' | 'series' | 'game'. scope_value is the series or
    game name when applicable."""
    out = []
    for meta in MatchHistory.list_events():
        if scope_type == "series" and (meta.get("series") or "") != scope_value:
            continue
        if scope_type == "game" and (meta.get("game") or "") != scope_value:
            continue
        data = MatchHistory.load_event(meta["event_slug"])
        if not data:
            continue
        data["label"] = meta.get("label") or meta.get("event_slug")
        out.append(data)
    return out


@api.route('/seedingCompute', methods=['POST'])
def seeding_compute():
    """Fetch a tournament's entrants, resolve to local players, and rank.

    Body: {
      slug,                         # full start.gg event URL or slug
      scope_type: 'all'|'series'|'game', scope_value,
      curve, decay_mode, threshold, recency_factor,   # ranking knobs
      refresh: bool                 # re-pull entrants instead of using cache
    }
    Returns three groups: ranked (matched + history), known_unranked
    (matched, no history in scope), unmatched (no local player)."""
    body = request.get_json() or {}
    tournament, event = _parse_event_slug(body.get("slug", ""), "startgg")
    if not tournament or not event:
        return jsonify({"ok": False, "message": "Could not parse an event slug from that input"}), 400

    cache_key = tournament + "|" + event
    entrants = _seeding_entrant_cache.get(cache_key)
    if entrants is None or body.get("refresh"):
        try:
            entrants = startgg_client.get_all_players_from_tournament(tournament, event)
        except Exception as e:
            print("seedingCompute entrant fetch error: %s" % e)
            return jsonify({"ok": False, "message": "Could not fetch entrants: %s" % e}), 502
        _seeding_entrant_cache[cache_key] = entrants

    # Resolve each entrant to a local player via the same alias/assignment
    # logic the importer uses.
    players = players_db.get_local_players()
    assignments, by_name = _build_assignments(players)

    def ent_fields(ent):
        """Normalize an entrant into {tag, user_id, team}.

        get_all_players_from_tournament returns Player OBJECTS (attributes
        .name/.team/.entrant_id/.country/.seed, no user_id), but other call
        sites use plain dicts -- handle both. The tag is the display name."""
        if isinstance(ent, dict):
            return {"tag": (ent.get("tag") or ent.get("name") or "").strip(),
                    "user_id": ent.get("user_id"),
                    "team": (ent.get("team") or "").strip()}
        return {"tag": (getattr(ent, "name", "") or "").strip(),
                "user_id": getattr(ent, "user_id", None),
                "team": (getattr(ent, "team", "") or "").strip()}

    def resolve(f):
        uid = f.get("user_id")
        if uid is not None:
            pid = assignments.get("u:" + str(uid))
            if pid:
                return pid
        return by_name.get((f.get("tag") or "").strip().lower())

    # Scope + ranking settings
    scope_type = body.get("scope_type", "all")
    scope_value = body.get("scope_value", "")
    curve = body.get("curve", "standard")
    decay_mode = body.get("decay_mode", "none")
    try:
        threshold = int(body.get("threshold", 2))
    except (TypeError, ValueError):
        threshold = 2
    try:
        recency_factor = float(body.get("recency_factor", 0.85))
    except (TypeError, ValueError):
        recency_factor = 0.85

    events = _scoped_events(scope_type, scope_value)

    # Split entrants into matched / unmatched
    matched = {}       # player_id -> entrant fields (first wins if dup)
    unmatched = []
    for ent in (entrants or []):
        f = ent_fields(ent)
        if not f["tag"]:
            continue
        pid = resolve(f)
        if pid:
            if pid not in matched:
                matched[pid] = f
        else:
            unmatched.append(f)

    # Rank the matched players; separate those with no history in scope
    ranked_raw = SeedingRank.rank_players(list(matched.keys()), events,
                                          curve=curve, decay_mode=decay_mode,
                                          threshold=threshold, recency_factor=recency_factor)
    ranked = []
    known_unranked = []
    for r in ranked_raw:
        pid = r["player_id"]
        name = players.get(pid, {}).get("name", pid)
        tag = matched[pid].get("tag", "")
        row = {"player_id": pid, "name": name, "tag": tag,
               "points": r["points"], "events_counted": r["events_counted"],
               "placements": r["placements"]}
        if r["events_counted"] > 0:
            ranked.append(row)
        else:
            known_unranked.append(row)

    # Coverage hint for absence decay: how many events are in scope.
    coverage = {"events_in_scope": len(events),
                "scope_type": scope_type, "scope_value": scope_value}

    # Rematch detection: predict likely early-bracket rematches from history.
    # The seed order the TO would enter is ranked (best-first) then the known
    # -but-unranked players, so we detect against that combined order.
    rematch_flags = []
    pair_history = []
    state_flags = []
    city_flags = []
    state_lookup = {}
    city_lookup = {}
    state_id_lookup = {}
    try:
        # check_mode: 'rematch' | 'state' | 'both' | 'off'. (Back-compat: the
        # old rematch_check bool still turns rematch on if check_mode absent.)
        check_mode = body.get("check_mode")
        if check_mode is None:
            check_mode = "rematch" if body.get("rematch_check", True) else "off"
        do_rematch = check_mode in ("rematch", "both", "all", "rematch_state", "rematch_city")
        do_state = check_mode in ("state", "both", "all", "rematch_state")
        do_city = check_mode in ("city", "all", "rematch_city")
        try:
            early_rounds = int(body.get("early_rounds", 2))
        except (TypeError, ValueError):
            early_rounds = 2
        seed_order = ranked + known_unranked   # full entry order

        if do_rematch and early_rounds > 0:
            try:
                rematch_recency = float(body.get("rematch_recency", 0.8))
            except (TypeError, ValueError):
                rematch_recency = 0.8
            try:
                lookback = int(body.get("rematch_lookback", 0))
            except (TypeError, ValueError):
                lookback = 0
            rematch_flags = SeedingRank.detect_rematches(
                seed_order, events, early_rounds=early_rounds,
                recency_factor=rematch_recency, lookback=lookback)

        if do_state and early_rounds > 0:
            # attach each seeded player's state from the DB for detection
            for row in seed_order:
                pid = row.get("player_id")
                if pid:
                    row["state"] = players.get(pid, {}).get("state", "")
            state_flags = SeedingRank.detect_state_clashes(seed_order, early_rounds=early_rounds)

        if do_city and early_rounds > 0:
            # city needs state/state_id too (cross-state same-name exclusion)
            for row in seed_order:
                pid = row.get("player_id")
                if pid:
                    prec = players.get(pid, {})
                    row["city"] = prec.get("city", "")
                    row["state"] = prec.get("state", "")
                    row["state_id"] = prec.get("state_id")
            city_flags = SeedingRank.detect_city_clashes(seed_order, early_rounds=early_rounds)

        # Always expose raw pair history + player states so the client can
        # recompute BOTH checks instantly on a drag-reorder, no server round-trip.
        _ordered_ev = SeedingRank._event_order(events)
        _seed_ids = [r.get("player_id") for r in seed_order if r.get("player_id")]
        _pm = SeedingRank.prior_meetings(_seed_ids, _ordered_ev)
        name_lookup = {}
        state_lookup = {}
        for r in seed_order:
            if r.get("player_id"):
                name_lookup[r["player_id"]] = r.get("name", r["player_id"])
                state_lookup[r["player_id"]] = players.get(r["player_id"], {}).get("state", "")
                city_lookup[r["player_id"]] = players.get(r["player_id"], {}).get("city", "")
                state_id_lookup[r["player_id"]] = players.get(r["player_id"], {}).get("state_id")
        pair_history = [{"a_id": a, "b_id": b,
                         "a_name": name_lookup.get(a, a), "b_name": name_lookup.get(b, b),
                         "events_ago": info["events_ago"], "label": info["label"],
                         "date": info["date"], "count": info["count"]}
                        for (a, b), info in _pm.items()]
    except Exception as e:
        print("seedingCompute detection error: %s" % e)
        rematch_flags = []
        state_flags = []
        city_flags = []

    return jsonify({
        "ok": True,
        "ranked": ranked,                 # already sorted best-first
        "known_unranked": known_unranked, # matched but no scoped history
        "unmatched": unmatched,           # need reconcile
        "coverage": coverage,
        "entrant_count": len(entrants or []),
        "rematches": rematch_flags,       # likely early-bracket rematches
        "state_clashes": state_flags,     # same-state early meetings
        "pair_history": pair_history,      # raw prior meetings, for live re-check on reorder
        "player_states": state_lookup,    # pid -> state, for live re-check
        "city_clashes": city_flags,       # same-city early meetings
        "player_cities": city_lookup,     # pid -> city, for live re-check
        "player_state_ids": state_id_lookup,  # pid -> stateId (city cross-state rule)
    }), 200


@api.route('/seedingReconcile', methods=['POST'])
def seeding_reconcile():
    """Match a tournament entrant to a local player (existing or new),
    purely by aliasing -- no event involved.

    Body: { tag, user_id (optional), action: 'existing'|'new',
            player_id (for existing) }
    Records the tag (and 'sgg:<user_id>') as aliases so the entrant
    resolves from now on (in seeding AND imports). Returns the player_id."""
    body = request.get_json() or {}
    tag = (body.get("tag") or "").strip()
    user_id = body.get("user_id")
    action = body.get("action")
    if not tag or action not in ("existing", "new"):
        return jsonify({"ok": False, "message": "Missing tag or action"}), 400

    players = players_db.get_local_players()
    new_aliases = [tag]
    if user_id:
        new_aliases.append("sgg:" + str(user_id))

    if action == "existing":
        pid = body.get("player_id", "")
        if pid not in players:
            return jsonify({"ok": False, "message": "Unknown player_id"}), 400
        existing = set(a.lower() for a in players[pid].get("aliases", []))
        for a in new_aliases:
            if a.lower() != players[pid]["name"].lower() and a.lower() not in existing:
                players[pid].setdefault("aliases", []).append(a)
                existing.add(a.lower())
    else:  # new
        pid = _next_player_id(players)
        # Point 4: if the caller passed start.gg location for this entrant,
        # save it onto the freshly created profile.
        loc_state = (body.get("state") or "").strip()
        loc_state_id = body.get("state_id")
        loc_city = (body.get("city") or "").strip()
        loc_country = (body.get("country") or "").strip().upper()
        players[pid] = {"id": pid, "name": tag, "team": "", "country": loc_country,
                        "state": loc_state, "state_id": loc_state_id, "city": loc_city,
                        "social_handle": "", "social_platform": "",
                        "is_commentator": False, "characters": {}, "roster": {},
                        "aliases": [a for a in new_aliases if a.lower() != tag.lower()]}
    players_db.save_local_players(players)
    return jsonify({"ok": True, "player_id": pid}), 200


@api.route('/locationReview', methods=['POST'])
def location_review():
    """Pull entrant locations from start.gg and build a review list.

    Body: { "slug": "<url or slug>" }
    Fetches the tournament's entrants (which now include state/stateId/city),
    resolves each to a local player the same way seeding does, and returns a
    review list (fills, conflicts, non-standard values) for the TO to confirm
    or edit before anything is written. Nothing is saved here."""
    body = request.get_json() or {}
    tournament, event = _parse_event_slug(body.get("slug", ""), "startgg")
    if not tournament or not event:
        return jsonify({"ok": False, "message": "Could not parse an event slug from that input"}), 400
    try:
        entrants = startgg_client.get_all_players_from_tournament(tournament, event)
    except Exception as e:
        print("locationReview entrant fetch error: %s" % e)
        return jsonify({"ok": False, "message": "Could not fetch entrants: %s" % e}), 502

    players = players_db.get_local_players()
    assignments, by_name = _build_assignments(players)

    def resolve(uid, tag):
        if uid is not None:
            pid = assignments.get("u:" + str(uid))
            if pid:
                return pid
        return by_name.get((tag or "").strip().lower())

    # Build the entrant-location list the resolver expects.
    ent_locs = []
    for ent in (entrants or []):
        tag = (getattr(ent, "name", "") or "").strip()
        uid = getattr(ent, "user_id", None)
        pid = resolve(uid, tag)
        ent_locs.append({
            "player_id": pid,
            "tag": tag,
            "user_id": uid,
            "state": getattr(ent, "state", "") or "",
            "state_id": getattr(ent, "state_id", None),
            "city": getattr(ent, "city", "") or "",
            "country": getattr(ent, "location_country", "") or "",
        })

    review = LocationResolve.build_review(
        ent_locs, lambda pid: players.get(pid) if pid else None)
    # carry user_id onto review rows (for reconcile-create-new from the UI)
    uid_by_tag = {e["tag"]: e["user_id"] for e in ent_locs}
    for r in review:
        r["user_id"] = uid_by_tag.get(r["tag"])
    flagged = sum(1 for r in review if r.get("is_flagged"))
    with_location = sum(1 for e in ent_locs
                        if e.get("state") or e.get("state_id") is not None or e.get("country"))
    return jsonify({"ok": True, "review": review,
                    "total_entrants": len(entrants or []),
                    "with_location": with_location,
                    "needs_review": len(review), "flagged": flagged}), 200


@api.route('/applyLocations', methods=['POST'])
def apply_locations():
    """Write the TO-approved location values onto local profiles.

    Body: { "updates": [ {player_id, state, state_id, city}, ... ] }
    Only the rows the TO approved/edited are sent. Location fields are the
    only thing changed; everything else on the profile is preserved. Rows
    with no player_id are ignored (those go through reconcile create-new)."""
    body = request.get_json() or {}
    updates = body.get("updates") or []
    players = players_db.get_local_players()
    applied = 0
    for u in updates:
        pid = u.get("player_id")
        if not pid or pid not in players:
            continue
        if "state" in u:
            players[pid]["state"] = (u.get("state") or "").strip()
        if "state_id" in u:
            players[pid]["state_id"] = u.get("state_id")
        if "city" in u:
            players[pid]["city"] = (u.get("city") or "").strip()
        if "country" in u:
            players[pid]["country"] = (u.get("country") or "").strip().upper()
        applied += 1
    if applied:
        players_db.save_local_players(players)
    return jsonify({"ok": True, "applied": applied}), 200


@api.route('/setEventGame', methods=['POST'])
def set_event_game():
    """Assign/clear an event's game tag.

    Body: { "event_slug": "...", "game": "ssf2x" }"""
    body = request.get_json() or {}
    event_slug = body.get("event_slug", "")
    if not event_slug:
        return jsonify({"ok": False, "message": "event_slug required"}), 400
    ok = MatchHistory.set_event_game(event_slug, body.get("game", ""))
    MatchHistory.rebuild_alltime(_alias_map_for_rollup())
    return jsonify({"ok": ok}), (200 if ok else 404)


@api.route('/setEventDisplayName', methods=['POST'])
def set_event_display_name():
    """Set/clear an event's custom display name.

    Body: { "event_slug": "...", "display_name": "Texas Showdown 2026" }"""
    body = request.get_json() or {}
    event_slug = body.get("event_slug", "")
    if not event_slug:
        return jsonify({"ok": False, "message": "event_slug required"}), 400
    ok = MatchHistory.set_event_display_name(event_slug, body.get("display_name", ""))
    return jsonify({"ok": ok}), (200 if ok else 404)


@api.route('/setEventSeries', methods=['POST'])
def set_event_series():
    """Assign/clear an event's series tag.

    Body: { "event_slug": "...", "series": "STunday" }"""
    body = request.get_json() or {}
    event_slug = body.get("event_slug", "")
    if not event_slug:
        return jsonify({"ok": False, "message": "event_slug required"}), 400
    ok = MatchHistory.set_event_series(event_slug, body.get("series", ""))
    return jsonify({"ok": ok}), (200 if ok else 404)


@api.route('/getMatchupHistory', methods=['GET'])
def get_matchup_history():
    """H2H record between two players.

    Query: ?p1=<id>&p2=<id>&event=<slug optional>
    Returns all-time record always, plus event record when event given."""
    p1 = request.args.get("p1", "")
    p2 = request.args.get("p2", "")
    if not p1 or not p2:
        return jsonify({"ok": False, "message": "p1 and p2 required"}), 400
    game = request.args.get("game", "")  # filter all records to this game
    aw, al = MatchHistory.alltime_record(p1, p2, game)
    out = {"ok": True, "alltime": {"wins": aw, "losses": al}}
    series = request.args.get("series")
    if series:
        sw, sl = MatchHistory.series_record(series, p1, p2, game=game)
        out["series"] = {"wins": sw, "losses": sl, "name": series}
    event_slug = request.args.get("event")
    if event_slug:
        ew, el = MatchHistory.event_record(event_slug, p1, p2, game=game)
        out["event"] = {
            "wins": ew, "losses": el, "event_slug": event_slug,
            "p1_placement": MatchHistory.event_placement(event_slug, p1),
            "p2_placement": MatchHistory.event_placement(event_slug, p2),
        }
    return jsonify(out), 200


@api.route('/purgeAllPlayers', methods=['POST'])
def purge_all_players():
    """Delete the ENTIRE local player database (players, characters,
    rosters, aliases). Match history event files are left intact.

    Guarded: the body must contain {"confirm": "DELETE"} exactly, so it
    cannot fire by accident. Returns how many players were removed."""
    body = request.get_json() or {}
    if body.get("confirm") != "DELETE":
        return jsonify({"ok": False, "message": "Confirmation required."}), 400
    try:
        removed = players_db.purge_all_players()
    except Exception as e:
        print(f"purgeAllPlayers error: {e}")
        return jsonify({"ok": False, "message": str(e)}), 500
    return jsonify({"ok": True, "removed": removed}), 200


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
    """Players flagged as commentators in their profile."""
    players = _read_local_players()
    result = {p["name"]: {"name": p["name"], "soc": p.get("social_handle", "")}
              for p in players.values() if p.get("is_commentator")}
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
        # Multi-slot character arrays (the current char system). These MUST be
        # persisted here too, or clearing them on a player swap never reaches
        # the overlay and the previous player's characters linger.
        temp["p1Characters"]     = json_data.get("p1Characters",     [])
        temp["p2Characters"]     = json_data.get("p2Characters",     [])
        temp["p1NextCharacters"] = json_data.get("p1NextCharacters", [])
        temp["p2NextCharacters"] = json_data.get("p2NextCharacters", [])
        # Head-to-head fields (drive the H2H overlays)
        temp["h2hVisible"]            = json_data.get("h2hVisible", False)
        temp["h2hScope"]              = json_data.get("h2hScope", "alltime")
        temp["h2hEventName"]          = json_data.get("h2hEventName", "")
        temp["h2hSeriesName"]         = json_data.get("h2hSeriesName", "")
        temp["p1MatchupWins"]         = json_data.get("p1MatchupWins", "")
        temp["p1MatchupLosses"]       = json_data.get("p1MatchupLosses", "")
        temp["p2MatchupWins"]         = json_data.get("p2MatchupWins", "")
        temp["p2MatchupLosses"]       = json_data.get("p2MatchupLosses", "")
        temp["p1EventPlacement"]      = json_data.get("p1EventPlacement", "")
        temp["p2EventPlacement"]      = json_data.get("p2EventPlacement", "")
        temp["p1EventPlacementText"]  = json_data.get("p1EventPlacementText", "")
        temp["p2EventPlacementText"]  = json_data.get("p2EventPlacementText", "")
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
        api.run(host=server_ip, port=server_port, threaded=True)
    except KeyboardInterrupt:
        pass