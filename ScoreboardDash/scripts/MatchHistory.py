"""Persistent player-vs-player match history.

Storage model (mirrors the RetroFGCReplayer matchup pattern):
  data/matchups/<event_slug>.json   -- one file per imported event,
      set-id keyed so re-importing updates in place.
  data/matchups/_alltime.json       -- derived rollup, regenerated on
      every import; nested {pid: {pid: {wins, losses, sets:[...]}}}.

Identity: sets are stored by resolved local player id where known, plus
the raw start.gg tag/user_id so unreconciled sets can be attached later.
The rollup resolves ids through the current alias/merge map at build
time, so merging two players retroactively unifies their history
without rewriting event files.
"""
import os
import json
import re

_base = os.path.dirname(os.path.abspath(__file__))
MATCHUP_DIR = os.path.join(_base, "..", "..", "data", "matchups")
ALLTIME_FILE = os.path.join(MATCHUP_DIR, "_alltime.json")


def _ensure_dir():
    os.makedirs(MATCHUP_DIR, exist_ok=True)


def _slug_to_filename(event_slug):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", event_slug)
    return os.path.join(MATCHUP_DIR, safe + ".json")


def event_display_name(data):
    """The label to show for an event: custom display_name if set,
    else 'Tournament -- Event', else the event name, else the slug."""
    custom = (data.get("display_name") or "").strip()
    if custom:
        return custom
    ev = (data.get("event_name") or "").strip()
    tn = (data.get("tournament_name") or "").strip()
    if tn and ev and tn.lower() != ev.lower():
        return tn + " \u2014 " + ev
    return ev or tn or data.get("event_slug", "")


