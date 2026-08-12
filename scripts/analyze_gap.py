#!/usr/bin/env python3
"""
Compute the full gap: all counties in 20 states + all 50K+ cities,
versus what already exists on evictions.help.
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import os
import time

SEO_DIR = "/opt/eviction-defense/seo"

COVERED_STATES = {
    'AZ': 'arizona', 'AR': 'arkansas', 'CA': 'california',
    'CO': 'colorado', 'CT': 'connecticut',
    'FL': 'florida', 'GA': 'georgia',
    'IL': 'illinois',
    'LA': 'louisiana',
    'MA': 'massachusetts', 'MI': 'michigan',
    'MN': 'minnesota',
    'NV': 'nevada', 'NM': 'new-mexico',
    'OR': 'oregon',
    'RI': 'rhode-island', 'SC': 'south-carolina',
    'TN': 'tennessee', 'TX': 'texas',
    'VA': 'virginia',
}

STATE_ABBR_TO_NAME = {
    'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut',
    'FL': 'Florida', 'GA': 'Georgia',
    'IL': 'Illinois',
    'LA': 'Louisiana',
    'MA': 'Massachusetts', 'MI': 'Michigan',
    'MN': 'Minnesota',
    'NV': 'Nevada', 'NM': 'New Mexico',
    'OR': 'Oregon',
    'RI': 'Rhode Island', 'SC': 'South Carolina',
    'TN': 'Tennessee', 'TX': 'Texas',
    'VA': 'Virginia',
}


def wiki_get(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": "evictions.help/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(6 * (attempt + 1))
            elif attempt == retries - 1:
                raise
            else:
                time.sleep(2)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


def slugify(text):
    return text.lower().replace(' ', '-').replace("'", "").replace('.', '')


def get_counties_for_state(state_abbr):
    """Fetch all counties for a state from Wikipedia."""
    state_name = STATE_ABBR_TO_NAME[state_abbr]
    page_title = f"List of counties in {state_name}"

    url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(page_title)}&prop=wikitext&format=json"
    data = wiki_get(url)
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return []

    counties = []
    # County names are in [[...]] links with "County" suffix or standalone
    # Match patterns like [[Alameda County, California|Alameda County]]
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', wikitext):
        target = m.group(1)
        display = m.group(2) or m.group(1)
        # Filter to county entries
        if 'County' in display or 'Parish' in display or 'county' in display or 'parish' in display:
            name = display.split(',')[0].strip()
            # Remove "County"/"Parish" suffix
            name = re.sub(r'\s+(County|Parish)$', '', name, flags=re.IGNORECASE)
            if name and name not in counties:
                counties.append(name)
    return counties


def get_cities_50k():
    """Fetch all 50K+ cities from Wikipedia list page."""
    url = "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_United_States_cities_by_population&prop=wikitext&format=json"
    data = wiki_get(url)
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return []

    table_match = re.search(
        r'\{\| class="sortable wikitable sticky-header-multi[^"]*"(.*?)^\|\}',
        wikitext, re.DOTALL | re.MULTILINE
    )
    if not table_match:
        return []

    rows = re.split(r'\n\|-\n', table_match.group(1))
    cities = []
    for row in rows:
        city_match = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row)
        if not city_match:
            continue
        city_name = (city_match.group(2) or city_match.group(1)).strip()
        if ',' in city_name:
            city_name = city_name.split(',')[0].strip()

        state_links = re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row)
        if len(state_links) < 2:
            continue
        state_abbr = state_links[1][1].strip() if state_links[1][1] else state_links[1][0].strip()
        if len(state_abbr) > 2:
            state_abbr = {v: k for k, v in STATE_ABBR_TO_NAME.items()}.get(state_abbr, state_abbr[:2].upper())
        if state_abbr not in COVERED_STATES:
            continue

        pop_match = re.search(r'\{\{change[^}]*?\|([\d,]+)\|([\d,]+)', row)
        if not pop_match:
            continue
        try:
            estimate = int(pop_match.group(1).replace(',', ''))
        except ValueError:
            continue
        if estimate >= 50000:
            cities.append({'city': city_name, 'state_abbr': state_abbr, 'population': estimate})
    return cities


def list_existing_counties():
    """List existing county directories per state."""
    existing = {}
    for state_slug in COVERED_STATES.values():
        state_dir = os.path.join(SEO_DIR, state_slug)
        if not os.path.exists(state_dir):
            existing[state_slug] = []
            continue
        counties = []
        try:
            for d in os.listdir(state_dir):
                full = os.path.join(state_dir, d)
                if os.path.isdir(full) and os.path.exists(os.path.join(full, 'index.html')):
                    base = d.replace('-county', '').replace('-parish', '').replace('-', ' ').strip()
                    counties.append(base)
        except OSError:
            pass
        existing[state_slug] = counties
    return existing


def list_existing_cities():
    """List existing city slugs per state."""
    existing = set()
    for state_slug in COVERED_STATES.values():
        state_dir = os.path.join(SEO_DIR, state_slug)
        if not os.path.exists(state_dir):
            continue
        try:
            for county in os.listdir(state_dir):
                cpath = os.path.join(state_dir, county)
                if not os.path.isdir(cpath):
                    continue
                for city in os.listdir(cpath):
                    cp = os.path.join(cpath, city)
                    if os.path.isdir(cp) and os.path.exists(os.path.join(cp, 'index.html')):
                        existing.add(city)
        except OSError:
            continue
    return existing


def main():
    print("Fetching all counties for 20 states...", flush=True)
    all_counties = {}
    for abbr in COVERED_STATES:
        try:
            counties = get_counties_for_state(abbr)
            all_counties[abbr] = counties
            print(f"  {abbr}: {len(counties)} counties", flush=True)
            time.sleep(1.5)
        except Exception as e:
            print(f"  {abbr}: ERROR {e}", flush=True)
            all_counties[abbr] = []

    print("\nFetching all 50K+ cities...", flush=True)
    cities = get_cities_50k()
    print(f"  Found {len(cities)} cities", flush=True)

    print("\nReading existing pages...", flush=True)
    existing_counties = list_existing_counties()
    existing_cities = list_existing_cities()

    # County gap
    print("\n" + "=" * 60)
    print("COUNTY GAP")
    print("=" * 60)
    total_missing_counties = 0
    for abbr, counties in sorted(all_counties.items()):
        state_slug = COVERED_STATES[abbr]
        existing = set(existing_counties.get(state_slug, []))
        missing = [c for c in counties if c.lower() not in {e.lower() for e in existing}]
        total_missing_counties += len(missing)
        print(f"{abbr}: {len(counties)} total, {len(existing)} existing, {len(missing)} MISSING")
        if missing:
            print(f"    Missing: {', '.join(sorted(missing)[:40])}{'...' if len(missing) > 40 else ''}")

    # City gap
    print("\n" + "=" * 60)
    print("CITY GAP (50K+)")
    print("=" * 60)
    missing_cities = []
    for c in cities:
        slug = slugify(c['city'])
        if slug not in existing_cities:
            missing_cities.append(c)

    print(f"Total 50K+ cities in 20 states: {len(cities)}")
    print(f"Existing: {len(cities) - len(missing_cities)}")
    print(f"MISSING: {len(missing_cities)}")

    # Save to JSON for the generator
    output = {
        "counties": all_counties,
        "missing_counties": {},
        "cities": cities,
        "missing_cities": missing_cities,
    }
    for abbr, counties in sorted(all_counties.items()):
        state_slug = COVERED_STATES[abbr]
        existing = set(existing_counties.get(state_slug, []))
        missing = [c for c in counties if c.lower() not in {e.lower() for e in existing}]
        output["missing_counties"][state_slug] = missing

    try:
        with open("/tmp/gap_analysis.json", "w") as f:
            json.dump(output, f)
    except OSError as e:
        print(f"Failed to save: {e}")

    print(f"\nSaved analysis to /tmp/gap_analysis.json")
    print(f"\nTOTALS: {total_missing_counties} missing counties, {len(missing_cities)} missing cities")


if __name__ == '__main__':
    main()
