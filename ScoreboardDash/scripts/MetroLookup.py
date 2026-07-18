"""Resolve a US city+state to its Metropolitan/Micropolitan Statistical Area
name, for metro-aware same-city seeding checks (so Plano/Garland/Richardson/
Rowlett all cluster with Dallas instead of only matching their own exact
city name).

Design, and why it needs no ongoing maintenance:
  - The only BUNDLED data is resources/us_places_gazetteer.json -- a plain
    "STATE|city name" -> (lat, lon) lookup, built by build_places_gazetteer.py.
    City coordinates essentially never change, so this rarely needs a refresh,
    and refreshing it is a documented one-command script, not a code change.
  - The actual metro ASSIGNMENT (which MSA a place belongs to) is resolved
    LIVE against the Census Bureau's public Geocoder, at the "Current_Current"
    vintage/benchmark -- so it automatically reflects whatever the current
    OMB delineation is. Nothing to track or refresh; it updates itself.
  - Every live lookup is cached to disk permanently (data/metro_cache.json),
    keyed by state+city, so it's a one-time network cost per distinct city
    ever seen, not a per-request or per-player cost.
  - If the network or the Census API is ever unavailable (it's a federal
    site; funding lapses have taken portions of census.gov offline before),
    every function here degrades to returning None rather than raising --
    callers fall back to today's exact-city-text matching, never break.
"""
import json
import os
import re
import urllib.error
import urllib.request

from scripts import LocationResolve

_HERE = os.path.dirname(os.path.abspath(__file__))
GAZETTEER_PATH = os.path.join(_HERE, "..", "resources", "us_places_gazetteer.json")
CACHE_PATH = os.path.join(_HERE, "..", "data", "metro_cache.json")

GEOCODER_URL = ("https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
                "?x={lon}&y={lat}&benchmark=Public_AR_Current&vintage=Current_Current"
                "&format=json&layers=Metropolitan%20Statistical%20Areas")

_gazetteer = None   # lazy-loaded, kept in memory for the process lifetime
_cache = None       # lazy-loaded dict, flushed to disk on every new entry


def _load_gazetteer():
    global _gazetteer
    if _gazetteer is not None:
        return _gazetteer
    try:
        with open(GAZETTEER_PATH, "r", encoding="utf-8") as f:
            _gazetteer = json.load(f)
    except Exception as e:
        print("MetroLookup: gazetteer not available (%s) -- metro matching disabled" % e)
        _gazetteer = {}
    return _gazetteer


def _load_cache():
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}
    return _cache


def _save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("MetroLookup: could not persist cache (%s)" % e)


def _normalize_city(city):
    return re.sub(r"\s+", " ", (city or "").strip().lower())


def _coords_for(state, city):
    gaz = _load_gazetteer()
    # The gazetteer keys on the 2-letter USPS code (that's what the Census
    # file uses), but the player's state field is free text -- a TO might
    # type "Texas" instead of "TX". Normalize through the same state-name
    # mapping the location-review flow already uses, so either form works.
    usps = LocationResolve.normalize_state(state) or (state or "").strip().upper()
    key = usps + "|" + _normalize_city(city)
    return gaz.get(key)


def resolve_metro(state, city, timeout=5):
    """Return the metro area name for a US state+city (e.g. "Plano","TX" ->
    "Dallas-Fort Worth-Arlington, TX"), or None if unavailable -- either
    because the city isn't in the bundled gazetteer (not a recognized US
    place, a typo, an international city, or a joke entry), or the live
    geocoder couldn't be reached. Never raises."""
    if not state or not city:
        return None
    cache = _load_cache()
    usps = LocationResolve.normalize_state(state) or state.strip().upper()
    cache_key = usps + "|" + _normalize_city(city)
    if cache_key in cache:
        return cache[cache_key] or None   # cached "no match" is stored as null

    coords = _coords_for(state, city)
    if not coords:
        return None   # not in the gazetteer at all -- don't cache (may exist under a variant spelling)

    lat, lon = coords
    url = GEOCODER_URL.format(lat=lat, lon=lon)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
        msas = (data.get("result", {}).get("geographies", {})
                    .get("Metropolitan Statistical Areas", []))
        metro = msas[0]["BASENAME"] if msas else None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as e:
        print("MetroLookup: geocoder lookup failed for %s, %s (%s)" % (city, state, e))
        return None   # transient failure -- don't cache, try again next time

    cache[cache_key] = metro   # cache the resolved name, or None if the point isn't in any MSA (micropolitan/rural)
    _save_cache()
    return metro


def resolve_metro_map(state_city_pairs):
    """Batch helper: given [(pid, state, city), ...], return {pid: metro_or_None}.
    Just calls resolve_metro per pair (each already cache-checked individually),
    convenient for the seeding compute endpoint to build player_metro in one call."""
    out = {}
    for pid, state, city in state_city_pairs:
        out[pid] = resolve_metro(state, city)
    return out