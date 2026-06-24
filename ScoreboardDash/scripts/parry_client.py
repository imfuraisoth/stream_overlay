"""parry.gg API client.

Fetches completed matches + placements from a parry.gg event and
normalizes them into the SAME dict shape startgg_client produces, so
MatchHistory / reconciliation / rollup / H2H all consume it unchanged.

parry.gg is gRPC/protobuf but callable as plain JSON-over-HTTP:
  POST https://grpcweb.parry.gg/parrygg.services.{Service}/{Method}
  headers: Content-Type: application/json, X-API-KEY: <key>
  body: JSON of the proto request message, fields lowerCamelCase.

STATUS: written against the published protos (verified Jun 2026) but
NOT yet run against a live event. Field access is defensive; the spots
most likely to need adjustment against real data are marked LIVE-CHECK.
See parry-gg-integration-design.md.
"""

import os
import json
import requests

BASE = "https://grpcweb.parry.gg"

# API key file lives beside the start.gg token in data/, same naming.
_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "../data/parry_token.txt")


def get_api_key():
    try:
        with open(_KEY_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _post(service, method, body=None):
    """POST a JSON-over-HTTP call. Returns (data_dict, error_str)."""
    url = BASE + "/parrygg.services." + service + "/" + method
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": get_api_key(),
    }
    try:
        resp = requests.post(url, json=(body or {}), headers=headers, timeout=30)
    except Exception as e:
        return None, "request failed: " + str(e)
    if resp.status_code != 200:
        # Errors come back non-200 with a JSON message.
        msg = ""
        try:
            msg = resp.json().get("message", "")
        except Exception:
            msg = (resp.text or "")[:300]
        return None, "HTTP %s: %s" % (resp.status_code, msg)
    try:
        return resp.json(), None
    except Exception:
        return None, "non-JSON response: " + (resp.text or "")[:300]


# ── helpers ──────────────────────────────────────────────────────────

def _event_identifier(tournament_slug, event_slug):
    """Build an EventIdentifier for MatchesFilter.

    LIVE-CHECK: EventIdentifier's exact JSON shape isn't confirmed from
    the schema (models/event.proto wasn't read). The proto pattern used
    elsewhere is a oneof {id, slug_id:{...}} or {id, slug}. We send a
    slug_id with the tournament+event slugs, which mirrors BracketSlugId.
    If live data rejects this, inspect a real EventIdentifier and adjust.
    """
    return {
        "eventSlugPath": {
            "tournamentSlug": tournament_slug,
            "eventSlug": event_slug,
        }
    }


def _seed_user(seed):
    """From a Seed -> {tag, team, entrant_id, user_id, country}.

    Verified against live parry data: the display name is the first
    user's gamerTag (EventEntrant.name is not populated). Country comes
    from users[0].locationCountry. Team is parsed from a "Team | Tag"
    gamerTag if present, matching the start.gg convention.
    """
    ee = (seed or {}).get("eventEntrant") or {}
    entrant = ee.get("entrant") or {}
    users = entrant.get("users") or []
    u0 = users[0] if users else {}
    user_id = u0.get("id")
    name = (u0.get("gamerTag") or "").strip()
    team = ""
    if " | " in name:
        team, name = name.split(" | ", 1)
    country = (u0.get("locationCountry") or "US").strip() or "US"
    return {
        "tag": name.strip(),
        "team": team.strip(),
        "entrant_id": ee.get("id") or entrant.get("id"),
        "user_id": user_id,
        "country": country,
    }


def _seeds_by_id(match_context):
    """Map seed_id -> seed for resolving match slots to entrants."""
    out = {}
    for s in (match_context.get("seeds") or []):
        sid = s.get("id")
        if sid:
            out[sid] = s
    return out


def _is_completed(match):
    """True if the match is finished. Accepts string or int enum form."""
    st = match.get("state")
    return st in ("MATCH_STATE_COMPLETED", 4)


def _slot_score(slot):
    v = slot.get("score")
    try:
        return int(round(float(v))) if v is not None else None
    except (TypeError, ValueError):
        return None


# ── main entry points ────────────────────────────────────────────────

