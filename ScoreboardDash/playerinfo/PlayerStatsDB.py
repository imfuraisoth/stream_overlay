import sqlite3


db_path = "../data/players/players.db"


def init_db():
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

    results = cur.fetchall()
    conn.close()
    return results
