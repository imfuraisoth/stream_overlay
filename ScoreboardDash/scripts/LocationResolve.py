"""Location resolution for start.gg profile pulls.

Given start.gg location data (state text, stateId, city) for a tournament's
entrants, decide -- per player -- whether to auto-fill the local profile, flag
a conflict for manual review, or leave it alone. The TO reviews the result
before anything is written (see /locationReview + /applyLocations in pyserver).

Design decisions (from the feature spec):
- stateId is the canonical match key; state text is a display label.
- Flag-don't-overwrite: if the profile already has a DIFFERENT state, we flag
  the conflict and do NOT overwrite (protects manual corrections).
- Backfill: if the profile has no state and start.gg has one, propose filling.
- Non-standard text (doesn't map to a known US state) is flagged for review.
- City is recorded when present (for a future city-tier seeding check); it is
  not used for matching or flagging.
"""

# Canonical US state name -> USPS abbreviation. Used only to decide whether a
# pulled state text is "standard" (clean) or should be flagged for review.
_US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "washington dc": "DC", "washington d.c.": "DC",
}
_US_ABBREVS = set(_US_STATES.values())


def normalize_state(text):
    """Return the USPS abbreviation for a state text if recognized, else None.
    Case-insensitive, trims, accepts full names and 2-letter abbreviations."""
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    if t.upper() in _US_ABBREVS:
        return t.upper()
    return _US_STATES.get(t)


# Resolution status codes for each reviewed player.
FILL = "fill"          # profile empty, start.gg has a value -> propose filling
CONFLICT = "conflict"  # profile has a DIFFERENT value -> flag, do not overwrite
MATCH = "match"        # profile already matches start.gg -> nothing to do
NONSTD = "nonstandard"  # start.gg value doesn't map to a known state -> flag
NONE = "none"          # start.gg has no state for this player -> skip


def resolve_one(profile_state, profile_state_id, sgg_state, sgg_state_id):
    """Decide the status + proposed value for a single player.

    Returns (status, proposed_state, proposed_state_id, is_flagged).
    proposed_* is what WOULD be written if the TO approves.
    """
    sgg_state = (sgg_state or "").strip()
    profile_state = (profile_state or "").strip()

    if not sgg_state and sgg_state_id in (None, ""):
        return NONE, "", None, False

    # canonical comparison prefers stateId; fall back to normalized text
    def canon(txt, sid):
        if sid not in (None, ""):
            return ("id", str(sid))
        norm = normalize_state(txt)
        return ("txt", norm or txt.lower())

    sgg_key = canon(sgg_state, sgg_state_id)
    prof_key = canon(profile_state, profile_state_id) if (profile_state or profile_state_id not in (None, "")) else None

    is_standard = normalize_state(sgg_state) is not None or sgg_state_id not in (None, "")

    # profile empty -> propose fill (flag if the pulled text is non-standard)
    if prof_key is None:
        if not is_standard:
            return NONSTD, sgg_state, sgg_state_id, True
        return FILL, sgg_state, sgg_state_id, False

    # profile already has something
    if prof_key == sgg_key:
        return MATCH, profile_state, profile_state_id, False

    # different -> conflict, do NOT overwrite (flag for manual decision)
    return CONFLICT, sgg_state, sgg_state_id, True


def build_review(entrant_locations, resolve_fn):
    """Build a review list from pulled entrant locations.

    entrant_locations: list of dicts, each:
      { player_id (or None if unmatched), tag, state, state_id, city }
    resolve_fn(player_id) -> profile dict (or None) with keys state, state_id.

    Returns a list of review rows (only those needing attention OR a fill):
      { player_id, tag, status, is_flagged,
        current_state, current_state_id,
        sgg_state, sgg_state_id, sgg_city,
        proposed_state, proposed_state_id, proposed_city }
    MATCH and NONE rows are omitted (nothing for the TO to act on), except we
    still carry city-only updates as fills when the state matched.
    """
    review = []
    for ent in entrant_locations:
        pid = ent.get("player_id")
        sgg_state = ent.get("state") or ""
        sgg_state_id = ent.get("state_id")
        sgg_city = ent.get("city") or ""
        prof = resolve_fn(pid) if pid else None
        prof_state = (prof or {}).get("state", "") if prof else ""
        prof_state_id = (prof or {}).get("state_id") if prof else None
        prof_city = (prof or {}).get("city", "") if prof else ""

        status, prop_state, prop_state_id, flagged = resolve_one(
            prof_state, prof_state_id, sgg_state, sgg_state_id)

        # city fill: propose whenever start.gg has a city the profile lacks
        city_fill = bool(sgg_city and not prof_city)

        # Skip rows with genuinely nothing to do: no state action AND no city fill.
        if status in (MATCH, NONE) and not city_fill:
            continue

        review.append({
            "player_id": pid,
            "tag": ent.get("tag", ""),
            "status": status,
            "is_flagged": flagged,
            "current_state": prof_state,
            "current_state_id": prof_state_id,
            "current_city": prof_city,
            "sgg_state": sgg_state,
            "sgg_state_id": sgg_state_id,
            "sgg_city": sgg_city,
            "proposed_state": prop_state,
            "proposed_state_id": prop_state_id,
            "proposed_city": sgg_city if city_fill else prof_city,
            "city_fill": city_fill,
        })
    return review