def get_completed_matches(tournament_slug, event_slug):
    """All completed matches for an event, normalized like start.gg sets.

    Returns (results_list, error_str). Each result:
      { set_id, round_name, round, full_round_text, event_name,
        tournament_name, completed_at, p1, p2, p1_score, p2_score,
        winner_entrant_id, winner_user_id }
    Matches without two resolvable entrants, or byes, are skipped.
    """
    body = {
        "filter": {
            "event": _event_identifier(tournament_slug, event_slug),
            # LIVE-CHECK: enum as string; if rejected, try the int 4.
            "state": "MATCH_STATE_COMPLETED",
        }
    }
    data, err = _post("MatchService", "GetMatches", body)
    if err:
        return None, err

    contexts = data.get("matches") or []
    results = []
    for ctx in contexts:
        match = ctx.get("match") or {}
        if not _is_completed(match):
            continue
        slots = match.get("slots") or []
        if len(slots) != 2:
            continue  # byes / malformed

        seeds = _seeds_by_id(ctx)
        # Slots carry a 'slot' index (0 or 1); slot 0 may omit the field.
        by_slot = {}
        for sl in slots:
            by_slot[sl.get("slot", 0)] = sl
        s0 = by_slot.get(0) or slots[0]
        s1 = by_slot.get(1) or slots[1]
        e1 = _seed_user(seeds.get(s0.get("seedId")))
        e2 = _seed_user(seeds.get(s1.get("seedId")))
        # Skip if either side won't resolve to a real entrant
        if not e1["entrant_id"] or not e2["entrant_id"]:
            continue
        # Skip byes
        if s0.get("state") == "SLOT_STATE_BYE" or s1.get("state") == "SLOT_STATE_BYE":
            continue

        # Scores: a missing score field means 0 (verified -- the winning
        # slot sometimes carries score:3 while the loser omits score).
        sc1 = _slot_score(s0) or 0
        sc2 = _slot_score(s1) or 0

        # Winner = higher score. (In parry data the per-slot 'placement'
        # field is a bracket/standings marker, NOT the match winner, so
        # score is the reliable signal.) A DQ leaves the other as winner.
        winner_entrant_id = None
        winner_user_id = None
        if s0.get("state") == "SLOT_STATE_DQ" and s1.get("state") != "SLOT_STATE_DQ":
            winner_entrant_id, winner_user_id = e2["entrant_id"], e2["user_id"]
        elif s1.get("state") == "SLOT_STATE_DQ" and s0.get("state") != "SLOT_STATE_DQ":
            winner_entrant_id, winner_user_id = e1["entrant_id"], e1["user_id"]
        elif sc1 != sc2:
            if sc1 > sc2:
                winner_entrant_id, winner_user_id = e1["entrant_id"], e1["user_id"]
            else:
                winner_entrant_id, winner_user_id = e2["entrant_id"], e2["user_id"]
        if winner_entrant_id is None:
            continue  # tied/unknown -> not a usable completed set

        # Round label: prefer the embedded Round.label, else match.round.
        rnd = ctx.get("round") or {}
        round_label = rnd.get("label") or ""
        # Event/tournament names live in hierarchy.paths[]: the EVENT path
        # has type PATH_TYPE_EVENT; the tournament is the path with no type.
        ev_name = event_slug
        tourn = tournament_slug
        for p in ((ctx.get("hierarchy") or {}).get("paths") or []):
            ptype = p.get("type")
            if ptype == "PATH_TYPE_EVENT":
                ev_name = p.get("name") or ev_name
            elif not ptype:  # the tournament path carries no type
                tourn = p.get("name") or tourn

        results.append({
            "set_id": str(match.get("id")),
            "round_name": round_label or str(match.get("round") or ""),
            "round": match.get("round"),
            "full_round_text": round_label,
            "event_name": ev_name,
            "tournament_name": tourn,
            "completed_at": match.get("endedAt"),
            "p1": e1,
            "p2": e2,
            "p1_score": sc1,
            "p2_score": sc2,
            "winner_entrant_id": winner_entrant_id,
            "winner_user_id": winner_user_id,
        })
    return results, None


