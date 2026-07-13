import sqlite3, os
from pathlib import Path

# Optional observer: set on_change = fn() to be notified after any
# player-data mutation (used for live page sync)
on_change = None

_base = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(_base, "../../data/players/players.db")


def _connect():
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the unified schema and migrate any older layouts in place."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS local_players (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        team TEXT DEFAULT '',
        country TEXT DEFAULT '',
        state TEXT DEFAULT '',
        state_id INTEGER,
        city TEXT DEFAULT '',
        social_handle TEXT DEFAULT '',
        social_platform TEXT DEFAULT '',
        is_commentator INTEGER DEFAULT 0
    )
    """)

    _migrate_legacy_tables(cur)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        name TEXT PRIMARY KEY,
        char_slots INTEGER NOT NULL DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS local_player_characters (
        player_id TEXT NOT NULL,
        game TEXT NOT NULL,
        slot INTEGER NOT NULL DEFAULT 0,
        pack TEXT DEFAULT '',
        character TEXT DEFAULT '',
        palette INTEGER DEFAULT 0,
        file TEXT DEFAULT '',
        PRIMARY KEY (player_id, game, slot),
        FOREIGN KEY(player_id) REFERENCES local_players(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS local_player_roster (
        player_id TEXT NOT NULL,
        game TEXT NOT NULL,
        character TEXT NOT NULL,
        pack TEXT DEFAULT '',
        palette INTEGER DEFAULT 0,
        file TEXT DEFAULT '',
        PRIMARY KEY (player_id, game, character),
        FOREIGN KEY(player_id) REFERENCES local_players(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_aliases (
        player_id TEXT NOT NULL,
        alias TEXT NOT NULL UNIQUE COLLATE NOCASE,
        FOREIGN KEY(player_id) REFERENCES local_players(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


def _migrate_legacy_tables(cur):
    """Upgrade from previous schemas without losing data.

    1. Drops the retired roster system tables (players/characters/
       player_characters) and the old integer-keyed games table.
    2. Rebuilds local_player_characters with the slot column if it
       exists in the pre-slot layout, carrying rows over as slot 0.
    """
    # Drop retired roster tables, dependents first (player_characters
    # holds foreign keys into the other three)
    for legacy in ("player_characters", "characters", "players"):
        cur.execute("DROP TABLE IF EXISTS " + legacy)

    # Old roster games table had an integer id column -- detect and drop
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if cur.fetchone():
        cols = [r[1] for r in cur.execute("PRAGMA table_info(games)").fetchall()]
        if "char_slots" not in cols:
            cur.execute("DROP TABLE games")

    # local_players from before the case-insensitive name constraint
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='local_players'")
    row = cur.fetchone()
    if row and "COLLATE NOCASE" not in (row[0] or ""):
        cur.execute("ALTER TABLE local_players RENAME TO _lp_old")
        cur.execute("""
        CREATE TABLE local_players (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            team TEXT DEFAULT '',
            country TEXT DEFAULT '',
            social_handle TEXT DEFAULT '',
            social_platform TEXT DEFAULT '',
            is_commentator INTEGER DEFAULT 0
        )
        """)
        cur.execute("""
        INSERT OR IGNORE INTO local_players
        SELECT id, name, team, country, social_handle, social_platform,
               is_commentator
        FROM _lp_old
        """)
        cur.execute("DROP TABLE _lp_old")

    # Add location columns to existing local_players tables that predate them
    # (used for seeding checks + start.gg location auto-pull). Idempotent:
    # each column is only added if missing, so this no-ops after the first run.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_players'")
    if cur.fetchone():
        lp_cols = [r[1] for r in cur.execute("PRAGMA table_info(local_players)").fetchall()]
        if "state" not in lp_cols:
            cur.execute("ALTER TABLE local_players ADD COLUMN state TEXT DEFAULT ''")
        if "state_id" not in lp_cols:
            cur.execute("ALTER TABLE local_players ADD COLUMN state_id INTEGER")
        if "city" not in lp_cols:
            cur.execute("ALTER TABLE local_players ADD COLUMN city TEXT DEFAULT ''")

    # Pre-slot local_player_characters: PRIMARY KEY was (player_id, game)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_player_characters'")
    if cur.fetchone():
        cols = [r[1] for r in cur.execute("PRAGMA table_info(local_player_characters)").fetchall()]
        if "slot" not in cols:
            cur.execute("ALTER TABLE local_player_characters RENAME TO _lpc_old")
            cur.execute("""
            CREATE TABLE local_player_characters (
                player_id TEXT NOT NULL,
                game TEXT NOT NULL,
                slot INTEGER NOT NULL DEFAULT 0,
                pack TEXT DEFAULT '',
                character TEXT DEFAULT '',
                palette INTEGER DEFAULT 0,
                file TEXT DEFAULT '',
                PRIMARY KEY (player_id, game, slot),
                FOREIGN KEY(player_id) REFERENCES local_players(id) ON DELETE CASCADE
            )
            """)
            cur.execute("""
            INSERT INTO local_player_characters
                (player_id, game, slot, pack, character, palette, file)
            SELECT player_id, game, 0, pack, character, palette, file
            FROM _lpc_old
            """)
            cur.execute("DROP TABLE _lpc_old")


# ============================================================
# Games registry
# ============================================================

def get_games():
    """Return {game_name: char_slots} for all registered games."""
    conn = _connect()
    cur = conn.cursor()
    result = {name: slots for name, slots in
              cur.execute("SELECT name, char_slots FROM games")}
    conn.close()
    return result


def ensure_games(names):
    """Register any unseen game names with the default of 1 slot."""
    if not names:
        return
    conn = _connect()
    cur = conn.cursor()
    for name in names:
        if name:
            cur.execute("INSERT OR IGNORE INTO games (name, char_slots) VALUES (?, 1)",
                        (name,))
    conn.commit()
    conn.close()


def set_game_slots(name, char_slots):
    """Set how many character picks a game uses (clamped to 1..8)."""
    if not name:
        return False
    char_slots = max(1, min(8, int(char_slots)))
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO games (name, char_slots) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET char_slots=excluded.char_slots
    """, (name, char_slots))
    conn.commit()
    conn.close()
    return True


