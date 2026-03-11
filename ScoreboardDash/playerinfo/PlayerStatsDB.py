import sqlite3, os, json
from pathlib import Path

db_path = "../data/players/players.db"
last_access_path = "../data/players/last_access_info.txt"
last_access_info = {}


def read_file(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return {}


def write_file(file_path, content):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(content, default=lambda o: o.__dict__))


def init_db():
    global last_access_info
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    last_access_info = read_file(last_access_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        image TEXT,
        variant TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER,
        character_id INTEGER,
        game_id INTEGER,
        FOREIGN KEY(player_id) REFERENCES players(id),
        FOREIGN KEY(character_id) REFERENCES characters(id),
        FOREIGN KEY(game_id) REFERENCES games(id)
    )
    """)

    conn.commit()
    conn.close()


def save_player_characters(data):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    game = data["game"]
    player = data["player"]
    characters = data["characters"]

    # --- insert or get game ---
    cur.execute("INSERT OR IGNORE INTO games(name) VALUES(?)", (game,))
    cur.execute("SELECT id FROM games WHERE name=?", (game,))
    game_id = cur.fetchone()[0]

    # --- insert or get player ---
    cur.execute("INSERT OR IGNORE INTO players(name) VALUES(?)", (player,))
    cur.execute("SELECT id FROM players WHERE name=?", (player,))
    player_id = cur.fetchone()[0]

    # --- remove old selections for this player/game ---
    cur.execute("""
        DELETE FROM player_characters
        WHERE player_id=? AND game_id=?
    """, (player_id, game_id))

    for c in characters:
        name = c["character"]
        image = c["image"].replace("\\", "/")
        variant = c.get("variant", "")

        # insert or get character
        cur.execute("""
            INSERT OR IGNORE INTO characters(name, image, variant)
            VALUES (?, ?, ?)
        """, (name, image, variant))

        cur.execute("""
            SELECT id FROM characters
            WHERE name=? AND image=? AND variant=?
        """, (name, image, variant))
        character_id = cur.fetchone()[0]

        # link player -> character
        cur.execute("""
            INSERT INTO player_characters(player_id, character_id, game_id)
            VALUES (?, ?, ?)
        """, (player_id, character_id, game_id))

    conn.commit()
    conn.close()


def get_player_characters(player, game):
    global last_access_info
    last_access_info = {"player": player, "game": game}
    write_file(last_access_path, last_access_info)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT characters.name, characters.variant, characters.image
        FROM player_characters
        JOIN characters ON characters.id = player_characters.character_id
        JOIN players ON players.id = player_characters.player_id
        JOIN games ON games.id = player_characters.game_id
        WHERE players.name=? AND games.name=?
    """, (player, game))

    rows = cur.fetchall()
    conn.close()

    characters = []
    for name, variant, image in rows:
        characters.append({
            "character": name,
            "variant": variant,
            "image": image
        })

    return {
        "player": player,
        "game": game,
        "characters": characters
    }


def get_last_access_player_info():
    global last_access_info
    if not last_access_info:
        return {}
    return get_player_characters(last_access_info.get("player"), last_access_info.get("game"))


def remove_player(player_name):
    global last_access_info
    if last_access_info.get("player") == player_name:
        last_access_info = {}
        write_file(last_access_path, last_access_info)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # get player id
    cur.execute("SELECT id FROM players WHERE name=?", (player_name,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return False

    player_id = row[0]

    # remove character associations
    cur.execute("""
        DELETE FROM player_characters
        WHERE player_id=?
    """, (player_id,))

    # remove player
    cur.execute("""
        DELETE FROM players
        WHERE id=?
    """, (player_id,))

    conn.commit()
    conn.close()

    return True
