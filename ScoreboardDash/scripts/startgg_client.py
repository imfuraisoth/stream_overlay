import requests
import json
from io import open

token_file = "../../data/startgg_token.txt"
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


def get_next_players(event_name, current_player1, current_player2):
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
    slug = "tournament/" + event_name
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
        sets = stream_queue[0]["sets"]
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


if __name__ == "__main__":
    print(get_events("test-tournament-1330"))
    print(get_next_players("test-tournament-1330", "a8", "b1"))
