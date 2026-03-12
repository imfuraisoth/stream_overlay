import json, csv, copy, threading
from io import open
from pathlib import Path
from dataclasses import dataclass
from scripts.FileUtils import FileUtils

root_dir = ""
player_data_file_name = root_dir + "../data/player_data.json"
player_data_backup_file_name = root_dir + "../data/player_data_backup.json"
placement_file_name = root_dir + "../data/placement_strings.json"
league_directory = "../data/league/"
current_event = ""
current_league = ""
first_placement_image_p1 = "In-Game_Cam_Left_Champ.png"
top_8_placement_image_p1 = "In-Game_Cam_Left_Red.png"
first_placement_image_p2 = "In-Game_Cam_Right_Champ.png"
top_8_placement_image_p2 = "In-Game_Cam_Right_Red.png"
league_stats_h2h_file = "braacket_league-head2head.csv"
league_stats_ranking_file = "braacket_league-ranking.csv"
league_rank_dict = {}
league_h2h_dict = {}


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


@dataclass(init=False)
class PlayerLeagueStats:
    rank: str
    points: str
    win_loss: str

    def __init__(self, rank: str, points: str, win_loss: str):
        self.rank = rank
        self.points = points
        self.win_loss = win_loss


@dataclass(init=False)
class MatchInfo:
    player1: PlayerLeagueStats
    player2: PlayerLeagueStats

    def __init__(self, player1: PlayerLeagueStats, player2: PlayerLeagueStats):
        self.player1 = player1
        self.player2 = player2


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
            return json.load(json_file, object_hook=event_data_decoder)
    except Exception as e:
        print("Error opening file", e)
        return {}


placement_map = read_file(placement_file_name)
player_data = read_file(player_data_file_name)
player_data_lock = threading.Lock()


def write_to_file(json_data):
    global player_data
    player_data = copy.deepcopy(json_data)
    FileUtils.write_file(player_data_file_name, player_data)


def add_to_file(json_data):
    global player_data
    with player_data_lock:
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
    with player_data_lock:
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
    with player_data_lock:
        player_data_backup = read_file(player_data_file_name)
        file_path = Path(player_data_backup_file_name)
        if not file_path.exists():
            file_path.write_text("{}")  # Creates the file
            print("Player data backup file created successfully.")
        if player_data_backup:
            # Check to see if it's empty or not before saving it
            FileUtils.write_file(player_data_backup_file_name, player_data_backup)
        player_data = {}
        FileUtils.write_file(player_data_file_name, player_data)


def set_current_event(event):
    global current_event
    current_event = event


def get_current_event():
    global current_event
    return current_event


def get_all_events_with_stats():
    global player_data, current_event
    events = set()
    for player in player_data:
        for event in player_data[player]:
            events.add(event)
    events_data = {
        "current_event": current_event,
        "events": list(events)
    }
    return events_data


def get_match_info(p1_name, p2_name):
    global league_rank_dict, league_h2h_dict

    # ----- Player 1 -----
    p1_data = league_rank_dict.get(p1_name, {})
    p1_rank = str(p1_data.get("Rank", ""))
    p1_points = str(p1_data.get("Points", ""))

    p1_win_loss = league_h2h_dict.get(p1_name, {}).get(p2_name, "")

    # ----- Player 2 -----
    p2_data = league_rank_dict.get(p2_name, {})
    p2_rank = str(p2_data.get("Rank", ""))
    p2_points = str(p2_data.get("Points", ""))

    p2_win_loss = league_h2h_dict.get(p2_name, {}).get(p1_name, "")

    player1 = PlayerLeagueStats(p1_rank, p1_points, p1_win_loss)
    player2 = PlayerLeagueStats(p2_rank, p2_points, p2_win_loss)

    return MatchInfo(player1, player2)


def update_league_stats(directory):
    global league_rank_dict, league_h2h_dict, current_league
    league_rank_dict = get_league_ranking_stats(directory)
    league_h2h_dict = get_league_h2h_stats(directory)
    current_league = directory


def clear_stats():
    global league_rank_dict, league_h2h_dict, current_league
    league_rank_dict = {}
    league_h2h_dict = {}
    current_league = ""
    print("League stats reset")


def get_league_h2h_stats(directory):
    global league_directory
    if not directory:
        return {}
    file_path = Path(league_directory + directory + "/" + league_stats_h2h_file)
    if not file_path.exists():
        print("Could not locate head to head file in directory: " + directory)
        return {}

    league_data = {}
    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))

        # Second row contains column player names (skip first 2 columns)
        column_names = reader[1][2:]

        # Remaining rows contain match data
        for row in reader[2:]:
            row_player = row[1]           # Player name for this row
            match_results = row[2:]       # Results vs others

            league_data[row_player] = {}

            for opponent, result in zip(column_names, match_results):
                league_data[row_player][opponent] = result.strip()
        print("League h2h stats loaded in: " + directory)
    return league_data


def get_league_ranking_stats(directory):
    global league_directory
    if not directory:
        return {}
    file_path = Path(league_directory + directory + "/" + league_stats_ranking_file)
    if not file_path.exists():
        print("Could not locate ranking file in directory: " + directory)
        return {}

    league_data = {}
    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            player_name = row["Player"]

            # Optional: convert numeric fields
            row["Rank"] = int(row["Rank"])
            row["Points"] = int(row["Points"])

            league_data[player_name] = row
    print("League rank stats loaded in: " + directory)
    return league_data


def list_league_stats_directories():
    global current_league
    league_data = {
        "current_league": current_league,
        "leagues": [p.name for p in Path(league_directory).iterdir() if p.is_dir()]

    }
    return league_data
