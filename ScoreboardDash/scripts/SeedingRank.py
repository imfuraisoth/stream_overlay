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


# ── REMATCH DETECTION ─────────────────────────────────────────────────
# start.gg builds standard single-elim brackets with the "opposite ends"
# rule: seed 1 and seed 2 sit at far ends and only meet in the final, and in
# general two seeds meet in a round determined by their positions in the
# standard bracket order. We can't control the bracket (the tool only outputs
# a seed ORDER the TO types in), but given the seed order + entrant count we
# can PREDICT which pairs would meet early, cross-reference prior meetings from
# history, and flag likely early rematches -- weighted so a more recent prior
# meeting matters more than an old one.

def _next_pow2(n):
    p = 1
    while p < n:
        p *= 2
    return max(p, 2)


def standard_bracket_order(size):
    """Seed numbers in bracket-SLOT order for a standard single-elim bracket
    of the given (power-of-two) size -- the "opposite ends" placement.

    e.g. size 4 -> [1,4,2,3]; size 8 -> [1,8,4,5,2,7,3,6]. The list index is
    the bracket slot; the value is the seed sitting in that slot."""
    order = [1, 2]
    while len(order) < size:
        m = len(order) * 2
        nxt = []
        for s in order:
            nxt.append(s)
            nxt.append(m + 1 - s)
        order = nxt
    return order


def meeting_round(slot_a, slot_b, size):
    """Round (1 = first round) in which two bracket slots would meet, assuming
    both keep winning. size is the bracket size (power of two)."""
    r = 1
    block = 2
    while block <= size:
        if slot_a // block == slot_b // block:
            return r
        r += 1
        block *= 2
    return r  # they'd meet in the final


def _pair_key(a, b):
    return (a, b) if a <= b else (b, a)


def prior_meetings(seeded_ids, events_oldest_first):
    """Scan events for sets between two of the seeded players. Returns
    {(id_a,id_b): {"events_ago": int, "label": str, "date": str, "count": int}}
    where events_ago counts from the most recent event (0 = the newest event
    in scope). Only the MOST RECENT meeting per pair is recorded (plus a total
    count)."""
    idset = set(seeded_ids)
    n = len(events_oldest_first)
    out = {}
    for i, ev in enumerate(events_oldest_first):
        events_ago = (n - 1) - i     # 0 for the newest event
        for s in (ev.get("sets") or {}).values():
            p1 = (s.get("p1") or {}).get("player_id")
            p2 = (s.get("p2") or {}).get("player_id")
            if not p1 or not p2 or p1 not in idset or p2 not in idset:
                continue
            key = _pair_key(p1, p2)
            rec = out.get(key)
            if rec is None:
                out[key] = {"events_ago": events_ago,
                            "label": ev.get("label") or ev.get("event_slug") or "",
                            "date": ev.get("event_date") or "",
                            "count": 1}
            else:
                rec["count"] += 1
                # keep the most recent (smallest events_ago)
                if events_ago < rec["events_ago"]:
                    rec["events_ago"] = events_ago
                    rec["label"] = ev.get("label") or ev.get("event_slug") or ""
                    rec["date"] = ev.get("event_date") or ""
    return out


def detect_rematches(ranked, events, early_rounds=2, recency_factor=0.8,
                     lookback=0):
    """Find likely early rematches given a ranked seed list.

    ranked          -- list of {player_id, name, ...} in seed order (index 0 =
                       seed 1). name is optional; callers usually attach it.
    events          -- scoped event dicts (unordered ok; sorted here).
    early_rounds    -- flag pairs meeting in this round or earlier (1 = only
                       first-round rematches; 2 = first two rounds; etc.).
    recency_factor  -- 0..1 decay per event of age; a meeting `events_ago` old
                       gets weight recency_factor**events_ago. Higher factor =
                       older meetings still count.
    lookback        -- if > 0, ignore meetings older than this many events.

    Returns a list of flag dicts sorted worst-first:
      { a_seed, a_id, a_name, b_seed, b_id, b_name, round, bracket_size,
        events_ago, last_label, last_date, meetings, recency_weight, severity }
    """
    seed_of = {}          # player_id -> seed number (1-indexed)
    name_of = {}
    order_ids = []
    for i, r in enumerate(ranked):
        pid = r.get("player_id")
        if not pid:
            continue
        seed_of[pid] = i + 1
        name_of[pid] = r.get("name", pid)
        order_ids.append(pid)

    size = _next_pow2(len(order_ids))
    bracket = standard_bracket_order(size)
    # seed number -> slot index in the bracket
    slot_of_seed = {seed: slot for slot, seed in enumerate(bracket)}

    ordered = _event_order(events)
    meetings = prior_meetings(order_ids, ordered)

    flags = []
    for (a, b), info in meetings.items():
        if lookback and info["events_ago"] >= lookback:
            continue
        sa, sb = seed_of.get(a), seed_of.get(b)
        if not sa or not sb:
            continue
        slot_a = slot_of_seed.get(sa)
        slot_b = slot_of_seed.get(sb)
        if slot_a is None or slot_b is None:
            continue
        rnd = meeting_round(slot_a, slot_b, size)
        if rnd > early_rounds:
            continue
        rweight = recency_factor ** info["events_ago"]
        # severity: earlier round dominates; recency breaks ties / scales it.
        # (early_rounds - rnd + 1) is bigger for earlier rounds.
        severity = round((early_rounds - rnd + 1) * rweight, 4)
        flags.append({
            "a_seed": sa, "a_id": a, "a_name": name_of.get(a, a),
            "b_seed": sb, "b_id": b, "b_name": name_of.get(b, b),
            "round": rnd, "bracket_size": size,
            "events_ago": info["events_ago"],
            "last_label": info["label"], "last_date": info["date"],
            "meetings": info["count"],
            "recency_weight": round(rweight, 3),
            "severity": severity,
        })
    flags.sort(key=lambda f: f["severity"], reverse=True)
    return flags


