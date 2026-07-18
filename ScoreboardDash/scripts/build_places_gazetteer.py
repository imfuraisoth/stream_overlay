#!/usr/bin/env python3
"""Build resources/us_places_gazetteer.json -- a compact "STATE|city name"
-> (lat, lon) lookup table for every incorporated US place, used to resolve
a player's free-text city into coordinates for metro-area matching.

THIS IS THE ONLY STATIC DATASET THE METRO FEATURE BUNDLES. Everything else
(which metro area a place belongs to) is resolved LIVE against the Census
Bureau's Geocoder at the "Current_Current" vintage/benchmark, so metro
BOUNDARIES never go stale -- they update themselves automatically whenever
OMB revises them. Only city *coordinates* are bundled, and those almost
never change (new incorporated places are rare, existing ones don't move).

── HOW TO REFRESH ──
Census publishes a new Gazetteer Places file most years. To update:
  1. Find the current year's file at:
       https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html
     (or https://www.census.gov/geographies/reference-files/<YEAR>/geo/gazetter-file.html)
     -> "National Places Gazetteer Files"
  2. Set GAZETTEER_URL below to that year's URL (just the year changes in
     the path/filename, e.g. .../2025_Gazetteer/2025_Gaz_place_national.zip).
  3. Run: python build_places_gazetteer.py
  4. Commit the updated resources/us_places_gazetteer.json.

That's it -- no code changes needed elsewhere. This is a static file lookup
of city NAMES to coordinates, not the metro boundaries themselves.
"""
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

GAZETTEER_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_place_national.zip"

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "resources", "us_places_gazetteer.json")

# Census appends one of these designation suffixes to every place name
# (e.g. "Plano city", "Abanda CDP"). Strip them so lookups match how a
# player naturally types their city ("Plano", not "Plano city").
SUFFIXES = [" city", " town", " village", " CDP", " borough", " municipality",
            " township", " corporation", " zona urbana", " comunidad",
            " urban cluster"]


def strip_suffix(name):
    for suf in SUFFIXES:
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def main():
    print("Downloading %s ..." % GAZETTEER_URL)
    with urllib.request.urlopen(GAZETTEER_URL, timeout=60) as resp:
        raw = resp.read()
    print("Downloaded %d bytes, extracting..." % len(raw))

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        txt_names = [n for n in zf.namelist() if n.endswith(".txt")]
        if not txt_names:
            print("ERROR: no .txt file found in the zip", file=sys.stderr)
            sys.exit(1)
        with zf.open(txt_names[0]) as f:
            lines = f.read().decode("utf-8").splitlines()

    lookup = {}
    dupes = 0
    for line in lines[1:]:   # skip header
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        usps, geoid, ansi, name, lsad, funcstat, aland, awater, alandsq, awatersq, lat, lon = parts[:12]
        norm = strip_suffix(name.strip())
        key = usps.strip().upper() + "|" + norm.strip().lower()
        if key in lookup:
            dupes += 1   # same normalized name twice in one state -- keep first, rare
            continue
        try:
            lookup[key] = [round(float(lat), 6), round(float(lon), 6)]
        except ValueError:
            continue

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, separators=(",", ":"))

    print("Wrote %d places (%d duplicate names skipped) to %s"
          % (len(lookup), dupes, OUT_PATH))


if __name__ == "__main__":
    main()