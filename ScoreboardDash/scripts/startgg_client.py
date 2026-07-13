import requests
import json
from io import open
import math
from scripts import PlayerStats

root_dir = ""
country_prop_file = root_dir + "resources/country_map.properties"
token_file = root_dir + "../data/startgg_token.txt"
start_gg_file = root_dir + "../data/startgg_info.txt"
url = 'https://api.start.gg/gql/alpha'
player_stats = PlayerStats
entrants_per_page = 25
max_seed = 8
use_highest_phase = True


def read_file(file_name, default):
    try:
        with open(file_name) as json_file:
            content = json_file.read()
            if not content.strip():
                return default
            return json.loads(content)
    except Exception:
        return default


country_code_map = read_file(country_prop_file, "{}")


def get_api_data(response):
    try:
        response_json = response.json()
    except Exception:
        print("start.gg non-JSON response (HTTP %s): %s" % (getattr(response, "status_code", "?"), getattr(response, "text", "")[:500]))
        return None
    errors = response_json.get("errors")
    if errors:
        print("start.gg API error: " + str(errors))
        # Also surface any partial data path so the offending field is clear
        return None
    return response_json.get("data")


class Match:
    def __init__(self, player1, player2, set_id):
        self.player1 = player1
        self.player2 = player2
        self.set_id = set_id

    def already_played(self, previous_matches_map):
        opponent = previous_matches_map.get(self.player1.name)
        if opponent and opponent == self.player2.name:
            return True
        opponent = previous_matches_map.get(self.player2.name)
        return opponent and opponent == self.player1.name

    def contains_players(self, name1, name2):
        return self.player1.name == name1 or self.player1.name == name2 \
               or self.player2.name == name1 or self.player2.name == name2

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)


class Player:
    def __init__(self, name, entrant_id, team, country, seed,
                 state="", state_id=None, city="", user_id=None):
        self.name = name
        self.team = team
        self.entrant_id = entrant_id
        self.country = country
        self.seed = seed
        self.state = state            # start.gg location.state (text, may be blank)
        self.state_id = state_id      # start.gg location.stateId (canonical int)
        self.city = city              # start.gg location.city (text, may be blank)
        self.user_id = user_id        # start.gg user id (for durable resolution)


def get_token():
    with open(token_file, 'r') as file:
        return file.readline()


