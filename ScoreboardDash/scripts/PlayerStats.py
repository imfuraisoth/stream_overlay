import json
from io import open
from pathlib import Path
from dataclasses import dataclass

player_data_file_name = "../data/player_data.json"
player_data_backup_file_name = "../data/player_data_backup.json"
placement_file_name = "../data/placement_strings.json"
current_event = ""
first_placement_image_p1 = "In-Game_Cam_Left_Champ.png"
top_8_placement_image_p1 = "In-Game_Cam_Left_Red.png"
first_placement_image_p2 = "In-Game_Cam_Right_Champ.png"
top_8_placement_image_p2 = "In-Game_Cam_Right_Red.png"


@dataclass(init=False)
class EventData:
    placement: int
    wins: int
    losses: int
    message: str
    image: str

    def __init__(self, placement: int, wins: int, losses: int):
        global placement_map
        self.placement = placement
        self.wins = wins
        self.losses = losses
        self.message = placement_map.get(str(placement), "")
        self.image = ""


def event_data_decoder(dct):
    if 'placement' in dct and 'wins' in dct and 'losses' in dct:  # Check for required keys
        return EventData(dct['placement'], dct['wins'], dct['losses'])
    return dct


def read_file(file_name):
    file_path = Path(file_name)
    if not file_path.exists():
        file_path.write_text("{}")  # Creates the file
        print(file_name + " file created successfully.")

    try:
        with open(file_name) as json_file:
            line = json_file.readline()
            result = json.loads(line, object_hook=event_data_decoder)
            json_file.close()
            return result
    except Exception as e:
        print("Error opening file", e)
        return {}


placement_map = read_file(placement_file_name)
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


def get_placement(player_id, p1_or_p2):
    global current_event
    return get_placement_for_event(player_id, current_event, p1_or_p2)


def get_placement_for_event(player_id, event_id, p1_or_p2):
    global player_data
    player = player_data.get(player_id, None)
    if player is None:
        return None

    event_data = player.get(event_id, None)
    if event_data:
        event_data.image = get_image_location(p1_or_p2, event_data.placement)
    return event_data


def get_image_location(p1_or_p2, placement):
    images = {
        (1, 1): first_placement_image_p1,
        (2, 1): first_placement_image_p2,
        (1, 8): top_8_placement_image_p1,
        (2, 8): top_8_placement_image_p2
    }
    return images.get((int(p1_or_p2), 1 if placement == 1 else 8), "")


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
