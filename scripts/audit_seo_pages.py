#!/usr/bin/env python3
"""Audit seo/ for duplicates and missing 50k+ city pages."""
import os
import json
import re

SEO = "/opt/eviction-defense/seo"
EXCLUDED = {'assets', 'checkout', 'disclaimer', 'privacy', 'terms', 'robots.txt'}

STATE_SLUG_TO_ABBR = {
    "arkansas": "AR", "colorado": "CO", "connecticut": "CT", "georgia": "GA",
    "illinois": "IL", "indiana": "IN", "kentucky": "KY", "louisiana": "LA",
    "michigan": "MI", "minnesota": "MN", "missouri": "MO", "new-mexico": "NM",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "rhode-island": "RI",
    "south-carolina": "SC", "tennessee": "TN", "texas": "TX", "virginia": "VA",
}

def slugify(text):
    return (text.lower().replace(' ', '-').replace("'", "")
            .replace('.', '').replace('–', '-').replace('—', '-'))

# ---- Build index: state -> county -> [city slugs] ----
index = {}
for state in sorted(os.listdir(SEO)):
    spath = os.path.join(SEO, state)
    if not os.path.isdir(spath) or state in EXCLUDED or state.startswith('.'):
        continue
    index[state] = {}
    for county in sorted(os.listdir(spath)):
        cpath = os.path.join(spath, county)
        if not os.path.isdir(cpath):
            continue
        cities = []
        for city in os.listdir(cpath):
            cipath = os.path.join(cpath, city)
            if os.path.isdir(cipath) and os.path.isfile(os.path.join(cipath, 'index.html')):
                cities.append(city)
        index[state][county] = cities

# ---- State dirs ----
state_dirs = set(index.keys())
print("=== STATE DIRECTORIES ===")
print(f"  found {len(state_dirs)}: {sorted(state_dirs)}")
missing_states = [s for s in STATE_SLUG_TO_ABBR if s not in state_dirs]
extra_states = [s for s in state_dirs if s not in STATE_SLUG_TO_ABBR]
print(f"  missing state dirs: {missing_states}")
print(f"  extra/non-20-state dirs: {extra_states}")

# ---- County + city counts ----
total_counties = sum(len(c) for c in index.values())
total_cities = sum(len(v) for c in index.values() for v in c.values())
print(f"\n  total county dirs: {total_counties}")
print(f"  total city dirs:   {total_cities}")

# ---- Duplicate city slugs (same slug in multiple counties within a state) ----
print("\n=== DUPLICATE CITY SLUGS (same slug in >1 county within a state) ===")
dupe_city = 0
for state, counties in index.items():
    city_to_counties = {}
    for county, cities in counties.items():
        for city in cities:
            city_to_counties.setdefault(city, []).append(county)
    for city, cs in sorted(city_to_counties.items()):
        if len(cs) > 1:
            dupe_city += 1
            print(f"  {state}/{city} -> {cs}")
print(f"  TOTAL duplicate city slugs: {dupe_city}")

# ---- Missing 50k+ cities ----
cities = json.load(open("/tmp/cities50k.json"))
print("\n=== MISSING 50k+ CITY PAGES ===")
# existing city slugs per state
existing_by_state = {}
for state, counties in index.items():
    s = set()
    for cities_list in counties.values():
        s.update(cities_list)
    existing_by_state[state] = s

missing = []
for c in cities:
    slug = slugify(c["city"])
    if slug not in existing_by_state.get(c["state_slug"], set()):
        missing.append(c)

print(f"  authoritative 50k+ cities: {len(cities)}")
print(f"  missing (no page anywhere in state): {len(missing)}")
from collections import Counter
print("  missing per state:", dict(sorted(Counter(c['state_abbr'] for c in missing).items())))
print("\n  full missing list:")
for c in missing:
    print(f"    {c['state_abbr']:2} {c['city']:28s} {c['county_name']:24s} {c['population']:,}")

json.dump(missing, open("/tmp/missing_cities.json", "w"), indent=2)
print(f"\nwrote /tmp/missing_cities.json ({len(missing)} entries)")
