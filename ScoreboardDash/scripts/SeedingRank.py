"""Seeding rank computation from imported match history.

Given a set of imported events (filtered to a scope) and the placements
within each, produce a suggested seed order for a list of players, using
placement points with an optional recency/absence decay.

This is pure computation -- it takes plain event dicts (as produced by
MatchHistory.load_event) and returns ranked data. No I/O here, so it's
easy to unit-test.

POINTS MODEL
------------
Each event placement converts to points via a curved scale (better
placements earn disproportionately more, with diminishing returns lower
down). The curve is configurable; default is an inverse-style curve.

DECAY MODES
-----------
- "none"      : every event counts at full weight (pure cumulative points).
- "absence"   : a player's results are discounted once that result has
                >= threshold events (in scope) that the player DID NOT
                enter occurring AFTER it. Recent attendance "refreshes"
                standing -- a regular never decays; a returning player's
                pre-gap results are discounted but new ones count full.
                (Interpretation 1.)
- "recency"   : calendar-style -- the most recent event counts full and
                each older event counts a bit less (geometric falloff by
                position in the scoped timeline), regardless of attendance.

Events are ordered oldest -> newest by their `imported_at` timestamp.
Note: imported_at is the IMPORT time, which tracks event time closely for
events imported as they happen, but can be misleading if old events were
bulk-imported later. Callers should surface that caveat.
"""


def placement_points(placement, curve="standard"):
    """Convert a final placement (1 = best) into a point value.

    Curves:
      "standard" : 1st=100, then a diminishing curve (100 / placement-ish
                   but softened so 1st >> 2nd while low places compress).
      "linear"   : simple inverse (higher placement = fewer points), gentle.
      "topheavy" : rewards the very top much more steeply.
    """
    if placement is None or placement < 1:
        return 0.0
    p = float(placement)
    if curve == "linear":
        # 1st=100, drops by a flat amount; floors at a small positive value
        return max(1.0, 100.0 - (p - 1.0) * 5.0)
    if curve == "topheavy":
        # steep: 100 / p^1.3
        return 100.0 / (p ** 1.3)
    # "standard": 100 / sqrt-softened placement -- 1st=100, 2nd~70, 3rd~58,
    # 4th=50, 8th~35, 16th~25, 32nd~18. Strong top, gentle tail.
    return 100.0 / (p ** 0.5)


def _event_sort_key(e):
    """Best available date for ordering: prefer the real event_date, fall back
    to imported_at so undated events still order sensibly."""
    return e.get("event_date") or e.get("imported_at") or ""


def _event_order(events):
    """Return events sorted oldest -> newest by their best date."""
    return sorted(events, key=_event_sort_key)


def _placement_for(event, player_id):
    """Look up a player's placement in one event's placements map.

    Mirrors MatchHistory.event_placement's primary paths but operates on
    an already-loaded event dict. Returns int placement or None.
    """
    placements = event.get("placements", {}) or {}
    # direct local-id key
    row = placements.get(player_id)
    if row and row.get("placement") is not None:
        return row.get("placement")
    # a row whose resolved player_id matches
    for r in placements.values():
        if r.get("player_id") == player_id and r.get("placement") is not None:
            return r.get("placement")
    return None


def _attended(event, player_id):
    """Did this player enter this event (appear in its placements)?"""
    return _placement_for(event, player_id) is not None


def compute_player_score(player_id, events_oldest_first, curve="standard",
                         decay_mode="none", threshold=2, recency_factor=0.85):
    """Compute a player's total seed score across scoped events.

    Returns a dict: {
       points: float,                 # total weighted points
       events_counted: int,           # events the player placed in
       placements: [ {label, placement, raw_points, weight, weighted} ],
    }
    `events_oldest_first` must be pre-sorted oldest -> newest.
    """
    n = len(events_oldest_first)
    detail = []
    total = 0.0
    counted = 0

    # Pre-compute, for the "absence" mode, how many events AFTER each index
    # the player did not attend.
    for i, ev in enumerate(events_oldest_first):
        placement = _placement_for(ev, player_id)
        if placement is None:
            continue  # didn't enter this event
        counted += 1
        raw = placement_points(placement, curve)

        weight = 1.0
        if decay_mode == "none":
            weight = 1.0
        elif decay_mode == "recency":
            # newest event (highest index) = full; each older step *factor.
            steps_from_newest = (n - 1) - i
            weight = recency_factor ** steps_from_newest
        elif decay_mode == "absence":
            # count events AFTER this one that the player did NOT enter
            missed_after = 0
            for j in range(i + 1, n):
                if not _attended(events_oldest_first[j], player_id):
                    missed_after += 1
            # full weight until missed_after reaches threshold, then decay
            if missed_after < threshold:
                weight = 1.0
            else:
                # each missed event beyond the threshold halves the weight
                over = missed_after - threshold + 1
                weight = 0.5 ** over

        weighted = raw * weight
        total += weighted
        detail.append({
            "label": ev.get("label") or ev.get("event_slug") or "",
            "placement": placement,
            "raw_points": round(raw, 1),
            "weight": round(weight, 3),
            "weighted": round(weighted, 1),
        })

    return {
        "points": round(total, 1),
        "events_counted": counted,
        "placements": detail,
    }


def rank_players(player_ids, events, curve="standard", decay_mode="none",
                 threshold=2, recency_factor=0.85):
    """Rank a list of local player_ids by computed score (desc).

    `events` is a list of event dicts (each must include placements and
    imported_at). Returns a list of {player_id, points, events_counted,
    placements} sorted best-first. Players with zero counted events get
    points 0 -- callers decide whether to separate those out.
    """
    ordered = _event_order(events)
    results = []
    for pid in player_ids:
        sc = compute_player_score(pid, ordered, curve, decay_mode,
                                  threshold, recency_factor)
        sc["player_id"] = pid
        results.append(sc)
    # sort by points desc, then by events_counted desc as a tiebreak
    results.sort(key=lambda r: (r["points"], r["events_counted"]), reverse=True)
    return results