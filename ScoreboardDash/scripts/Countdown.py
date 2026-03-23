from dataclasses import dataclass
from scripts.FileUtils import FileUtils
from flask import jsonify

game_dir = "../../events/resources/game_logos/"
last_game = "../data/last_countdown.txt"


@dataclass(init=False)
class CurrentGame:
    game_name: str
    icon_file: str
    message: str
    timer: int

    def __init__(self, game_name: str, icon_file: str, message: str, timer: int):
        self.game_name = game_name
        self.icon_file = icon_file
        self.message = message
        self.timer = timer

    def to_dict(self):
        return {
            "game_name": self.game_name,
            "icon_file": self.icon_file,
            "message": self.message,
            "timer": self.timer
        }


current_game = None


def set_game(game_name, message, timer):
    if not game_name:
        print("Game name is invalid. No game set for countdown")
        return
    global current_game, last_game
    icon_file = FileUtils.find_file_name(game_dir, game_name)
    current_game = CurrentGame(game_name, icon_file, message, timer)
    last_game_data = CurrentGame(game_name, icon_file, message, timer)
    FileUtils.write_file(last_game, last_game_data.to_dict())


def get_as_json(first_load):
    global current_game, last_game
    if not current_game:
        if first_load:
            return jsonify(FileUtils.read_file(last_game))
        return "{}"
    result = jsonify(current_game)
    current_game = None
    return result


def get_games():
    return FileUtils.list_files_no_ext(game_dir)