# ============================================================
# Local player profiles
#
#   get_local_players() -> {pid: {id, name, team, country,
#                                 social_handle, social_platform,
#                                 is_commentator,
#                                 characters: {game: [ {slot, pack,
#                                     character, palette, file}, ... ]}}}
#
#   save_local_players(players_dict) -> syncs the DB to match the dict
#       (upserts everything, deletes records whose id is absent)
#
# Character lists are ordered by slot. A game's list may have fewer
# entries than its char_slots if some slots are unset.
# ============================================================

def get_local_players():
    conn = _connect()
    cur = conn.cursor()

    players = {}
    cur.execute("""
        SELECT id, name, team, country, state, state_id, city, social_handle, social_platform,
               is_commentator
        FROM local_players
    """)
    for pid, name, team, country, state, state_id, city, soc_h, soc_p, is_comm in cur.fetchall():
        players[pid] = {
            "id": pid,
            "name": name,
            "team": team or "",
            "country": country or "",
            "state": state or "",
            "state_id": state_id,
            "city": city or "",
            "social_handle": soc_h or "",
            "social_platform": soc_p or "",
            "is_commentator": bool(is_comm),
            "characters": {},
            "roster": {},
            "aliases": []
        }

    cur.execute("""
        SELECT player_id, game, slot, pack, character, palette, file
        FROM local_player_characters
        ORDER BY player_id, game, slot
    """)
    for pid, game, slot, pack, character, palette, file in cur.fetchall():
        if pid in players:
            players[pid]["characters"].setdefault(game, []).append({
                "slot": slot,
                "pack": pack or "",
                "character": character or "",
                "palette": palette if palette is not None else 0,
                "file": file or ""
            })

    cur.execute("SELECT player_id, alias FROM player_aliases ORDER BY alias")
    for pid, alias in cur.fetchall():
        if pid in players:
            players[pid]["aliases"].append(alias)

    cur.execute("""
        SELECT player_id, game, character, pack, palette, file
        FROM local_player_roster
        ORDER BY player_id, game, character
    """)
    for pid, game, character, pack, palette, file in cur.fetchall():
        if pid in players:
            players[pid]["roster"].setdefault(game, []).append({
                "character": character or "",
                "pack": pack or "",
                "palette": palette if palette is not None else 0,
                "file": file or ""
            })

    conn.close()
    return players