def get_events(tournament_name):
    token = get_token()
    query = '''
        query TournamentEvents($tourneySlug:String!) {
          tournament(slug: $tourneySlug) {
            id
            name
            events {
              id
              name
            }
          }
        }
        '''
    variables = {
        "tourneySlug": tournament_name
    }

    headers = {
        'Authorization': 'Bearer ' + token
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    data = get_api_data(response)
    if data is None:
        return "[]"
    events = data["tournament"]["events"]
    if events is None or len(events) == 0:
        print("No events found in start.gg for tournament: " + tournament_name)
        return "[]"
    events_list = []
    for event in events:
        event_name = event["name"]
        if event_name is not None and event_name.strip() != "":
            events_list.append(event_name)
    return json.dumps(events_list)


def get_event_start_at(tournament_name, event_name):
    """Return the event's scheduled start as a Unix timestamp (int), or None.

    Falls back to the tournament's startAt if the event has none. Used to stamp
    imported events with their real date instead of the import time."""
    token = get_token()
    query = '''
            query EventStart($eventSlug:String!) {
              event(slug: $eventSlug) {
                startAt
                tournament { startAt }
              }
            }
        '''
    variables = {"eventSlug": "tournament/" + tournament_name + "/event/" + event_name}
    headers = {'Authorization': 'Bearer ' + token}
    try:
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        data = get_api_data(response)
        if not data or not data.get("event"):
            return None
        ev = data["event"]
        if ev.get("startAt"):
            return ev["startAt"]
        t = ev.get("tournament") or {}
        return t.get("startAt")
    except Exception as e:
        print("get_event_start_at error: %s" % e)
        return None


def get_num_entrants_for_event(tournament_name, event_name):
    token = get_token()
    query = '''
            query EventEntrants($eventSlug:String!) {
              event(slug: $eventSlug) {
                numEntrants
              }
            }
        '''
    variables = {
        "eventSlug": "tournament/" + tournament_name + "/event/" + event_name,
    }

    headers = {
        'Authorization': 'Bearer ' + token
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    data = get_api_data(response)
    if data is None:
        return 0
    return data["event"]["numEntrants"]


def get_top_8_entrants(tournament_name, event_name, page):
    global entrants_per_page
    token = get_token()
    query = '''
            query EventEntrants($eventSlug:String!, $page: Int!, $perPage: Int!) {
              event(slug: $eventSlug) {
                name
                entrants(query: {
                  page: $page
                  perPage: $perPage
                }) {
                  nodes {
                    standing {
                      placement
                    }
                    participants {
                      gamerTag
                    }
                  }
                }
              }
            }
        '''
    variables = {
        "eventSlug": "tournament/" + tournament_name + "/event/" + event_name,
        "page": page,
        "perPage": entrants_per_page
    }

    headers = {
        'Authorization': 'Bearer ' + token
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    data = get_api_data(response)
    if data is None:
        return {}
    entrants = data["event"]["entrants"]["nodes"]
    if entrants is None or len(entrants) == 0:
        print("No entrants found for event: " + event_name + " in start.gg for tournament: " + tournament_name)
        return {}
    entrants_map = {}
    entrant_count = 0
    for entrant in entrants:
        entrant_count = entrant_count + 1
        placement = entrant["standing"]["placement"]
        if placement <= 8:
            gamer_tag = entrant["participants"][0]["gamerTag"]
            if gamer_tag is not None and gamer_tag.strip() != "":
                entrants_map[gamer_tag] = {event_name: PlayerStats.EventData(placement, 0, 0)}
    return entrants_map


def get_next_players(current_player1, current_player2, previous_matches_map):
    startgg_info = get_start_gg_info()
    if startgg_info is None:
        print("No tournament information found, returning empty")
        return []
    tournament = startgg_info["tournament"]
    stream = startgg_info["stream"]
    print("Tournament: " + tournament + " stream: " + stream)
    return get_next_players_from_tournament(tournament, stream, current_player1, current_player2, previous_matches_map)


def get_next_players_from_tournament(tournament_name, stream_name, current_player1, current_player2, previous_matches_map):
    token = get_token()
    query = '''
    query StreamQueueOnTournament($tourneySlug: String!) {
      tournament(slug: $tourneySlug) {
        id
        streamQueue {
          stream {
            streamSource
            streamName
          }
          sets {
            id,
            event {
              name
            },
            slots {
                entrant {
                    id
                    name
                    team {
                        name
                    }
                    participants {                      
                        gamerTag,
                        user {
                            location {
                                country
                            }
                        }
                    },
                    seeds {
                      phase {
                        phaseOrder
                      },
                      seedNum                    
                    }                    
                }
            }
          }
        }
      }
    }
    '''
    slug = "tournament/" + tournament_name
    variables = {
        "tourneySlug": slug
    }

    headers = {
        'Authorization': 'Bearer ' + token
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    data = get_api_data(response)
    if data is None:
        return json.dumps([])
    print(data)
    matches = []
    stream_queue = data["tournament"]["streamQueue"]
    if stream_queue is not None and len(stream_queue) > 0:
        for stream in stream_queue:
            if stream['stream']['streamName'] == stream_name:
                print("Found stream queue data for: " + stream_name)
                sets = stream["sets"]
                for s in sets:
                    set_id = s["id"]
                    slots = s["slots"]
                    event_name = s["event"]["name"]
                    if slots is not None and len(slots) == 2:
                        match = Match(create_player(slots[0]), create_player(slots[1]), set_id)
                        if not match.contains_players(current_player1, current_player2) and not match.already_played(previous_matches_map):
                            matches.append(match.to_json())
    json_dicts = [json.loads(match) for match in matches]
    return json.dumps(json_dicts, indent=4)


def report_winner(set_id, winner_id, loser_id, entrant_1_score, entrant_2_score):
    token = get_token()
    query = '''
        mutation reportSet($setId: ID!, $winnerId: ID!, $gameData: [BracketSetGameDataInput]) {
          reportBracketSet(setId: $setId, winnerId: $winnerId, gameData: $gameData) {
            id
            state
          }
        }
    '''
    variables = {
        "setId": set_id,
        "winnerId": winner_id,
        "gameData": create_results_data(winner_id, loser_id, int(entrant_1_score), int(entrant_2_score))
    }
    headers = {
        'Authorization': 'Bearer ' + token
    }

    try:
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        response_json = response.json()
        print(response_json)
    except Exception as e:
        print("Failed to report score!", e)
        return False
    return True


def get_players_from_tournament(tournament_name, event_name, page):
    global entrants_per_page
    token = get_token()
    query = '''
            query EventEntrants($eventSlug:String!, $page: Int!, $perPage: Int!) {
              event(slug: $eventSlug) {
                name
                entrants(query: {
                  page: $page
                  perPage: $perPage
                }) {
                  nodes {
                    id,
                    participants {
                      gamerTag,
                      prefix,
                      user {
                        id
                        location {
                          country
                          state
                          stateId
                          city
                        }
                      }
                    },
                    seeds {
                      phase {
                        phaseOrder
                      },
                      seedNum                        
                    }
                  }
                }
              }
            }
        '''
    variables = {
        "eventSlug": "tournament/" + tournament_name + "/event/" + event_name,
        "page": page,
        "perPage": entrants_per_page
    }

    headers = {
        'Authorization': 'Bearer ' + token
    }

    response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    data = get_api_data(response)
    if data is None:
        return []
    entrants = data["event"]["entrants"]["nodes"]
    event_name = data["event"]["name"]
    if entrants is None or len(entrants) == 0:
        print("No entrants found for event: " + event_name + " in start.gg for tournament: " + tournament_name)
        return []
    entrants_list = []
    for entrant in entrants:
        entrant_id = entrant["id"]
        gamer_tag = entrant["participants"][0]["gamerTag"]
        team = entrant["participants"][0]["prefix"]
        country = get_country(entrant["participants"][0])
        loc = get_location(entrant["participants"][0])
        seed = get_seed(entrant["seeds"])
        entrants_list.append(Player(gamer_tag, entrant_id, team or "", country, seed,
                                    state=loc["state"], state_id=loc["state_id"],
                                    city=loc["city"], user_id=loc["user_id"]))
    return entrants_list


def create_results_data(winner_id, loser_id, entrant_1_score, entrant_2_score):
    games = []
    game_num = 1
    id_1 = winner_id
    id_2 = loser_id
    if entrant_2_score > entrant_1_score:
        id_1 = loser_id
        id_2 = winner_id
    total_games = max(entrant_1_score, entrant_2_score) + 1
    for counter in range(1, total_games):
        if entrant_1_score > 0:
            game = {
                "winnerId": id_1,
                "gameNum": game_num,
                "entrant1Score": 1,
                "entrant2Score": 0
            }
            games.append(game)
            game_num = game_num + 1
            entrant_1_score = entrant_1_score - 1
        if entrant_2_score > 0:
            game = {
                "winnerId": id_2,
                "gameNum": game_num,
                "entrant1Score": 0,
                "entrant2Score": 1
            }
            games.append(game)
            game_num = game_num + 1
            entrant_2_score = entrant_2_score - 1
    return games


def create_player(slot):
    if slot["entrant"] is None or slot["entrant"]["name"] is None or slot["entrant"]["name"].strip() == "":
        return Player("TBD", "TBD", "", "US", "")

    name = slot["entrant"]["name"]
    team = ""
    if " | " in name:
        team, name = slot["entrant"]["name"].split(" | ", 1)
    country_code = get_country(slot["entrant"]["participants"][0])
    entrant_id = slot["entrant"]["id"]
    seed = get_seed(slot["entrant"]["seeds"])
    return Player(name, entrant_id, team, country_code, seed)


def get_seed(seeds):
    global max_seed, use_highest_phase
    # Only grab the seed of the first phase
    current_phase_order = 0
    seed_result = ""
    for seed in seeds:
        phase_order = seed["phase"]["phaseOrder"]
        if use_highest_phase:
            if phase_order > current_phase_order:
                seed_num = seed["seedNum"]
                current_phase_order = phase_order
                if seed_num <= max_seed:
                    seed_result = str(seed_num)
        elif phase_order == 1:
            seed_num = seed["seedNum"]
            if seed_num > max_seed:
                return ""
            return str(seed_num)
    return seed_result


def get_country(participant):
    user = participant.get("user") if isinstance(participant, dict) else None
    country_code = "US"
    if user:
        location = user.get("location") if isinstance(user, dict) else None
        if location:
            country = location.get("country")
            if country:
                country_code = country_code_map.get(country)
                if country_code is None:
                    # Couldn't find the country code from country code map, default back to US
                    print("Couldn't find country code for country: " + country)
                    country_code = "US"
    return country_code


def get_location(participant):
    """Return {state, state_id, city, user_id} from a participant's start.gg
    profile location. All may be blank/None (profile privacy or unset)."""
    out = {"state": "", "state_id": None, "city": "", "user_id": None}
    user = participant.get("user") if isinstance(participant, dict) else None
    if isinstance(user, dict):
        out["user_id"] = user.get("id")
        location = user.get("location")
        if isinstance(location, dict):
            out["state"] = (location.get("state") or "").strip()
            out["state_id"] = location.get("stateId")
            out["city"] = (location.get("city") or "").strip()
    return out


def save_start_gg_info(data):
    try:
        with open(start_gg_file, 'a+'):
            pass
    finally:
        pass
    with open(start_gg_file, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(data))


def get_start_gg_info():
    try:
        with open(start_gg_file, 'a+'):
            pass
    finally:
        pass

    return read_file(start_gg_file, "{\"tournament\":\"\",\"event\":\"\",\"stream\":\"\"}")


def get_top_8_entrants_for_event(tournament_name, event_name):
    pages = math.ceil(get_num_entrants_for_event(tournament_name, event_name) / entrants_per_page)
    entrants = {}
    for page in range(1, pages + 1):
        entrants.update(get_top_8_entrants(tournament_name, event_name, page))
    return entrants


def get_all_players_from_tournament(tournament_name, event_name):
    pages = math.ceil(get_num_entrants_for_event(tournament_name, event_name) / entrants_per_page)
    entrants = []
    for page in range(1, pages + 1):
        entrants += get_players_from_tournament(tournament_name, event_name, page)
    return entrants


def _entrant_from_slot(slot):
    """Pull (tag, team, entrant_id, user_id, country) from a set slot.

    user_id is the stable start.gg account id (survives tag changes);
    None for entrants with no linked account. entrant_id is per-event."""
    entrant = slot.get("entrant") if slot else None
    if not entrant:
        return None
    name = entrant.get("name") or ""
    team = ""
    if " | " in name:
        team, name = name.split(" | ", 1)
    parts = entrant.get("participants") or [{}]
    p0 = parts[0] if parts else {}
    if not team:
        team = p0.get("prefix") or ""
    tag = p0.get("gamerTag") or name
    user = p0.get("user") or {}
    user_id = user.get("id")
    country = get_country(p0) if p0 else "US"
    return {
        "tag": tag.strip(),
        "team": (team or "").strip(),
        "entrant_id": entrant.get("id"),
        "user_id": user_id,
        "country": country,
    }


def _parse_display_score(display_score, tag1, tag2):
    """Best-effort score parse from start.gg displayScore.

    displayScore looks like 'Owls 3 - Bas 1' (or 'DQ'/None). Returns
    (score1, score2) aligned to (tag1, tag2), or (None, None) if it
    can't be parsed. The per-slot standing scores are preferred when
    available; this is the fallback."""
    if not display_score or display_score in ("DQ", "0 - 0"):
        return None, None
    import re as _re
    nums = _re.findall(r"-?\d+", display_score)
    if len(nums) < 2:
        return None, None
    # Assume 'tag1 N - tag2 M' ordering as start.gg emits slots in order
    return int(nums[-2]), int(nums[-1])


# Full set query (rich fields) and a minimal fallback that only uses
# fields from start.gg's official "Sets in Event" example. If the full
# query is rejected, we retry minimal so the import still succeeds.
_SETS_QUERY_FULL = '''
    query EventSets($eventSlug: String!, $page: Int!, $perPage: Int!) {
      event(slug: $eventSlug) {
        name
        tournament { name }
        sets(page: $page, perPage: $perPage) {
          pageInfo { total }
          nodes {
            id
            state
            completedAt
            round
            fullRoundText
            displayScore
            winnerId
            slots {
              standing { stats { score { value } } }
              entrant {
                id
                name
                participants { gamerTag prefix user { id location { country } } }
              }
            }
          }
        }
      }
    }
    '''

_SETS_QUERY_MIN = '''
    query EventSets($eventSlug: String!, $page: Int!, $perPage: Int!) {
      event(slug: $eventSlug) {
        name
        sets(page: $page, perPage: $perPage) {
          pageInfo { total }
          nodes {
            id
            winnerId
            displayScore
            fullRoundText
            slots {
              entrant {
                id
                name
                participants { gamerTag prefix }
              }
            }
          }
        }
      }
    }
    '''


def get_completed_sets(tournament_name, event_name, per_page=40, max_pages=50):
    """Fetch all completed sets for an event.

    Tries a rich query first; if start.gg rejects it, retries with a
    minimal query built only from documented-safe fields, so the import
    still works (scores then come from displayScore parsing). Sets
    without exactly two entrants, or with no winner, are skipped."""
    token = get_token()
    event_slug = "tournament/" + tournament_name + "/event/" + event_name
    headers = {"Authorization": "Bearer " + token}

    # Probe page 1 with the full query; on error, drop to minimal.
    query = _SETS_QUERY_FULL
    probe = requests.post(url, json={"query": query, "variables":
            {"eventSlug": event_slug, "page": 1, "perPage": per_page}}, headers=headers)
    pj = {}
    try:
        pj = probe.json()
    except Exception:
        pass
    if pj.get("errors"):
        print("start.gg full set query rejected (" + str(pj["errors"])[:160]
              + ") -- retrying with minimal query")
        query = _SETS_QUERY_MIN
    results = []
    page = 1
    total_pages = 1
    while page <= total_pages and page <= max_pages:
        variables = {"eventSlug": event_slug, "page": page, "perPage": per_page}
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        data = get_api_data(response)
        if data is None or not data.get("event"):
            break
        event = data["event"]
        ev_name = event.get("name") or event_name
        tourn = (event.get("tournament") or {}).get("name") or tournament_name
        sets_block = event.get("sets") or {}
        page_info = sets_block.get("pageInfo") or {}
        total_count = page_info.get("total") or 0
        total_pages = max(1, math.ceil(total_count / per_page))
        nodes = sets_block.get("nodes") or []
        if not nodes:
            break
        for node in nodes:
            # Only completed sets (state 3); skip in-progress/pending
            if node.get("state") not in (3, None):
                continue
            slots = node.get("slots") or []
            if len(slots) != 2:
                continue
            # A real completed set has a winner
            if node.get("winnerId") is None:
                continue
            e1 = _entrant_from_slot(slots[0])
            e2 = _entrant_from_slot(slots[1])
            if not e1 or not e2:
                continue
            # Structured score first
            def _slot_score(slot):
                st = (slot.get("standing") or {}).get("stats") or {}
                sc = (st.get("score") or {})
                return sc.get("value")
            s1 = _slot_score(slots[0])
            s2 = _slot_score(slots[1])
            if s1 is None or s2 is None:
                s1, s2 = _parse_display_score(node.get("displayScore"), e1["tag"], e2["tag"])
            # start.gg marks a DQ with a -1 score on the DQ'd slot (and the
            # displayScore reads "DQ" when slot scores are absent). A DQ'd
            # "set" was never actually played, so recording it would poison
            # H2H records, rematch detection, and seeding points. Skip it.
            if ((s1 is not None and int(s1) < 0) or
                    (s2 is not None and int(s2) < 0) or
                    (node.get("displayScore") or "").strip().upper() == "DQ"):
                continue
            winner_id = node.get("winnerId")
            winner_user_id = None
            winner_entrant_id = winner_id
            if winner_id == e1["entrant_id"]:
                winner_user_id = e1["user_id"]
            elif winner_id == e2["entrant_id"]:
                winner_user_id = e2["user_id"]
            results.append({
                "set_id": str(node.get("id")),
                "round_name": node.get("fullRoundText") or "",
                "round": node.get("round"),
                "full_round_text": node.get("fullRoundText") or "",
                "event_name": ev_name,
                "tournament_name": tourn,
                "completed_at": node.get("completedAt"),
                "p1": e1,
                "p2": e2,
                "p1_score": int(s1) if s1 is not None else None,
                "p2_score": int(s2) if s2 is not None else None,
                "winner_entrant_id": winner_entrant_id,
                "winner_user_id": winner_user_id,
            })
        page += 1
    return results


def get_event_standings(tournament_name, event_name, per_page=64, max_pages=20):
    """Final placements for an event, keyed for player matching.

    Returns a list of dicts:
      { placement, tag, team, user_id, entrant_id }
    Placement is the start.gg final standing (1 = winner). Paged the
    same way as sets. Safe to call right after get_completed_sets --
    it is a separate lightweight query on the same event node."""
    token = get_token()
    query = '''
    query EventStandings($eventSlug: String!, $page: Int!, $perPage: Int!) {
      event(slug: $eventSlug) {
        standings(query: { page: $page, perPage: $perPage }) {
          nodes {
            placement
            entrant {
              id
              name
              participants {
                gamerTag
                prefix
                user { id }
              }
            }
          }
        }
      }
    }
    '''
    event_slug = "tournament/" + tournament_name + "/event/" + event_name
    headers = {"Authorization": "Bearer " + token}
    out = []
    page = 1
    while page <= max_pages:
        variables = {"eventSlug": event_slug, "page": page, "perPage": per_page}
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        data = get_api_data(response)
        if data is None or not data.get("event"):
            break
        block = (data["event"].get("standings") or {})
        nodes = block.get("nodes") or []
        if not nodes:
            break
        for node in nodes:
            entrant = node.get("entrant") or {}
            parts = entrant.get("participants") or [{}]
            p0 = parts[0] if parts else {}
            name = entrant.get("name") or ""
            team = ""
            if " | " in name:
                team, name = name.split(" | ", 1)
            if not team:
                team = p0.get("prefix") or ""
            tag = p0.get("gamerTag") or name
            user = p0.get("user") or {}
            out.append({
                "placement": node.get("placement"),
                "tag": (tag or "").strip(),
                "team": (team or "").strip(),
                "user_id": user.get("id"),
                "entrant_id": entrant.get("id"),
            })
        page += 1
    return out


if __name__ == "__main__":
    # result = get_top_8_entrants_for_event("texas-showdown-2024", "super-street-fighter-ii-turbo")
    # print(result)
    # player_stats.write_to_file(result)
    # cache = TTLCache.SimpleTTLCache(10)
    # print(get_next_players_from_tournament("test-tournament-1330", "riz0ne", "a8", "b1", cache))
    # report_score(74947317, 16679609)
    result = get_all_players_from_tournament("texas-showdown-2024", "super-street-fighter-ii-turbo")
    print(json.dumps([item.__dict__ for item in result], indent=4))