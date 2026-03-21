from pathlib import Path
from collections import defaultdict

games_path = "images/games"
image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")


def get_character_images(game):
    global games_path, image_extensions
    character_map = defaultdict(list)

    for file in Path(games_path + "/" + game + "/icon").iterdir():

        name = file.stem  # filename without extension

        if "_" not in name:
            continue

        character, variation = name.rsplit("_", 1)

        if not variation.isdigit():
            continue

        character_map[character].append(str(file))

    return dict(character_map)


def list_games():
    global games_path
    return [p.name for p in Path(games_path).iterdir() if p.is_dir()]