def detect_state_clashes(ranked, early_rounds=2):
    """Find seeded players from the SAME state who'd meet early.

    Structurally like detect_rematches but pairs by shared state instead of
    prior meetings, and has no recency dimension (being from the same state
    isn't "recent" or "old"). Players with no state set are ignored.

    ranked        -- list of {player_id, name, state, ...} in seed order.
    early_rounds  -- flag pairs meeting in this round or earlier.

    Returns flags sorted worst-first (earliest round first):
      { a_seed, a_id, a_name, b_seed, b_id, b_name, state, round,
        bracket_size, severity }
    """
    seed_of = {}
    name_of = {}
    state_of = {}
    order_ids = []
    for i, r in enumerate(ranked):
        pid = r.get("player_id")
        if not pid:
            continue
        seed_of[pid] = i + 1
        name_of[pid] = r.get("name", pid)
        st = (r.get("state") or "").strip()
        if st:
            state_of[pid] = st
        order_ids.append(pid)

    size = _next_pow2(len(order_ids))
    bracket = standard_bracket_order(size)
    slot_of_seed = {seed: slot for slot, seed in enumerate(bracket)}

    # Group players by normalized (case-insensitive) state.
    by_state = {}
    for pid, st in state_of.items():
        by_state.setdefault(st.lower(), []).append(pid)

    flags = []
    for st_key, pids in by_state.items():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                slot_a = slot_of_seed.get(seed_of[a])
                slot_b = slot_of_seed.get(seed_of[b])
                if slot_a is None or slot_b is None:
                    continue
                rnd = meeting_round(slot_a, slot_b, size)
                if rnd > early_rounds:
                    continue
                flags.append({
                    "a_seed": seed_of[a], "a_id": a, "a_name": name_of.get(a, a),
                    "b_seed": seed_of[b], "b_id": b, "b_name": name_of.get(b, b),
                    "state": state_of[a],
                    "round": rnd, "bracket_size": size,
                    "severity": round(float(early_rounds - rnd + 1), 4),
                })
    flags.sort(key=lambda f: f["severity"], reverse=True)
    return flags

def detect_city_clashes(ranked, early_rounds=2):
    """Find seeded players from the SAME city who'd meet early.

    The city-tier companion to detect_state_clashes: at a state-heavy event
    (e.g. a Texas major) the state check flags everyone and becomes noise,
    while same-CITY still surfaces genuinely local clusters.

    City is free text with no canonical id, so matching is normalized
    (trimmed, case-insensitive: "dallas" == "Dallas"). Because city names
    collide across states (Springfield, Portland...), a pair is EXCLUDED
    when both players have a state and the states differ; if either lacks
    a state, the city match is allowed.

    ranked        -- list of {player_id, name, city, state, state_id, ...}
                     in seed order.
    early_rounds  -- flag pairs meeting in this round or earlier.

    Returns flags sorted worst-first:
      { a_seed, a_id, a_name, b_seed, b_id, b_name, city, round,
        bracket_size, severity }
    """
    seed_of = {}
    name_of = {}
    city_of = {}
    statekey_of = {}
    order_ids = []
    for i, r in enumerate(ranked):
        pid = r.get("player_id")
        if not pid:
            continue
        seed_of[pid] = i + 1
        name_of[pid] = r.get("name", pid)
        ct = (r.get("city") or "").strip()
        if ct:
            city_of[pid] = ct
        sid = r.get("state_id")
        st = (r.get("state") or "").strip()
        if sid not in (None, ""):
            statekey_of[pid] = "id:%s" % sid
        elif st:
            statekey_of[pid] = "txt:%s" % st.lower()
        order_ids.append(pid)

    size = _next_pow2(len(order_ids))
    bracket = standard_bracket_order(size)
    slot_of_seed = {seed: slot for slot, seed in enumerate(bracket)}

    by_city = {}
    for pid, ct in city_of.items():
        by_city.setdefault(ct.lower(), []).append(pid)

    flags = []
    for ct_key, pids in by_city.items():
        if len(pids) < 2:
            continue
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                a, b = pids[i], pids[j]
                ka, kb = statekey_of.get(a), statekey_of.get(b)
                if ka and kb and ka != kb:
                    continue   # same city NAME, different states
                slot_a = slot_of_seed.get(seed_of[a])
                slot_b = slot_of_seed.get(seed_of[b])
                if slot_a is None or slot_b is None:
                    continue
                rnd = meeting_round(slot_a, slot_b, size)
                if rnd > early_rounds:
                    continue
                flags.append({
                    "a_seed": seed_of[a], "a_id": a, "a_name": name_of.get(a, a),
                    "b_seed": seed_of[b], "b_id": b, "b_name": name_of.get(b, b),
                    "city": city_of[a],
                    "round": rnd, "bracket_size": size,
                    "severity": round(float(early_rounds - rnd + 1), 4),
                })
    flags.sort(key=lambda f: f["severity"], reverse=True)
    return flags