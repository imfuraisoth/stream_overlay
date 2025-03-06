import json
from io import open
from pathlib import Path
from dataclasses import dataclass

player_data_file_name = "../data/player_data.json"


def read_file(file_name):
    file_path = Path(file_name)
    if not file_path.exists():
        file_path.write_text("{}")  # Creates the file
        print("Player data file created successfully.")

    try:
        with open(file_name) as json_file:
            line = json_file.readline()
            result = json.loads(line)
            json_file.close()
            return result
    except Exception as e:
        print("Error opening file", e)
        return {}


def write_to_file(json_data):
    global player_data
    player_data = json_data
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(player_data, default=lambda o: o.__dict__))


player_data = read_file(player_data_file_name)


@dataclass
class EventData:
    placement: int
    wins: int
    losses: int


def add_player_data(player_id, event_id, placement, wins, loses):
    event_data = EventData(placement, wins, loses)
    global player_data
    event_map = player_data[player_id]
    if event_map is None:
        event_map = {}
    event_map[event_id] = event_data
    player_data[player_id] = event_map
    write_to_file(player_data)


def get_placement(player_id, event_id):
    global player_data
    player = player_data[player_id]
    if player is None:
        return None

    event = player[event_id]
    if event is None:
        return None

    return event.placement
