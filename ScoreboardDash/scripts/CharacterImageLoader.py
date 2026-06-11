import os
from pathlib import Path
from collections import defaultdict

_base = os.path.dirname(os.path.abspath(__file__))
games_path = os.path.join(_base, "../images/games")
image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def get_character_images(game):
    character_map = defaultdict(list)
    game_dir = Path(games_path) / game
    if not game_dir.exists():
        return {}
    for pack_dir in game_dir.iterdir():
        if not pack_dir.is_dir():
            continue
        for file in pack_dir.iterdir():
            if file.suffix.lower() not in image_extensions:
                continue
            name = file.stem
            if "_" not in name:
                continue
            character, variation = name.rsplit("_", 1)
            if not variation.isdigit():
                continue
            if "-" in character:
                character = character.split("-", 1)[1]
            character_map[character].append(str(file))
    return dict(character_map)


def list_games():
    p = Path(games_path)
    if not p.exists():
        return []
    return [d.name for d in p.iterdir() if d.is_dir()]