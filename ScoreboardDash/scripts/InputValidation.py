"""Input validation & sanitization for the local player database.

This is a defensive layer that runs at the WRITE boundary -- before player
data reaches the SQLite inserts -- so that malformed or oversized values
can't enter the DB and break pages, overlays, or the seeding/H2H logic
downstream. It matters most for the import feature, where a bundle may come
from a hand-edited file, an old export, or a corrupted download.

Note on SQL injection: the DB layer already uses parameterized queries
everywhere (the ? placeholders), so string values -- however weird -- are
stored as literal data, never executed. This module is therefore about DATA
QUALITY (empty/huge/duplicate/wrong-type values), not injection.

Philosophy: sanitize rather than reject wherever reasonable. We trim, cap,
dedupe, and coerce types so good-but-messy data still saves; we only drop a
record entirely when it's unsalvageable (e.g. a player with no usable name).
Every fix/drop is recorded in an `issues` list so the import flow can report
what it cleaned.
"""

# Length caps -- generous enough for real names/tags, small enough to stop
# runaway values from bloating the DB or breaking layouts.
MAX_NAME = 80
MAX_TEAM = 60
MAX_COUNTRY = 40
MAX_STATE = 40
MAX_CITY = 60
MAX_HANDLE = 80
MAX_PLATFORM = 40
MAX_ALIAS = 80
MAX_ALIASES = 50
MAX_GAME = 60
MAX_CHAR = 60
MAX_PACK = 80
MAX_FILE = 200
MAX_SLOTS = 8


def _clean_str(v, cap):
    """Coerce to a trimmed string, drop control characters, cap length.
    Returns '' for None/unusable input."""
    if v is None:
        return ""
    s = str(v)
    # strip ASCII control chars (except normal whitespace already handled by strip)
    s = "".join(ch for ch in s if ch == "\t" or ord(ch) >= 32)
    s = s.strip()
    if len(s) > cap:
        s = s[:cap].strip()
    return s


def _clean_int(v, lo, hi, default):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _coerce_state_id(v):
    """start.gg stateId is a canonical int (or None). Keep None as None;
    coerce numeric strings to int; drop anything unusable."""
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def sanitize_player(rec, issues=None):
    """Return a cleaned copy of one player record, or None if unsalvageable.

    Appends human-readable notes to `issues` (a list) for anything changed
    or dropped."""
    issues = issues if issues is not None else []
    if not isinstance(rec, dict):
        issues.append("dropped a player entry that wasn't an object")
        return None

    name = _clean_str(rec.get("name"), MAX_NAME)
    if not name:
        issues.append("dropped a player with no usable name")
        return None

    out = {
        "id": _clean_str(rec.get("id"), 60),
        "name": name,
        "team": _clean_str(rec.get("team"), MAX_TEAM),
        "country": _clean_str(rec.get("country"), MAX_COUNTRY),
        "state": _clean_str(rec.get("state"), MAX_STATE),
        "state_id": _coerce_state_id(rec.get("state_id")),
        "city": _clean_str(rec.get("city"), MAX_CITY),
        "social_handle": _clean_str(rec.get("social_handle"), MAX_HANDLE),
        "social_platform": _clean_str(rec.get("social_platform"), MAX_PLATFORM),
        "is_commentator": bool(rec.get("is_commentator")),
    }

    # aliases: trim, drop empties, dedupe case-insensitively, cap count.
    seen = set()
    aliases = []
    raw_aliases = rec.get("aliases") or []
    if not isinstance(raw_aliases, list):
        issues.append("%s: aliases weren't a list, ignored" % name)
        raw_aliases = []
    for a in raw_aliases:
        a = _clean_str(a, MAX_ALIAS)
        if not a:
            continue
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        aliases.append(a)
    if len(aliases) > MAX_ALIASES:
        issues.append("%s: had %d aliases, capped to %d" % (name, len(aliases), MAX_ALIASES))
        aliases = aliases[:MAX_ALIASES]
    out["aliases"] = aliases

    out["characters"] = _sanitize_game_map(rec.get("characters"), name, "characters", issues)
    out["roster"] = _sanitize_game_map(rec.get("roster"), name, "roster", issues)
    return out


def _sanitize_game_map(val, pname, field, issues):
    """characters/roster are {game: [ {pack,character,palette,file,...}, ... ]}.
    Clean game keys and each pick's fields. Preserves the shape the DB layer
    expects; leaves list vs single-dict as-is (the DB layer already handles
    both)."""
    if not isinstance(val, dict):
        if val not in (None, {}):
            issues.append("%s: %s wasn't an object, ignored" % (pname, field))
        return {}
    out = {}
    for game, picks in val.items():
        g = _clean_str(game, MAX_GAME)
        if not g:
            continue
        cleaned = []
        seq = picks if isinstance(picks, list) else [picks]
        for pick in seq:
            if not isinstance(pick, dict):
                continue
            cp = {
                "pack": _clean_str(pick.get("pack"), MAX_PACK),
                "character": _clean_str(pick.get("character"), MAX_CHAR),
                "palette": _clean_int(pick.get("palette", 0), 0, 999, 0),
                "file": _clean_str(pick.get("file"), MAX_FILE),
            }
            if "slot" in pick:
                cp["slot"] = _clean_int(pick.get("slot"), 0, 99, 0)
            cleaned.append(cp)
        if cleaned:
            out[g] = cleaned
    return out


def sanitize_players(players, issues=None):
    """Sanitize a whole {id: record} player map. Drops unsalvageable records.
    Returns the cleaned map. Records issues in `issues` if provided."""
    issues = issues if issues is not None else []
    if not isinstance(players, dict):
        issues.append("player data wasn't an object; nothing imported")
        return {}
    out = {}
    for pid, rec in players.items():
        clean = sanitize_player(rec, issues)
        if clean is None:
            continue
        # keep the original key as the id if the record didn't carry one
        if not clean.get("id"):
            clean["id"] = _clean_str(pid, 60) or pid
        out[clean["id"] if clean.get("id") else pid] = clean
    return out


def sanitize_games(games, issues=None):
    """Sanitize a {game_name: char_slots} map."""
    issues = issues if issues is not None else []
    if not isinstance(games, dict):
        return {}
    out = {}
    for name, slots in games.items():
        g = _clean_str(name, MAX_GAME)
        if not g:
            continue
        out[g] = _clean_int(slots, 1, MAX_SLOTS, 1)
    return out