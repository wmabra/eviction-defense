#!/usr/bin/env python3
"""
Find all cities with 50K+ population in our 20 covered states that are
missing from evictions.help. Parses Wikipedia wikitext table.
"""
import urllib.request
import json
import re
import os

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


def fetch_wikitext():
    """Fetch the Wikipedia page wikitext."""
    url = "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_United_States_cities_by_population&prop=wikitext&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "evictions.help/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["parse"]["wikitext"]["*"]


def parse_cities(wikitext):
    """Parse the main data table. Returns list of {city, state_abbr, population}."""
    # Find the main data table - it has "sticky-header-multi" class
    table_match = re.search(
        r'\{\| class="sortable wikitable sticky-header-multi[^"]*"(.*?)^\|\}',
        wikitext, re.DOTALL | re.MULTILINE
    )
    if not table_match:
        return []
    
    table = table_match.group(1)
    
    # Split into rows
    rows = re.split(r'\n\|-\n', table)
    
    cities = []
    for row in rows:
        # Extract city name: [[City Name, State|City]] or [[City Name]]
        city_match = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row)
        if not city_match:
            continue
        
        # Use display text if available (after pipe), otherwise link target
        city_name = (city_match.group(2) or city_match.group(1)).strip()
        # Remove state suffix like "Phoenix, Arizona" if present in display
        if ',' in city_name:
            city_name = city_name.split(',')[0].strip()
        
        # Skip header rows and non-city rows
        if city_name in ('Municipality', 'City', '!') or city_name.startswith('!'):
            continue
        
        # Clean city name - remove things in parentheses like "(balance)"
        city_name = re.sub(r'\s*\([^)]*\)', '', city_name).strip()
        
        # Extract state abbreviation
        # Pattern: [[State Name|ST]] or [[State Name]]
        state_match = re.search(r'\[\[([^\]|]+)\|?([A-Z]{2})?\]\]', row)
        if not state_match:
            continue
        
        # The state should be the second link in the row
        state_links = re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', row)
        if len(state_links) < 2:
            continue
        
        state_abbr = state_links[1][1].strip() if state_links[1][1] else state_links[1][0].strip()
        if len(state_abbr) > 2:
            # It's the full state name, need abbreviation
            state_abbr_map = {
                'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
                'Colorado': 'CO', 'Connecticut': 'CT',
                'Florida': 'FL', 'Georgia': 'GA',
                'Illinois': 'IL',
                'Louisiana': 'LA',
                'Massachusetts': 'MA', 'Michigan': 'MI',
                'Minnesota': 'MN',
                'Nevada': 'NV', 'New Mexico': 'NM',
                'Oregon': 'OR',
                'Rhode Island': 'RI', 'South Carolina': 'SC',
                'Tennessee': 'TN', 'Texas': 'TX',
                'Virginia': 'VA',
            }
            state_abbr = state_abbr_map.get(state_abbr, state_abbr[:2].upper())
        
        if state_abbr not in COVERED_STATES:
            continue
        
        # Extract population - first number in {{change|...|ESTIMATE|CENSUS}}
        pop_match = re.search(r'\{\{change[^}]*?\|([\d,]+)\|([\d,]+)', row)
        if not pop_match:
            continue
        
        estimate = int(pop_match.group(1).replace(',', ''))
        
        if estimate >= 50000:
            cities.append({
                'city': city_name,
                'state_abbr': state_abbr,
                'state_slug': COVERED_STATES[state_abbr],
                'population': estimate,
                'slug': normalize_city_name(city_name),
            })
    
    return cities


def get_existing_cities():
    """Get set of existing city paths."""
    existing = set()
    try:
        for state in os.listdir(SEO_DIR):
            spath = os.path.join(SEO_DIR, state)
            if not os.path.isdir(spath) or state.startswith('.'):
                continue
            if state in ('assets', 'checkout', 'disclaimer', 'privacy', 'terms'):
                continue
            for county in os.listdir(spath):
                cpath = os.path.join(spath, county)
                if not os.path.isdir(cpath):
                    continue
                for city in os.listdir(cpath):
                    city_path = os.path.join(cpath, city)
                    if os.path.isdir(city_path) and os.path.exists(os.path.join(city_path, 'index.html')):
                        existing.add(f"{state}/{county}/{city}")
    except OSError:
        pass
    return existing


def normalize_city_name(name):
    """Normalize city name to match URL slug format."""
    return name.lower().replace(' ', '-').replace("'", "").replace('.', '').replace('–', '-')


def find_county(city_name, state_slug):
    """Find which county directory a city belongs to."""
    state_dir = os.path.join(SEO_DIR, state_slug)
    if not os.path.exists(state_dir):
        return None, None
    
    norm_city = normalize_city_name(city_name)
    
    # Exact match: city dir exists under a county
    for county in os.listdir(state_dir):
        cpath = os.path.join(state_dir, county)
        if not os.path.isdir(cpath):
            continue
        if os.path.exists(os.path.join(cpath, norm_city)):
            return county, county.replace('-county', '').replace('-', ' ').title()
    
    # Text search: city mentioned in county page
    for county in os.listdir(state_dir):
        cpath = os.path.join(state_dir, county)
        idx = os.path.join(cpath, 'index.html')
        if not os.path.exists(idx):
            continue
        try:
            with open(idx, 'r') as f:
                content = f.read().lower()
            if city_name.lower() in content:
                return county, county.replace('-county', '').replace('-', ' ').title()
        except Exception:
            continue
    
    return None, None


def main():
    print("Fetching Wikipedia data...")
    wikitext = fetch_wikitext()
    
    print("Parsing cities...")
    cities = parse_cities(wikitext)
    print(f"Found {len(cities)} cities with 50K+ in our 20 states\n")
    
    existing = get_existing_cities()
    print(f"Existing city pages on site: {len(existing)}\n")
    
    # Cross-reference
    missing = []
    matched = 0
    
    for c in cities:
        norm_city = normalize_city_name(c['city'])
        found = any(ep.endswith('/' + norm_city) for ep in existing)
        
        if found:
            matched += 1
        else:
            county_slug, county_title = find_county(c['city'], c['state_slug'])
            missing.append({**c, 'county_slug': county_slug, 'county_title': county_title})
    
    print("=" * 70)
    print(f"Already have pages: {matched}")
    print(f"MISSING:            {len(missing)}")
    print("=" * 70)
    
    if not missing:
        print("\nAll cities with 50K+ population already have pages!")
        return
    
    # Group by state
    by_state = {}
    for m in missing:
        by_state.setdefault(m['state_slug'], []).append(m)
    
    print("\n=== MISSING CITY PAGES (50K+ population) ===\n")
    
    for state in sorted(by_state.keys()):
        cities_list = by_state[state]
        print(f"\n{state.upper()} ({len(cities_list)} missing):")
        for c in sorted(cities_list, key=lambda x: -x['population']):
            county_info = f" ({c['county_title']} County)" if c['county_title'] else " (county NOT FOUND)"
            print(f"  {c['city']} — pop {c['population']:,}{county_info}")


if __name__ == '__main__':
    main()
