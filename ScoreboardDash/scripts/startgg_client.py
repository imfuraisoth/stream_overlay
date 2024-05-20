import requests
import json
from io import open

token_file = "../data/startgg_token.txt"
start_gg_file = "../data/startgg_info.txt"
url = 'https://api.start.gg/gql/alpha'


class Match:
    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2

    def contains_players(self, name1, name2):
        return self.player1.name == name1 or self.player1.name == name2 \
               or self.player2.name == name1 or self.player2.name == name2

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)


class Player:
    def __init__(self, name, team):
        self.name = name
        self.team = team


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
    result = response.json()
    events = result["data"]["tournament"]["events"]
    if events is None or len(events) == 0:
        print("No events found in start.gg for tournament: " + tournament_name)
        return "[]"
    events_list = []
    for event in events:
        event_name = event["name"]
        if event_name is not None and event_name.strip() != "":
            events_list.append(event_name)
    return json.dumps(events_list)


def get_next_players(current_player1, current_player2):
    startgg_info = get_start_gg_info()
    if startgg_info is None:
        print("No tournament information found, returning empty")
        return []
    tournament = startgg_info["tournament"]
    stream = startgg_info["stream"]
    print("Tournament: " + tournament + " stream: " + stream)
    return get_next_players_from_tournament(tournament, stream, current_player1, current_player2)


def get_next_players_from_tournament(tournament_name, stream_name, current_player1, current_player2):
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
                    name
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
    result = response.json()
    matches = []
    stream_queue = result["data"]["tournament"]["streamQueue"]
    if stream_queue is not None and len(stream_queue) > 0:
        for stream in stream_queue:
            if stream['stream']['streamName'] == stream_name:
                print("Found stream queue data for: " + stream_name)
                sets = stream["sets"]
                for s in sets:
                    slots = s["slots"]
                    if slots is not None and len(slots) == 2:
                        match = Match(create_player(slots[0]), create_player(slots[1]))
                        if not match.contains_players(current_player1, current_player2):
                            matches.append(match.to_json())
    json_dicts = [json.loads(match) for match in matches]
    return json.dumps(json_dicts, indent=4)


def create_player(slot):
    if slot["entrant"] is None or slot["entrant"]["name"] is None or slot["entrant"]["name"].strip() == "":
        return Player("Winner", "")

    name = slot["entrant"]["name"]
    team = ""
    if " | " in name:
        team, name = slot["entrant"]["name"].split(" | ")

    return Player(name, team)


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

    return read_file(start_gg_file)


def read_file(file_name):
    with open(file_name) as json_file:
        line = json_file.readline()
        result = json.loads(line)
        json_file.close()
        return result


if __name__ == "__main__":
    print(get_events("test-tournament-1330"))
    print(get_next_players_from_tournament("test-tournament-1330", "riz0ne", "a8", "b1"))