def set_event_display_name(event_slug, display_name):
    """Set/clear an event's custom display name. Returns True if written."""
    data = load_event(event_slug)
    if not data:
        return False
    data["display_name"] = (display_name or "").strip()
    with open(_slug_to_filename(event_slug), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def list_events():
    """Return metadata for every imported event, newest first."""
    _ensure_dir()
    events = []
    for fn in os.listdir(MATCHUP_DIR):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        try:
            with open(os.path.join(MATCHUP_DIR, fn), encoding="utf-8") as f:
                data = json.load(f)
            events.append({
                "event_slug": data.get("event_slug"),
                "event_name": data.get("event_name"),
                "tournament_name": data.get("tournament_name"),
                "display_name": data.get("display_name", ""),
                "label": event_display_name(data),
                "game": data.get("game", ""),
                "series": data.get("series", ""),
                "imported_at": data.get("imported_at"),
                "set_count": len(data.get("sets", {})),
                "file": fn,
            })
        except Exception as e:
            print("MatchHistory: skipping unreadable %s (%s)" % (fn, e))
    events.sort(key=lambda e: e.get("imported_at") or "", reverse=True)
    return events


def delete_event(event_slug):
    """Remove a per-event file. Caller should rebuild_alltime() after.

    Returns True if a file was removed, False if it didn't exist.
    Players and aliases are intentionally left untouched."""
    path = _slug_to_filename(event_slug)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def load_event(event_slug):
    path = _slug_to_filename(event_slug)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_event_import(event_slug, event_name, tournament_name, sets, imported_at,
                      assignments=None, standings=None, series=None, game=None):
    """Write/replace a per-event file from get_completed_sets output.

    sets: list of dicts from startgg_client.get_completed_sets.
    assignments: optional {start.gg user_id or tag -> local player id}
        used to stamp the resolved local id onto each set's players.
    Set-id keyed: re-importing the same event replaces it cleanly.
    """
    _ensure_dir()
    assignments = assignments or {}

    def _resolve(entrant):
        # Prefer user_id (stable across tag changes), fall back to tag
        key = ("u:" + str(entrant["user_id"])) if entrant.get("user_id") else ("t:" + entrant.get("tag", ""))
        return assignments.get(key) or assignments.get(entrant.get("tag", "")) or None

    set_map = {}
    for s in sets:
        set_map[str(s["set_id"])] = {
            "set_id": str(s["set_id"]),
            "round_name": s.get("full_round_text") or s.get("round_name") or "",
            "round": s.get("round"),
            "completed_at": s.get("completed_at"),
            "p1": {
                "tag": s["p1"]["tag"], "team": s["p1"].get("team", ""),
                "user_id": s["p1"].get("user_id"),
                "entrant_id": s["p1"].get("entrant_id"),
                "player_id": _resolve(s["p1"]),
            },
            "p2": {
                "tag": s["p2"]["tag"], "team": s["p2"].get("team", ""),
                "user_id": s["p2"].get("user_id"),
                "entrant_id": s["p2"].get("entrant_id"),
                "player_id": _resolve(s["p2"]),
            },
            "p1_score": s.get("p1_score"),
            "p2_score": s.get("p2_score"),
            "winner_entrant_id": s.get("winner_entrant_id"),
            "winner_user_id": s.get("winner_user_id"),
        }

    # Placements keyed by resolved local id when known, else by the
    # raw start.gg key so reconciliation can attach them later.
    placement_map = {}
    for st in (standings or []):
        ent = {"tag": st.get("tag", ""), "user_id": st.get("user_id"),
               "entrant_id": st.get("entrant_id")}
        local = _resolve(ent)
        key = local or (("u:" + str(st["user_id"])) if st.get("user_id") else ("t:" + st.get("tag", "")))
        placement_map[key] = {
            "placement": st.get("placement"),
            "tag": st.get("tag", ""),
            "user_id": st.get("user_id"),
            "player_id": local,
        }

    # Preserve existing placements on re-import if standings not re-fetched
    existing = load_event(event_slug)
    if standings is None and existing:
        placement_map = existing.get("placements", {})

    # Preserve an existing series tag across re-import unless one is
    # explicitly provided.
    if series is None and existing:
        series = existing.get("series", "")
    # Preserve custom display name + game across re-import.
    display_name = existing.get("display_name", "") if existing else ""
    if game is None:
        game = existing.get("game", "") if existing else ""
    payload = {
        "event_slug": event_slug,
        "event_name": event_name,
        "tournament_name": tournament_name,
        "display_name": display_name,
        "game": game or "",
        "series": series or "",
        "imported_at": imported_at,
        "sets": set_map,
        "placements": placement_map,
    }
    with open(_slug_to_filename(event_slug), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return len(set_map)


def collect_unassigned(event_slug):
    """Entrants in an event with no resolved local player_id.

    Returns list of {tag, user_id, team} deduped by user_id/tag, for
    the reconciliation UI."""
    data = load_event(event_slug)
    if not data:
        return []
    seen = {}
    for s in data.get("sets", {}).values():
        for side in ("p1", "p2"):
            p = s[side]
            if p.get("player_id"):
                continue
            key = ("u:" + str(p["user_id"])) if p.get("user_id") else ("t:" + p.get("tag", ""))
            if key not in seen:
                seen[key] = {"tag": p.get("tag", ""), "user_id": p.get("user_id"),
                             "team": p.get("team", ""), "key": key}
    return list(seen.values())


def _winner_local(side_set, alias_resolver):
    """Determine which local player id won, resolving through aliases."""
    p1 = side_set["p1"]
    p2 = side_set["p2"]
    w_uid = side_set.get("winner_user_id")
    w_eid = side_set.get("winner_entrant_id")
    p1_local = alias_resolver(p1)
    p2_local = alias_resolver(p2)
    winner_local = None
    if w_uid is not None and p1.get("user_id") == w_uid:
        winner_local = p1_local
    elif w_uid is not None and p2.get("user_id") == w_uid:
        winner_local = p2_local
    elif w_eid is not None and p1.get("entrant_id") == w_eid:
        winner_local = p1_local
    elif w_eid is not None and p2.get("entrant_id") == w_eid:
        winner_local = p2_local
    return p1_local, p2_local, winner_local


def rebuild_alltime(alias_map=None):
    """Regenerate the all-time rollup from every event file.

    alias_map: optional {raw_player_id -> canonical_player_id} from
        the merge system, applied so merged players unify retroactively.
    Produces nested {pid: {opponent_pid: {wins, losses}}} plus a flat
    set list per pair for drill-down.
    """
    _ensure_dir()
    alias_map = alias_map or {}

    def canon(pid):
        return alias_map.get(pid, pid) if pid else None

    def resolver(entrant):
        return canon(entrant.get("player_id"))

    # Nested by game: {game: {pid: {opp: {wins, losses}}}}
    rollup = {}

    def _bump(game, a, b, a_won):
        if not a or not b:
            return
        g = rollup.setdefault(game or "", {})
        g.setdefault(a, {}).setdefault(b, {"wins": 0, "losses": 0})
        if a_won:
            g[a][b]["wins"] += 1
        else:
            g[a][b]["losses"] += 1

    for ev in list_events():
        data = load_event(ev["event_slug"])
        if not data:
            continue
        game = (data.get("game") or "").strip()
        for s in data.get("sets", {}).values():
            p1_local, p2_local, winner_local = _winner_local(s, resolver)
            if not p1_local or not p2_local or winner_local is None:
                continue  # unreconciled or unknown winner -> not counted
            _bump(game, p1_local, p2_local, winner_local == p1_local)
            _bump(game, p2_local, p1_local, winner_local == p2_local)

    payload = {"matchups_by_game": rollup}
    with open(ALLTIME_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return rollup


def alltime_record(pid_a, pid_b, game=None):
    """All-time (wins, losses) for pid_a against pid_b in a game.

    game: filter to this game tag. If None/empty, sums across all games
    (legacy behavior) -- callers should normally pass the current game.
    """
    if not os.path.exists(ALLTIME_FILE):
        return 0, 0
    with open(ALLTIME_FILE, encoding="utf-8") as f:
        by_game = json.load(f).get("matchups_by_game", {})
    game = (game or "").strip()
    if game:
        rec = by_game.get(game, {}).get(pid_a, {}).get(pid_b)
        if not rec:
            return 0, 0
        return rec.get("wins", 0), rec.get("losses", 0)
    # No game specified: sum every game
    wins = losses = 0
    for g in by_game.values():
        rec = g.get(pid_a, {}).get(pid_b)
        if rec:
            wins += rec.get("wins", 0)
            losses += rec.get("losses", 0)
    return wins, losses


def event_placement(event_slug, pid, alias_map=None):
    """Final placement of a player in an event, or None.

    Resolves through alias_map (merges) and also checks placement rows
    that were keyed by raw start.gg id before reconciliation."""
    alias_map = alias_map or {}
    data = load_event(event_slug)
    if not data:
        return None
    placements = data.get("placements", {})
    canon = alias_map.get(pid, pid)
    # Direct id key
    for key in (canon, pid):
        if key in placements:
            return placements[key].get("placement")
    # Fall back: a placement row whose resolved player_id matches
    for row in placements.values():
        rp = row.get("player_id")
        if rp and alias_map.get(rp, rp) == canon:
            return row.get("placement")
    return None


def event_record(event_slug, pid_a, pid_b, alias_map=None, game=None):
    """(wins, losses) for pid_a vs pid_b within a single event.

    game: if given, returns 0-0 when the event isn't that game."""
    alias_map = alias_map or {}

    def canon(pid):
        return alias_map.get(pid, pid) if pid else None

    def resolver(entrant):
        return canon(entrant.get("player_id"))

    data = load_event(event_slug)
    if not data:
        return 0, 0
    game = (game or "").strip()
    if game and (data.get("game") or "").strip() != game:
        return 0, 0
    wins = losses = 0
    for s in data.get("sets", {}).values():
        p1_local, p2_local, winner_local = _winner_local(s, resolver)
        pair = {p1_local, p2_local}
        if pair != {pid_a, pid_b}:
            continue
        if winner_local == pid_a:
            wins += 1
        elif winner_local == pid_b:
            losses += 1
    return wins, losses


def list_series():
    """Distinct non-empty series names across all events, sorted."""
    names = set()
    for ev in list_events():
        s = (ev.get("series") or "").strip()
        if s:
            names.add(s)
    return sorted(names, key=lambda x: x.lower())


def set_event_series(event_slug, series):
    """Set/clear an event's series tag in place. Returns True if written."""
    data = load_event(event_slug)
    if not data:
        return False
    data["series"] = (series or "").strip()
    with open(_slug_to_filename(event_slug), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def set_event_game(event_slug, game):
    """Set/clear an event's game tag in place. Returns True if written."""
    data = load_event(event_slug)
    if not data:
        return False
    data["game"] = (game or "").strip()
    with open(_slug_to_filename(event_slug), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True


def list_games_with_events():
    """Distinct game tags across imported events, sorted."""
    games = set()
    for ev in list_events():
        g = (ev.get("game") or "").strip()
        if g:
            games.add(g)
    return sorted(games, key=lambda x: x.lower())


def series_record(series, pid_a, pid_b, alias_map=None, game=None):
    """(wins, losses) for pid_a vs pid_b across all events in a series.

    game: if given, only counts events tagged with that game."""
    alias_map = alias_map or {}
    game = (game or "").strip()

    def canon(pid):
        return alias_map.get(pid, pid) if pid else None

    def resolver(entrant):
        return canon(entrant.get("player_id"))

    target = (series or "").strip().lower()
    wins = losses = 0
    for ev in list_events():
        if (ev.get("series") or "").strip().lower() != target:
            continue
        if game and (ev.get("game") or "").strip() != game:
            continue
        data = load_event(ev["event_slug"])
        if not data:
            continue
        for s in data.get("sets", {}).values():
            p1_local, p2_local, winner_local = _winner_local(s, resolver)
            pair = {p1_local, p2_local}
            if pair != {pid_a, pid_b}:
                continue
            if winner_local == pid_a:
                wins += 1
            elif winner_local == pid_b:
                losses += 1
    return wins, losses