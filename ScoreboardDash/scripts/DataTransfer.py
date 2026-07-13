"""Export / import of the local player database and match history.

Produces a single transparent JSON "bundle" that can be moved between
machines (prep on one computer, carry to the venue laptop). The bundle can
contain the player DB, the match history, or both -- selectable at export.

Bundle shape:
{
  "format": "scoreboarddash-bundle",
  "version": 1,
  "exported_at": "<iso>",
  "contents": ["players", "history"],     # what's actually included
  "players": { <player_id>: {...}, ... } | null,
  "games":   { <game_name>: <char_slots>, ... } | null,
  "events":  [ { ...full event payload... }, ... ] | null
}

The derived _alltime.json rollup is intentionally NOT exported -- it's
regenerated from the per-event files on import, so a stale/corrupt rollup
can't travel between machines.

This module only builds/parses bundle dicts and reads/writes via the
existing PlayerStatsDB + MatchHistory APIs; the server handles HTTP, file
download, and the auto-backup-before-import safeguard.
"""

import json
import os
from datetime import datetime

BUNDLE_FORMAT = "scoreboarddash-bundle"
BUNDLE_VERSION = 1


def _clean_games(games):
    """Sanitize a {game: slots} map via InputValidation (clamps slots 1..8,
    trims/caps names). Falls back to the raw map if validation is unavailable."""
    try:
        from scripts import InputValidation
        return InputValidation.sanitize_games(games)
    except Exception:
        return games or {}


def build_bundle(players_db, match_history, include_players=True,
                 include_history=True):
    """Build an export bundle dict.

    players_db   -- the PlayerStatsDB module (get_local_players, get_games)
    match_history-- the MatchHistory module (list_events, load_event)
    include_*    -- which sections to include.
    """
    contents = []
    bundle = {
        "format": BUNDLE_FORMAT,
        "version": BUNDLE_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "contents": contents,
        "players": None,
        "games": None,
        "events": None,
    }

    if include_players:
        bundle["players"] = players_db.get_local_players()
        # games table travels with the player DB (rosters/characters key off it)
        try:
            bundle["games"] = players_db.get_games()
        except Exception:
            bundle["games"] = {}
        contents.append("players")

    if include_history:
        events = []
        for meta in match_history.list_events():
            data = match_history.load_event(meta["event_slug"])
            if data:
                events.append(data)
        bundle["events"] = events
        contents.append("history")

    return bundle


def bundle_summary(bundle):
    """A short human-readable description of what a parsed bundle holds.

    Used by the import flow to show the user what they're about to bring in
    before they commit. Returns a dict of counts + metadata."""
    players = bundle.get("players") or {}
    events = bundle.get("events") or []
    return {
        "format_ok": bundle.get("format") == BUNDLE_FORMAT,
        "version": bundle.get("version"),
        "exported_at": bundle.get("exported_at", ""),
        "contents": bundle.get("contents", []),
        "player_count": len(players),
        "event_count": len(events),
        "game_count": len(bundle.get("games") or {}),
    }


def validate_bundle(bundle):
    """Return (ok, message). Checks the bundle is the right format/version
    and structurally sane before we let it touch the destination."""
    if not isinstance(bundle, dict):
        return False, "Not a valid bundle (expected a JSON object)."
    if bundle.get("format") != BUNDLE_FORMAT:
        return False, "This file isn't a ScoreboardDash bundle."
    if bundle.get("version", 0) > BUNDLE_VERSION:
        return False, ("Bundle was made by a newer version (v%s); this app "
                       "supports up to v%s." % (bundle.get("version"), BUNDLE_VERSION))
    if bundle.get("players") is None and not bundle.get("events"):
        return False, "Bundle contains no player data or match history."
    return True, "OK"


# ── RESTORE ───────────────────────────────────────────────────────────

