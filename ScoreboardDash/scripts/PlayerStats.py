import json
from io import open
from pathlib import Path
from dataclasses import dataclass

player_data_file_name = "../data/player_data.json"
player_data_backup_file_name = "../data/player_data_backup.json"
current_event = ""


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


player_data = read_file(player_data_file_name)


def write_to_file(json_data):
    global player_data
    player_data = json_data
    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(player_data, default=lambda o: o.__dict__))


def add_to_file(json_data):
    global player_data
    player_data = read_file(player_data_file_name)
    for key in json_data:
        if key in player_data:
            event_map = player_data[key]
            event_map.update(json_data[key])
            player_data[key] = event_map
        else:
            player_data[key] = json_data[key]
    write_to_file(player_data)


@dataclass
class EventData:
    placement: int
    wins: int
    losses: int


def add_player_data(player_id, event_id, placement, wins, loses):
    event_data = EventData(placement, wins, loses)
    global player_data
    player_data = read_file(player_data_file_name)
    event_map = player_data.get(player_id, None)
    if event_map is None:
        event_map = {}
    event_map[event_id] = event_data
    player_data[player_id] = event_map
    write_to_file(player_data)


def get_placement(player_id):
    global current_event
    return get_placement_for_event(player_id, current_event)


def get_placement_for_event(player_id, event_id):
    global player_data
    player = player_data.get(player_id, None)
    if player is None:
        return None

    return player.get(event_id, None)


def delete_stats():
    global player_data
    player_data = {}
    player_data_backup = read_file(player_data_file_name)
    file_path = Path(player_data_backup_file_name)
    if not file_path.exists():
        file_path.write_text("{}")  # Creates the file
        print("Player data backup file created successfully.")
    if player_data_backup:
        # Check to see if it's empty or not before saving it
        with open(player_data_backup_file_name, 'w', encoding="utf-8") as json_file:
            json_file.write(json.dumps(player_data_backup, default=lambda o: o.__dict__))

    with open(player_data_file_name, 'w', encoding="utf-8") as json_file:
        json_file.write(json.dumps(player_data, default=lambda o: o.__dict__))


def set_current_event(event):
    global current_event
    current_event = event


def get_current_event():
    global current_event
    return current_event


def get_all_events_with_stats():
    global player_data
    events = set()
    for player in player_data:
        for event in player_data[player]:
            events.add(event)

    return list(events)
