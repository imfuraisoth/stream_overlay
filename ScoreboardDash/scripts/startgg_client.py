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


def read_file(file_name, default):
    with open(file_name) as json_file:
        line = json_file.readline()
        if not line:
            return default
        response_json = json.loads(line)
        json_file.close()
        return response_json


country_code_map = read_file(country_prop_file, "{}")


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
    def __init__(self, name, entrant_id, team, country):
        self.name = name
        self.team = team
        self.entrant_id = entrant_id
        self.country = country


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
    response_json = response.json()
    events = response_json["data"]["tournament"]["events"]
    if events is None or len(events) == 0:
        print("No events found in start.gg for tournament: " + tournament_name)
        return "[]"
    events_list = []
    for event in events:
        event_name = event["name"]
        if event_name is not None and event_name.strip() != "":
            events_list.append(event_name)
    return json.dumps(events_list)


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
    response_json = response.json()
    return response_json["data"]["event"]["numEntrants"]


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
    response_json = response.json()
    entrants = response_json["data"]["event"]["entrants"]["nodes"]
    if entrants is None or len(entrants) == 0:
        print("No entrants found for event: " + event_name + " in start.gg for tournament: " + tournament_name)
        return "[]"
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
            id
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
    response_json = response.json()
    print(response_json)
    matches = []
    stream_queue = response_json["data"]["tournament"]["streamQueue"]
    if stream_queue is not None and len(stream_queue) > 0:
        for stream in stream_queue:
            if stream['stream']['streamName'] == stream_name:
                print("Found stream queue data for: " + stream_name)
                sets = stream["sets"]
                for s in sets:
                    set_id = s["id"]
                    slots = s["slots"]
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
                        location {
                          country
                        }
                      }
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
    response_json = response.json()
    entrants = response_json["data"]["event"]["entrants"]["nodes"]
    if entrants is None or len(entrants) == 0:
        print("No entrants found for event: " + event_name + " in start.gg for tournament: " + tournament_name)
        return "[]"
    entrants_list = []
    for entrant in entrants:
        entrant_id = entrant["id"]
        gamer_tag = entrant["participants"][0]["gamerTag"]
        team = entrant["participants"][0]["prefix"]
        country = get_country(entrant["participants"][0])
        entrants_list.append(Player(gamer_tag, entrant_id, team or "", country))
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
        return Player("TBD", "TBD", "", "US")

    name = slot["entrant"]["name"]
    team = ""
    if " | " in name:
        team, name = slot["entrant"]["name"].split(" | ")
    country_code = get_country(slot["entrant"]["participants"][0])
    entrant_id = slot["entrant"]["id"]
    return Player(name, entrant_id, team, country_code)


def get_country(participant):
    user = participant["user"]
    country_code = "US"
    if user:
        location = user["location"]
        if location:
            country = location["country"]
            if country:
                country_code = country_code_map[country]
                if country_code is None:
                    # Couldn't find the country code from country code map, default back to US
                    print("Couldn't find country code for country: " + country)
                    country_code = "US"
    return country_code


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


if __name__ == "__main__":
    # result = get_top_8_entrants_for_event("texas-showdown-2024", "super-street-fighter-ii-turbo")
    # print(result)
    # player_stats.write_to_file(result)
    # cache = TTLCache.SimpleTTLCache(10)
    # print(get_next_players_from_tournament("test-tournament-1330", "riz0ne", "a8", "b1", cache))
    # report_score(74947317, 16679609)
    result = get_all_players_from_tournament("texas-showdown-2024", "super-street-fighter-ii-turbo")
    print(json.dumps([item.__dict__ for item in result], indent=4))