def write_auto_backup(players_db, match_history, backup_dir):
    """Before any import, dump the destination's CURRENT full state to a
    timestamped bundle file so the import is reversible. Returns the path."""
    os.makedirs(backup_dir, exist_ok=True)
    bundle = build_bundle(players_db, match_history, True, True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(backup_dir, "auto-backup-%s.json" % stamp)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    return path


def restore_players(players_db, bundle):
    """Replace the player DB with the bundle's players + games.

    save_local_players reconciles to exactly the passed dict (deletes ids not
    present), so this is a true replace. Games are upserted from the bundle."""
    players = bundle.get("players")
    if players is None:
        return 0
    # restore games first so rosters/characters have their game rows
    for name, slots in _clean_games(bundle.get("games")).items():
        try:
            players_db.set_game_slots(name, slots)
        except Exception as e:
            print("restore_players: game %r failed (%s)" % (name, e))
    players_db.save_local_players(players)
    return len(players)


def restore_history_replace(match_history, bundle):
    """Wipe all event files and write the bundle's events, then rebuild the
    all-time rollup. Returns the number of events written."""
    events = bundle.get("events")
    if events is None:
        return 0
    _wipe_event_files(match_history)
    return _write_events(match_history, events)


def _wipe_event_files(match_history):
    """Delete every per-event file AND the derived rollup from the matchup
    dir. Only touches .json files in that directory."""
    d = match_history.MATCHUP_DIR
    if not os.path.isdir(d):
        return
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            try:
                os.remove(os.path.join(d, fn))
            except OSError as e:
                print("_wipe_event_files: could not remove %s (%s)" % (fn, e))


def _write_events(match_history, events):
    """Write each event dict to its slug-derived file. Skips the derived
    rollup if one somehow appears in the list. Rebuilds all-time after."""
    match_history._ensure_dir()
    written = 0
    for ev in events:
        slug = ev.get("event_slug")
        if not slug:
            continue
        path = match_history._slug_to_filename(slug)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ev, f, ensure_ascii=False, indent=2)
        written += 1
    return written


# ── MERGE ─────────────────────────────────────────────────────────────
# Merge combines a bundle into the EXISTING data instead of replacing it.
# Player matching uses three tiers so we only bother the user when unsure:
#   confident -> auto-merge, none -> auto-add, ambiguous -> ask.
# History merges by slug (bundle wins on conflict). Because events reference
# players by the SOURCE machine's player_id, we build a remap
# (source_pid -> final_pid) from the merge decisions and REWRITE those ids in
# the imported events, so merged history resolves natively on the destination.

def _norm(s):
    return (s or "").strip().lower()


def _sgg_aliases(rec):
    """The start.gg account aliases (sgg:<id>) on a player record."""
    return set(a.lower() for a in (rec.get("aliases") or []) if a.lower().startswith("sgg:"))


def _all_ids(rec):
    """Everything that identifies a player: their name + all aliases,
    lower-cased. Used for overlap detection."""
    ids = set(a.lower() for a in (rec.get("aliases") or []))
    if rec.get("name"):
        ids.add(_norm(rec["name"]))
    return ids


def analyze_merge(dest_players, bundle):
    """Classify each incoming player against the destination.

    Returns {
      confident: [ {source_id, name, target_id, target_name, reason} ],
      new:       [ {source_id, name} ],
      ambiguous: [ {source_id, name, aliases, candidates:[{id,name,reason}]} ],
    }
    Does NOT modify anything -- this drives the UI's resolution step.
    """
    incoming = bundle.get("players") or {}
    confident, new, ambiguous = [], [], []

    for sid, inc in incoming.items():
        inc_sgg = _sgg_aliases(inc)
        inc_ids = _all_ids(inc)
        inc_name = _norm(inc.get("name"))

        # Gather candidate destination players by any identity signal.
        cands = []
        for did, dp in dest_players.items():
            reasons = []
            d_sgg = _sgg_aliases(dp)
            if inc_sgg and (inc_sgg & d_sgg):
                reasons.append("account")          # same start.gg user id
            if inc_name and inc_name == _norm(dp.get("name")):
                reasons.append("name")
            if (inc_ids & _all_ids(dp)) - {""}:
                # alias overlap beyond just the name signal already counted
                if "name" not in reasons or len(inc_ids & _all_ids(dp)) > 1:
                    reasons.append("alias")
            if reasons:
                cands.append({"id": did, "name": dp.get("name", did), "reasons": reasons})

        if not cands:
            new.append({"source_id": sid, "name": inc.get("name", sid)})
            continue

        # Confident: exactly one candidate that matches on account (sgg id),
        # OR exactly one candidate matching on BOTH name and an alias.
        strong = [c for c in cands
                  if "account" in c["reasons"] or ("name" in c["reasons"] and "alias" in c["reasons"])]
        if len(cands) == 1 and len(strong) == 1:
            c = cands[0]
            confident.append({"source_id": sid, "name": inc.get("name", sid),
                              "target_id": c["id"], "target_name": c["name"],
                              "reason": "+".join(c["reasons"])})
        else:
            ambiguous.append({"source_id": sid, "name": inc.get("name", sid),
                              "aliases": inc.get("aliases", []),
                              "candidates": [{"id": c["id"], "name": c["name"],
                                              "reason": "+".join(c["reasons"])} for c in cands]})

    return {"confident": confident, "new": new, "ambiguous": ambiguous}


