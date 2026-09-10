#!/usr/bin/env python3
"""Authoritative 50k+ city list for our 20 states, with county, from Census."""
import csv
import json
from collections import defaultdict

STATE_FIPS = {
    "05": "AR", "08": "CO", "09": "CT", "13": "GA", "17": "IL",
    "18": "IN", "21": "KY", "22": "LA", "26": "MI", "27": "27",
    "29": "MO", "35": "NM", "39": "OH", "40": "OK", "41": "OR",
    "44": "RI", "45": "SC", "47": "TN", "48": "TX", "51": "VA",
}
STATE_FIPS["27"] = "MN"  # fix typo

STATE_ABBR_TO_SLUG = {
    "AR": "arkansas", "CO": "colorado", "CT": "connecticut", "GA": "georgia",
    "IL": "illinois", "IN": "indiana", "KY": "kentucky", "LA": "louisiana",
    "MI": "michigan", "MN": "minnesota", "MO": "missouri", "NM": "new-mexico",
    "OH": "ohio", "OK": "oklahoma", "OR": "oregon", "RI": "rhode-island",
    "SC": "south-carolina", "TN": "tennessee", "TX": "texas", "VA": "virginia",
}

# county (state, county_fips) -> name
county_names = {}
with open("/tmp/co-est2024-alldata.csv", newline="", encoding="latin-1") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] != "050":
            continue
        state = row["STATE"]
        if state not in STATE_FIPS:
            continue
        cname = row["CTYNAME"].strip()
        cname = (cname.replace(" County", "").replace(" Parish", "")
                     .replace(" city", "").replace(" City", "")
                     .replace(" Borough", "").replace(" Census Area", ""))
        county_names[(state, row["COUNTY"])] = cname

# place -> primary county (via SUMLEV=157 "county portion of place")
place_county = defaultdict(lambda: (None, -1))
with open("/tmp/sub-est2024.csv", newline="", encoding="latin-1") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] != "157":
            continue
        state = row["STATE"]
        if state not in STATE_FIPS:
            continue
        place = row["PLACE"]
        if place == "99990":  # "Balance of county" — not a real place
            continue
        pop = int(row["POPESTIMATE2024"])
        key = (state, place)
        if pop > place_county[key][1]:
            place_county[key] = (row["COUNTY"], pop)

CITY_NAME_OVERRIDES = {
    "Augusta-Richmond County consolidated government": "Augusta",
    "Macon-Bibb County": "Macon",
    "Athens-Clarke County unified government": "Athens",
    "Louisville/Jefferson County metro government": "Louisville",
    "Lexington-Fayette urban county": "Lexington",
    "Nashville-Davidson metropolitan government": "Nashville",
}

def clean_city_name(name):
    n = name.strip()
    if "(" in n and n.rstrip().endswith(")"):
        n = n[: n.rfind("(")].rstrip()
    if n in CITY_NAME_OVERRIDES:
        return CITY_NAME_OVERRIDES[n]
    for s in [" city", " town", " village", " borough", " municipality",
              " (balance)", " balance", " township", " charter township",
              " city and borough", " metropolitan government",
              " consolidated government", " unified government"]:
        if n.lower().endswith(s.lower()):
            n = n[: -len(s)].rstrip()
            break
    return n

cities = []
with open("/tmp/sub-est2024.csv", newline="", encoding="latin-1") as f:
    for row in csv.DictReader(f):
        if row["SUMLEV"] != "162":
            continue
        state = row["STATE"]
        if state not in STATE_FIPS:
            continue
        pop = int(row["POPESTIMATE2024"])
        if pop < 50000:
            continue
        abbr = STATE_FIPS[state]
        place = row["PLACE"]
        county_fips = place_county.get((state, place), (None,))[0]
        cities.append({
            "city": clean_city_name(row["NAME"]),
            "state_abbr": abbr,
            "state_slug": STATE_ABBR_TO_SLUG[abbr],
            "county_fips": county_fips,
            "county_name": county_names.get((state, county_fips)),
            "population": pop,
        })

cities.sort(key=lambda c: (c["state_abbr"], -c["population"]))

from collections import Counter
per = Counter(c["state_abbr"] for c in cities)
print(f"TOTAL 50k+ incorporated places in 20 states: {len(cities)}")
print("per state:", dict(sorted(per.items())))
missing = [c for c in cities if not c["county_name"]]
print("cities missing county mapping:", len(missing))
for c in missing:
    print("  NO COUNTY:", c["city"], c["state_abbr"], "pop", c["population"])

with open("/tmp/cities50k.json", "w") as f:
    json.dump(cities, f, indent=2)
print("wrote /tmp/cities50k.json")