def get_event_standings(tournament_slug, event_slug):
    """Final placements for an event, shape-matched to start.gg's.

    Returns (list, error). Each row:
      { placement, tag, team, user_id, entrant_id, wins, losses }

    Primary path: EventService/GetEventPlacements -- parry's own
    authoritative standings, with win/loss records. Verified against a
    real bracket (placements + W/L matched exactly). Falls back to
    deriving from match data if the placements call returns nothing.
    """
    body = {
        "eventSlugPath": {
            "tournamentSlug": tournament_slug,
            "eventSlug": event_slug,
        }
    }
    data, err = _post("EventService", "GetEventPlacements", body)
    if err:
        # Fall back to match-derived standings on error.
        return _derive_standings_from_matches(tournament_slug, event_slug)

    placements = data.get("placements") or []
    out = []
    for p in placements:
        ee = p.get("eventEntrant") or {}
        entrant = ee.get("entrant") or {}
        users = entrant.get("users") or []
        u0 = users[0] if users else {}
        uid = u0.get("id")
        if not uid:
            continue
        name = (u0.get("gamerTag") or "").strip()
        team = ""
        if " | " in name:
            team, name = name.split(" | ", 1)
        try:
            place = int(p.get("placement")) if p.get("placement") is not None else None
        except (TypeError, ValueError):
            place = None
        if place is None or place <= 0:
            continue
        out.append({
            "placement": place,
            "tag": name.strip(),
            "team": team.strip(),
            "user_id": uid,
            "entrant_id": ee.get("id") or entrant.get("id"),
            "wins": int(p.get("wins") or 0),
            "losses": int(p.get("losses") or 0),
        })
    if not out:
        # Empty placements (e.g. event not finalized) -> derive.
        return _derive_standings_from_matches(tournament_slug, event_slug)
    out.sort(key=lambda r: r["placement"])
    return out, None


def _derive_standings_from_matches(tournament_slug, event_slug):
    """Fallback: reconstruct standings from match data when the direct
    GetEventPlacements call is unavailable or empty.

    A player's placement is the best (min) losersPlacement among matches
    they lost; the winner of the final match (latest endedAt) is 1st.
    Verified to match a real double-elim bracket.
    """
    body = {"filter": {"event": _event_identifier(tournament_slug, event_slug)}}
    data, err = _post("MatchService", "GetMatches", body)
    if err:
        return None, err

    info = {}
    lost_place = {}
    last_ended = ""
    last_winner_uid = None
    for ctx in (data.get("matches") or []):
        match = ctx.get("match") or {}
        if not _is_completed(match):
            continue
        slots = match.get("slots") or []
        if len(slots) != 2:
            continue
        seeds = _seeds_by_id(ctx)
        by_slot = {}
        for sl in slots:
            by_slot[sl.get("slot", 0)] = sl
        s0 = by_slot.get(0) or slots[0]
        s1 = by_slot.get(1) or slots[1]
        e0 = _seed_user(seeds.get(s0.get("seedId")))
        e1 = _seed_user(seeds.get(s1.get("seedId")))
        if not e0["user_id"] or not e1["user_id"]:
            continue
        for e in (e0, e1):
            info.setdefault(e["user_id"], {"tag": e["tag"], "team": e["team"],
                                           "entrant_id": e["entrant_id"]})
        sc0 = _slot_score(s0) or 0
        sc1 = _slot_score(s1) or 0
        if s0.get("state") == "SLOT_STATE_DQ":
            win_e, lose_e = e1, e0
        elif s1.get("state") == "SLOT_STATE_DQ":
            win_e, lose_e = e0, e1
        elif sc0 == sc1:
            continue
        else:
            win_e, lose_e = (e0, e1) if sc0 > sc1 else (e1, e0)
        lp = match.get("losersPlacement")
        try:
            lp = int(lp) if lp is not None else None
        except (TypeError, ValueError):
            lp = None
        if lp is not None and lp > 0:
            uid = lose_e["user_id"]
            if uid not in lost_place or lp < lost_place[uid]:
                lost_place[uid] = lp
        ended = match.get("endedAt") or ""
        if ended >= last_ended:
            last_ended = ended
            last_winner_uid = win_e["user_id"]

    out = []
    for uid, meta in info.items():
        if uid == last_winner_uid:
            place = 1
        elif uid in lost_place:
            place = lost_place[uid]
        else:
            continue
        out.append({
            "placement": place, "tag": meta["tag"], "team": meta["team"],
            "user_id": uid, "entrant_id": meta["entrant_id"],
            "wins": 0, "losses": 0,
        })
    out.sort(key=lambda r: r["placement"])
    return out, None


def get_game_slug(tournament_slug, event_slug):
    """Best-effort: the game slug for an event (one GetMatches call).

    Returns (slug_or_empty, error). Useful for auto-tagging the import
    to a game folder. LIVE-CHECK: MatchContext.game.slug path.
    """
    body = {"filter": {"event": _event_identifier(tournament_slug, event_slug)}}
    data, err = _post("MatchService", "GetMatches", body)
    if err:
        return "", err
    for ctx in (data.get("matches") or []):
        game = ctx.get("game") or {}
        slug = game.get("slug")
        if slug:
            return slug, None
    return "", None