def _merge_player_into(dest_rec, inc_rec):
    """Merge incoming player fields into an existing destination record
    (additive/non-destructive): union aliases + add incoming name as alias;
    union characters/roster per game (destination wins on a game both have);
    fill empty core fields from incoming."""
    # aliases: union, plus the incoming name becomes an alias if different
    existing = set(a.lower() for a in dest_rec.get("aliases", []))
    for a in (inc_rec.get("aliases") or []):
        if a.lower() not in existing and a.lower() != _norm(dest_rec.get("name")):
            dest_rec.setdefault("aliases", []).append(a); existing.add(a.lower())
    inc_name = inc_rec.get("name")
    if inc_name and _norm(inc_name) != _norm(dest_rec.get("name")) and _norm(inc_name) not in existing:
        dest_rec.setdefault("aliases", []).append(inc_name)
    # characters / roster: add games the destination doesn't already have
    for field in ("characters", "roster"):
        dinc = inc_rec.get(field) or {}
        dcur = dest_rec.setdefault(field, {})
        for game, val in dinc.items():
            if game not in dcur:
                dcur[game] = val
    # core fields: fill only if empty on destination
    for field in ("team", "country", "state", "state_id", "city", "social_handle", "social_platform"):
        if not dest_rec.get(field) and inc_rec.get(field):
            dest_rec[field] = inc_rec[field]


def apply_merge(players_db, match_history, bundle, resolutions,
                do_players=True, do_history=True, next_id_fn=None):
    """Apply a merge. `resolutions` maps ambiguous source_id -> decision:
      {"action": "merge", "target_id": "<dest_pid>"} or {"action": "new"}.
    Confident matches auto-merge; unlisted no-match players auto-add.

    Builds source_pid -> final_pid remap and rewrites imported events'
    player_id references so merged history resolves natively. Returns a
    result summary dict."""
    resolutions = resolutions or {}
    remap = {}          # source_pid -> final destination pid
    merged_ct = added_ct = 0

    if do_players and bundle.get("players") is not None:
        dest = players_db.get_local_players()
        # restore games first (union)
        for name, slots in _clean_games(bundle.get("games")).items():
            try: players_db.set_game_slots(name, slots)
            except Exception as e: print("apply_merge game %r: %s" % (name, e))

        plan = analyze_merge(dest, bundle)
        incoming = bundle.get("players") or {}

        # confident -> merge into target
        for item in plan["confident"]:
            sid, tid = item["source_id"], item["target_id"]
            _merge_player_into(dest[tid], incoming[sid])
            remap[sid] = tid; merged_ct += 1
        # no-match -> add as new (fresh non-colliding id)
        for item in plan["new"]:
            sid = item["source_id"]
            nid = next_id_fn(dest) if next_id_fn else sid
            rec = dict(incoming[sid]); rec["id"] = nid
            dest[nid] = rec; remap[sid] = nid; added_ct += 1
        # ambiguous -> follow the user's resolution
        for item in plan["ambiguous"]:
            sid = item["source_id"]
            decision = resolutions.get(sid) or {"action": "new"}
            if decision.get("action") == "merge" and decision.get("target_id") in dest:
                tid = decision["target_id"]
                _merge_player_into(dest[tid], incoming[sid])
                remap[sid] = tid; merged_ct += 1
            else:
                nid = next_id_fn(dest) if next_id_fn else sid
                rec = dict(incoming[sid]); rec["id"] = nid
                dest[nid] = rec; remap[sid] = nid; added_ct += 1

        players_db.save_local_players(dest)

    events_ct = 0
    if do_history and bundle.get("events") is not None:
        for ev in bundle["events"]:
            _remap_event_ids(ev, remap)
            slug = ev.get("event_slug")
            if not slug:
                continue
            # bundle wins on slug conflict (just overwrite that event file)
            with open(match_history._slug_to_filename(slug), "w", encoding="utf-8") as f:
                json.dump(ev, f, ensure_ascii=False, indent=2)
            events_ct += 1

    return {"players_merged": merged_ct, "players_added": added_ct,
            "events_imported": events_ct}


def _remap_event_ids(ev, remap):
    """Rewrite source player_ids to final ids in one event's placements/sets,
    so merged history references the destination's players. In-place."""
    if not remap:
        return
    # placements: dict keyed by player_id, with player_id inside each row
    placements = ev.get("placements") or {}
    new_pl = {}
    for key, row in placements.items():
        pid = row.get("player_id")
        final = remap.get(pid, pid)
        row["player_id"] = final
        new_pl[remap.get(key, key)] = row
    ev["placements"] = new_pl
    # sets: p1/p2 each carry a player_id
    for s in (ev.get("sets") or {}).values():
        for slot in ("p1", "p2"):
            if s.get(slot) and s[slot].get("player_id") in remap:
                s[slot]["player_id"] = remap[s[slot]["player_id"]]