def save_local_players(players):
    """Sync the DB to match the given {pid: record} dict.

    The dict is the complete source of truth: records are upserted,
    and any player whose id is missing from the dict is deleted.

    characters values may be:
      - a list of pick dicts (new shape; slot taken from the item's
        "slot" key, falling back to list position)
      - a single pick dict (old shape; treated as slot 0)
    """
    if not isinstance(players, dict):
        return

    # Sanitize all incoming records at this single write choke-point, so every
    # path (UI saves, imports, merges) is protected from malformed/oversized
    # data. SQL injection is already prevented by parameterized queries; this
    # is about data quality (empty/huge/duplicate/wrong-type values).
    try:
        from scripts import InputValidation
        players = InputValidation.sanitize_players(players)
    except Exception as _e:
        # If validation ever fails to import/run, fall back to raw data rather
        # than losing the save entirely (parameterized queries still protect
        # against injection).
        print("save_local_players: validation skipped (%s)" % _e)

    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM local_players")
        existing_ids = {row[0] for row in cur.fetchall()}
        removed = existing_ids - set(players.keys())
        for pid in removed:
            cur.execute("DELETE FROM local_players WHERE id=?", (pid,))
            cur.execute("DELETE FROM local_player_characters WHERE player_id=?", (pid,))

        for pid, rec in players.items():
            cur.execute("""
                INSERT INTO local_players
                    (id, name, team, country, state, state_id, city, social_handle,
                     social_platform, is_commentator)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    team=excluded.team,
                    country=excluded.country,
                    state=excluded.state,
                    state_id=excluded.state_id,
                    city=excluded.city,
                    social_handle=excluded.social_handle,
                    social_platform=excluded.social_platform,
                    is_commentator=excluded.is_commentator
            """, (
                pid,
                rec.get("name", ""),
                rec.get("team", ""),
                rec.get("country", ""),
                rec.get("state", ""),
                rec.get("state_id"),
                rec.get("city", ""),
                rec.get("social_handle", ""),
                rec.get("social_platform", ""),
                1 if rec.get("is_commentator") else 0
            ))

            cur.execute("DELETE FROM local_player_characters WHERE player_id=?", (pid,))
            chars = rec.get("characters") or {}
            if isinstance(chars, dict):
                for game, picks in chars.items():
                    if isinstance(picks, dict):
                        picks = [picks]          # legacy single-pick shape
                    if not isinstance(picks, list):
                        continue
                    seen_slots = set()
                    for index, pick in enumerate(picks):
                        if not isinstance(pick, dict):
                            continue
                        slot = pick.get("slot", index)
                        try:
                            slot = int(slot)
                        except (TypeError, ValueError):
                            slot = index
                        if slot in seen_slots:
                            continue
                        seen_slots.add(slot)
                        cur.execute("""
                            INSERT INTO local_player_characters
                                (player_id, game, slot, pack, character, palette, file)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            pid,
                            game,
                            slot,
                            pick.get("pack", ""),
                            pick.get("character", ""),
                            int(pick.get("palette", 0) or 0),
                            pick.get("file", "")
                        ))

            cur.execute("DELETE FROM player_aliases WHERE player_id=?", (pid,))
            for alias in (rec.get("aliases") or []):
                alias = str(alias).strip()
                if alias:
                    # UNIQUE NOCASE: silently skip collisions with other
                    # players' aliases
                    cur.execute(
                        "INSERT OR IGNORE INTO player_aliases (player_id, alias) VALUES (?, ?)",
                        (pid, alias))

            cur.execute("DELETE FROM local_player_roster WHERE player_id=?", (pid,))
            roster = rec.get("roster") or {}
            if isinstance(roster, dict):
                for game, entries in roster.items():
                    if isinstance(entries, dict):
                        entries = [entries]
                    if not isinstance(entries, list):
                        continue
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                        character = (entry.get("character") or "").strip()
                        if not character:
                            continue
                        # PK (player_id, game, character): repeats update
                        # the preferred pack/palette/file in place
                        cur.execute("""
                            INSERT INTO local_player_roster
                                (player_id, game, character, pack, palette, file)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(player_id, game, character) DO UPDATE SET
                                pack=excluded.pack,
                                palette=excluded.palette,
                                file=excluded.file
                        """, (
                            pid,
                            game,
                            character,
                            entry.get("pack", ""),
                            int(entry.get("palette", 0) or 0),
                            entry.get("file", "")
                        ))

        conn.commit()
    finally:
        conn.close()
    if on_change:
        try:
            on_change()
        except Exception:
            pass


def purge_all_players():
    """Delete EVERY local player and all their associated data
    (characters, roster, aliases). Match history event files are NOT
    touched -- they keep each set's tag/user_id, so a re-import or
    reconcile can recreate and re-link players afterward.

    Returns the number of players that were removed."""
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM local_players")
        count = cur.fetchone()[0]
        # Truncate every player-scoped table. 'games' is config, not
        # player data, so it is intentionally left alone.
        cur.execute("DELETE FROM local_player_characters")
        cur.execute("DELETE FROM local_player_roster")
        cur.execute("DELETE FROM player_aliases")
        cur.execute("DELETE FROM local_players")
        conn.commit()
    finally:
        conn.close()
    if on_change:
        try:
            on_change()
        except Exception:
            pass
    return count


def resolve_player_id(name):
    """Resolve a display name OR alias to a player id, case-insensitive.

    Returns the player id string, or None if nothing matches."""
    if not name or not str(name).strip():
        return None
    name = str(name).strip()
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM local_players WHERE name = ? COLLATE NOCASE", (name,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT player_id FROM player_aliases WHERE alias = ? COLLATE NOCASE", (name,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def merge_players(primary_id, duplicate_id):
    """Merge duplicate's data into primary, then delete the duplicate.

    - Profile fields: primary wins; primary's empty fields are filled
      from the duplicate; is_commentator is OR'd.
    - Characters/roster: copied for any game the primary lacks
      (per-game for picks, per-character for roster entries).
    - Identity: the duplicate's name and all its aliases become
      aliases of the primary, so future data under those names
      resolves correctly.

    Returns (ok, message)."""
    if primary_id == duplicate_id:
        return False, "Cannot merge a player into itself"
    players = get_local_players()
    primary = players.get(primary_id)
    duplicate = players.get(duplicate_id)
    if not primary or not duplicate:
        return False, "Player not found"

    # Profile: fill primary's blanks from the duplicate
    for field in ("team", "country", "state", "state_id", "city", "social_handle", "social_platform"):
        if not primary.get(field) and duplicate.get(field):
            primary[field] = duplicate[field]
    primary["is_commentator"] = bool(primary.get("is_commentator") or duplicate.get("is_commentator"))

    # Picks: per game, primary wins
    for game, picks in (duplicate.get("characters") or {}).items():
        if not primary["characters"].get(game):
            primary["characters"][game] = picks

    # Roster: union per game, primary's entry wins per character
    for game, entries in (duplicate.get("roster") or {}).items():
        mine = primary["roster"].setdefault(game, [])
        have = {e["character"].lower() for e in mine if e.get("character")}
        for e in entries:
            if e.get("character") and e["character"].lower() not in have:
                mine.append(e)

    # Identity: duplicate's name + aliases -> primary's aliases
    new_aliases = set(a.lower() for a in primary.get("aliases", []))
    for alias in [duplicate["name"]] + list(duplicate.get("aliases") or []):
        if alias and alias.lower() != primary["name"].lower() and alias.lower() not in new_aliases:
            primary.setdefault("aliases", []).append(alias)
            new_aliases.add(alias.lower())

    del players[duplicate_id]
    save_local_players(players)
    return True, "Merged %s into %s" % (duplicate["name"], primary["name"])