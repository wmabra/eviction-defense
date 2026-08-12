#!/usr/bin/env python3
"""
Generate ALL missing county + city pages for evictions.help.

Goal: every city with 50K+ population in our 20 covered states gets a page.
Missing county pages are created first, then city pages under them.

Resumable via a JSON progress file.

Usage:
    python3 generate_all_missing_pages.py --dry-run
    python3 generate_all_missing_pages.py            # full run (background)
    python3 generate_all_missing_pages.py --resume   # continue from progress
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import re
import os
import sys
import time
import shutil
from argparse import ArgumentParser

SEO_DIR = "/opt/eviction-defense/seo"
BACKUP_DIR = "/opt/eviction-defense/seo_backup_cities"
PROGRESS_FILE = "/tmp/generate_missing_pages_progress.json"

# Load env from .env file
def load_env():
    env_paths = ["/opt/eviction-defense/.env", "/opt/eviction-defense/app/.env"]
    for p in env_paths:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except OSError:
                pass

load_env()

LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

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

STATE_RESOURCES = {
    'CA': [
        ('State Housing', 'https://www.hcd.ca.gov/', 'California Department of Housing and Community Development', 'Housing programs, homelessness resources, renter assistance, and program notices'),
        ('State Referral', 'https://www.211ca.org/', '211 California', 'Rent, utilities, shelter, food, and crisis referrals'),
        ('Legal Aid', 'https://lawhelpca.org/', 'LawHelpCA', 'Eviction legal information and legal-aid routing'),
        ('Court Self-Help', 'https://selfhelp.courts.ca.gov/eviction', 'California Courts Self-Help — Eviction', 'Landlord-tenant procedures, forms, and court information'),
        ('HUD Renting', 'https://www.hud.gov/states/california/renting', 'HUD California Rental Help', 'Housing authorities, vouchers, and renter resources'),
        ('HUD Counseling', 'https://www.hud.gov/counseling', 'HUD Housing Counseling', 'HUD-approved housing counselors'),
    ],
    'TX': [
        ('State Housing', 'https://www.tdhca.texas.gov/', 'Texas Department of Housing and Community Affairs', 'Housing programs, homelessness resources, renter assistance, and program notices'),
        ('State Referral', 'https://www.211texas.org/', '2-1-1 Texas', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://texaslawhelp.org/', 'TexasLawHelp', 'Eviction legal information and legal-aid routing'),
        ('Court / Tenant Help', 'https://texaslawhelp.org/house-apartment/eviction-other-landlord-issues', 'TexasLawHelp Eviction and Landlord Issues', 'Eviction procedures, forms, and tenant guidance'),
    ],
    'FL': [
        ('State Housing', 'https://www.floridahousing.org/', 'Florida Housing Finance Corporation', 'Housing programs, homelessness resources, renter assistance'),
        ('State Referral', 'https://www.211.org/', '2-1-1 Florida', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://www.floridabar.org/public/consumer/pamphlet014/', 'Florida Bar — Eviction Information', 'Eviction legal information from The Florida Bar'),
        ('Court / Tenant Help', 'https://www.flcourts.gov/Resources-Services/Office-of-the-State-Courts-Administrator/Self-Help-Information', 'Florida Courts Self-Help', 'Eviction procedures, forms, and tenant guidance'),
    ],
}

_DEFAULT_RESOURCES = [
    ('State Housing', 'https://www.hud.gov/states', 'HUD State Resources', 'Find your state housing finance agency for rental assistance programs'),
    ('State Referral', 'https://www.211.org/', '2-1-1', 'Call 2-1-1 for rent, utilities, shelter, food and crisis referrals'),
    ('Legal Aid', 'https://www.lsc.gov/', 'Legal Services Corporation', 'Find a legal aid office near you for eviction help'),
    ('Court Self-Help', 'https://www.uscourts.gov/', 'U.S. Courts', 'Check your state court website for eviction self-help resources'),
]


def slugify(text):
    return text.lower().replace(' ', '-').replace("'", "").replace('.', '').replace('–', '-')


def wiki_get(url, retries=4):
    req = urllib.request.Request(url, headers={"User-Agent": "evictions.help/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
            elif attempt == retries - 1:
                raise
            else:
                time.sleep(2)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)
    return {}


def llm_generate(system_prompt, user_prompt):
    if not LLM_API_KEY:
        return None
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 500,
    }
    req = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read())
                text = body["choices"][0]["message"]["content"]
                text = text.replace("\u2014", " -- ").replace("\u2013", "-")
                text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
                text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
                text = re.sub(r"\*(.+?)\*", r"\1", text)
                return text.strip()
        except Exception as e:
            if attempt == 2:
                return None
            time.sleep(2 ** attempt)
    return None


# ── Wikipedia data ─────────────────────────────────────────

def fetch_cities_50k():
    """Fetch all 50K+ cities in our states from Wikipedia."""
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
        estimate = 0
        try:
            estimate = int(pop_match.group(1).replace(',', ''))
        except (ValueError, AttributeError):
            continue
        if estimate >= 50000:
            cities.append({
                'city': city_name,
                'state_abbr': state_abbr,
                'state_slug': COVERED_STATES[state_abbr],
                'population': estimate,
            })
    return cities


def get_county_and_pop(city_name, state_abbr):
    """Get county + population for a city from Wikipedia."""
    state_name = STATE_ABBR_TO_NAME.get(state_abbr, state_abbr)
    page_title = f"{city_name}, {state_name}"

    params = urllib.parse.urlencode({
        "action": "parse", "page": page_title, "prop": "wikitext", "format": "json", "section": 0,
    })
    data = wiki_get(f"https://en.wikipedia.org/w/api.php?{params}")
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    if not wikitext:
        # Try redirect
        params2 = urllib.parse.urlencode({
            "action": "query", "titles": page_title, "redirects": True, "format": "json",
        })
        d2 = wiki_get(f"https://en.wikipedia.org/w/api.php?{params2}")
        pages = d2.get("query", {}).get("pages", {})
        for p in pages.values():
            title = p.get("title", "")
            if title and title != page_title:
                params = urllib.parse.urlencode({
                    "action": "parse", "page": title, "prop": "wikitext", "format": "json", "section": 0,
                })
                data = wiki_get(f"https://en.wikipedia.org/w/api.php?{params}")
                wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
                break

    county = None
    for pattern in [
        r'\|\s*county\s*=\s*\[\[([^\]|]+)',
        r'\|\s*county\s*=\s*([^\n|]+)',
        r'\|\s*subdivision_name2\s*=\s*\[\[([^\]|]+)',
        r'\|\s*subdivision_name2\s*=\s*([^\n|]+)',
    ]:
        m = re.search(pattern, wikitext)
        if m:
            county = m.group(1).strip().rstrip(',').strip()
            break

    pop = None
    for pattern in [
        r'\|\s*population_total\s*=\s*([\d,]+)',
        r'\| population_total = ([\d,]+)',
    ]:
        m = re.search(pattern, wikitext)
        if m:
            try:
                pop = int(m.group(1).replace(',', ''))
                break
            except ValueError:
                continue

    return county, pop


def get_county_population(county_name, state_abbr):
    """Get county population from Wikipedia."""
    state_name = STATE_ABBR_TO_NAME.get(state_abbr, state_abbr)
    page_title = f"{county_name} County, {state_name}"
    params = urllib.parse.urlencode({
        "action": "query", "titles": page_title, "prop": "extracts",
        "exintro": True, "explaintext": True, "format": "json",
    })
    data = wiki_get(f"https://en.wikipedia.org/w/api.php?{params}")
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        extract = p.get("extract", "")
        m = re.search(r'population[^0-9]*([\d,]+)', extract)
        if m:
            try:
                return int(m.group(1).replace(',', ''))
            except ValueError:
                pass
        # Try "population of X"
        m = re.search(r'of\s+([\d,]+)\s+(?:people|residents)', extract)
        if m:
            try:
                return int(m.group(1).replace(',', ''))
            except ValueError:
                pass
    return None


# ── HTML builders ──────────────────────────────────────────

def build_form_html(state_abbr, county_name, city_name, page_id):
    """Build the shared eligibility form HTML."""
    state_select = ""
    for abbr, name in sorted(STATE_ABBR_TO_NAME.items(), key=lambda x: x[1]):
        if abbr in COVERED_STATES:
            sel = ' selected' if abbr == state_abbr else ''
            state_select += f'<option value="{abbr}"{sel}>{name}</option>\n'
    state_select = f'<select name="state" required aria-label="State"><option value="">Select a state</option>{state_select}</select>'

    return f'''<div class="screen-step active"><div class="question-count">Question 1 of 8</div><div class="question">Where is the rental property located?</div>{state_select}</div><div class="screen-step"><div class="question-count">Question 2 of 8</div><div class="question">What county is the eviction case in?</div><select name="county" required aria-label="County"><option value="">Select a county</option></select></div>

<div class="screen-step"><div class="question-count">Question 3 of 8</div><div class="question">Are you the tenant named in the eviction matter?</div><div class="choice-grid"><div class="choice"><input id="tenant-yes-{page_id}" type="radio" name="tenant" value="yes"><label for="tenant-yes-{page_id}">Yes</label></div><div class="choice"><input id="tenant-no-{page_id}" type="radio" name="tenant" value="no"><label for="tenant-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 4 of 8</div><div class="question">Have you been served with eviction court papers?</div><div class="choice-grid"><div class="choice"><input id="served-yes-{page_id}" type="radio" name="served" value="yes"><label for="served-yes-{page_id}">Yes</label></div><div class="choice"><input id="served-no-{page_id}" type="radio" name="served" value="no"><label for="served-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 5 of 8</div><div class="question">Is this a residential rental property?</div><div class="choice-grid"><div class="choice"><input id="residential-yes-{page_id}" type="radio" name="residential" value="yes"><label for="residential-yes-{page_id}">Yes</label></div><div class="choice"><input id="residential-no-{page_id}" type="radio" name="residential" value="no"><label for="residential-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 6 of 8</div><div class="question">Is the home Section 8, voucher-assisted, or public housing?</div><div class="choice-grid"><div class="choice"><input id="subsidized-yes-{page_id}" type="radio" name="subsidized" value="yes"><label for="subsidized-yes-{page_id}">Yes</label></div><div class="choice"><input id="subsidized-no-{page_id}" type="radio" name="subsidized" value="no"><label for="subsidized-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 7 of 8</div><div class="question">Are you or another tenant on active military duty?</div><div class="choice-grid"><div class="choice"><input id="military-yes-{page_id}" type="radio" name="military" value="yes"><label for="military-yes-{page_id}">Yes</label></div><div class="choice"><input id="military-no-{page_id}" type="radio" name="military" value="no"><label for="military-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 8 of 8</div><div class="question">Have you filed bankruptcy or is a bankruptcy case active?</div><div class="choice-grid"><div class="choice"><input id="bankruptcy-yes-{page_id}" type="radio" name="bankruptcy" value="yes"><label for="bankruptcy-yes-{page_id}">Yes</label></div><div class="choice"><input id="bankruptcy-no-{page_id}" type="radio" name="bankruptcy" value="no"><label for="bankruptcy-no-{page_id}">No</label></div></div></div>
<div class="screen-step"><div data-result class="result-box result-ok"></div><div data-qualified><div class="form-grid"><div class="field full"><label>Street address</label><input name="street" type="text" autocomplete="street-address" required></div><div class="field"><label>City</label><input name="city" type="text" autocomplete="address-level2" required></div><div class="field"><label>County</label><input name="county" type="text" autocomplete="address-level1" required></div><div class="field"><label>ZIP code</label><input name="zip" type="text" inputmode="numeric" autocomplete="postal-code" pattern="[0-9]{{5}}" required></div><div class="field"><label>Email</label><input name="email" type="email" autocomplete="email" required></div><div class="field full"><label>Phone</label><input name="phone" type="tel" autocomplete="tel" required></div></div><button class="btn btn-primary" style="max-width:100%;margin-top:16px" type="submit">Continue to secure checkout — $399</button><p class="micro">By continuing, you acknowledge that this is a self-help document preparation service—not a law firm or legal representation.</p></div></div>
<div class="screen-actions"><button data-back class="btn btn-secondary" type="button" hidden>Back</button></div>'''


def build_resource_html(state_abbr):
    resources = STATE_RESOURCES.get(state_abbr, _DEFAULT_RESOURCES)
    out = ""
    for res_type, url, title, desc in resources:
        if url and title:
            out += f'<article class="resource"><span class="type">{res_type}</span><h3><a href="{url}" rel="nofollow noopener" target="_blank">{title} ↗</a></h3><p>{desc}</p></article>\n'
        else:
            out += f'<article class="resource"><span class="type">{res_type}</span><h3>{title}</h3><p>{desc}</p></article>\n'
    return out


def build_header_and_hero(state_abbr, state_name, state_slug, county_name, county_slug, city_name, city_slug, is_city):
    """Build head + header + hero section (up to form)."""
    state_select = ""
    for abbr, name in sorted(STATE_ABBR_TO_NAME.items(), key=lambda x: x[1]):
        if abbr in COVERED_STATES:
            sel = ' selected' if abbr == state_abbr else ''
            state_select += f'<option value="{abbr}"{sel}>{name}</option>\n'

    if is_city:
        page_path = f"/{state_slug}/{county_slug}/{city_slug}/"
        title = f"Eviction Help in {city_name}, {state_name} | evictions.help"
        description = f"Check eligibility for eviction self-help document preparation in {city_name}, {county_name} County. Guided intake, $399 packet, filing preparation, and resource starting points."
        eyebrow = f"{city_name} eviction document help"
        h1 = f"Prepare eviction paperwork from {city_name} with a guided intake"
        lede = "Your city, county, and state are prefilled. Qualified tenants can continue to a $399 self-help document packet built from their own case information."
        body_attrs = f'data-state="{state_abbr}" data-county="{county_name} County" data-city="{city_name}"'
        breadcrumb = f'<li><a href="/">Home</a></li><li><a href="/{state_slug}/">{state_name}</a></li><li><a href="/{state_slug}/{county_slug}/">{county_name} County</a></li><li>{city_name}</li>'
        canonical = f"https://evictions.help{page_path}"
    else:
        page_path = f"/{state_slug}/{county_slug}/"
        title = f"Eviction Help in {county_name} County, {state_name} | evictions.help"
        description = f"Check eligibility for eviction self-help document preparation in {county_name} County, {state_name}. See packet details, statewide resources, nearby locations, and a prefilled screening form."
        eyebrow = f"{county_name} County eviction document help"
        h1 = f"Eviction paperwork help for tenants in {county_name} County"
        lede = f"Start with eight questions. Your {state_name} and {county_name} County location is carried into the guided intake and $399 document packet workflow."
        body_attrs = f'data-state="{state_abbr}" data-county="{county_name} County" data-city=""'
        breadcrumb = f'<li><a href="/">Home</a></li><li><a href="/{state_slug}/">{state_name}</a></li><li>{county_name} County</li>'
        canonical = f"https://evictions.help{page_path}"

    page_id = f"mnt-data-evictions-help-seo-website-public-{state_slug}-{county_slug}-{city_slug if is_city else 'index'}-index-html"

    state_select_form = f'<select name="state" required aria-label="State"><option value="">Select a state</option>{state_select}</select>'

    return f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{description}"><meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="{canonical}"><link rel="icon" href="/assets/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website"><meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png"><meta property="og:site_name" content="evictions.help"><meta property="og:title" content="{title}"><meta property="og:description" content="{description}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">&#123;&#34;@context&#34;: &#34;https://schema.org&#34;, &#34;@graph&#34;: [&#123;&#34;@type&#34;: &#34;Organization&#34;, &#34;@id&#34;: &#34;https://evictions.help/#organization&#34;, &#34;name&#34;: &#34;evictions.help&#34;, &#34;url&#34;: &#34;https://evictions.help/&#34;&#125;, &#123;&#34;@type&#34;: &#34;Service&#34;, &#34;@id&#34;: &#34;https://evictions.help/#service&#34;, &#34;name&#34;: &#34;Eviction self-help document preparation&#34;, &#34;provider&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#organization&#34;&#125;, &#34;areaServed&#34;: [&#34;Arkansas&#34;, &#34;Arizona&#34;, &#34;California&#34;, &#34;Colorado&#34;, &#34;Connecticut&#34;, &#34;Florida&#34;, &#34;Georgia&#34;, &#34;Illinois&#34;, &#34;Louisiana&#34;, &#34;Massachusetts&#34;, &#34;Michigan&#34;, &#34;Minnesota&#34;, &#34;New Mexico&#34;, &#34;Nevada&#34;, &#34;Oregon&#34;, &#34;Rhode Island&#34;, &#34;South Carolina&#34;, &#34;Tennessee&#34;, &#34;Texas&#34;, &#34;Virginia&#34;], &#34;offers&#34;: &#123;&#34;@type&#34;: &#34;Offer&#34;, &#34;price&#34;: &#34;299&#34;, &#34;priceCurrency&#34;: &#34;USD&#34;&#125;, &#34;description&#34;: &#34;AI-assisted self-help document preparation for residential tenants facing eviction.&#34;&#125;, &#123;&#34;@type&#34;: &#34;WebPage&#34;, &#34;@id&#34;: &#34;{canonical}#webpage&#34;, &#34;url&#34;: &#34;{canonical}&#34;, &#34;name&#34;: &#34;{title}&#34;, &#34;description&#34;: &#34;{description}&#34;, &#34;isPartOf&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#website&#34;&#125;, &#34;about&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#service&#34;&#125;&#125;, &#123;&#34;@type&#34;: &#34;WebSite&#34;, &#34;@id&#34;: &#34;https://evictions.help/#website&#34;, &#34;url&#34;: &#34;https://evictions.help/&#34;, &#34;name&#34;: &#34;evictions.help&#34;, &#34;publisher&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#organization&#34;&#125;&#125;, &#123;&#34;@type&#34;: &#34;BreadcrumbList&#34;, &#34;itemListElement&#34;: [&#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 1, &#34;name&#34;: &#34;Home&#34;, &#34;item&#34;: &#34;https://evictions.help/&#34;&#125;, &#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 2, &#34;name&#34;: &#34;{state_name}&#34;, &#34;item&#34;: &#34;https://evictions.help/{state_slug}/&#34;&#125;&#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 3, &#34;name&#34;: &#34;{county_name} County&#34;, &#34;item&#34;: &#34;https://evictions.help/{state_slug}/{county_slug}/&#34;&#125;&#125;]&#125;</script></head>
<body {body_attrs}>
<header class="site-header"><div class="container nav"><a class="brand" href="/" aria-label="evictions.help home"><img src="/assets/evictions-help-logo.png" alt="evictions.help"></a><nav class="nav-links" aria-label="Primary"><a href="/#included">What's included</a><a href="/#how-it-works">How it works</a><a href="/#states">States</a><a href="/#faq">FAQ</a><a href="/contact">Contact</a><a class="nav-cta" href="#eligibility">Check eligibility</a></nav><button class="mobile-menu" aria-label="Open menu">☰</button></div></header>
<nav class="breadcrumb container" aria-label="Breadcrumb"><ol>{breadcrumb}</ol></nav>
<section class="hero"><div class="container hero-grid"><div class="hero-copy"><span class="eyebrow">{eyebrow}</span><h1>{h1}</h1><p class="lede">{lede}</p><div class="price-row"><span class="price">$399</span><span class="price-note">flat fee · digital packet</span></div><div class="trust-row"><span class="trust-chip"><i class="check">✓</i> 8-question screening</span><span class="trust-chip"><i class="check">✓</i> Guided AI intake</span><span class="trust-chip"><i class="check">✓</i> Downloadable packet</span></div><p class="hero-note">Self-help document preparation only. evictions.help is not a law firm and does not provide legal advice or representation. No court outcome is guaranteed.</p></div><form id="eligibility" class="screen-card eligibility-form" {body_attrs}><div class="screen-head"><h2>See whether you can continue</h2><p>Answer eight questions. No payment is collected during eligibility.</p></div><div class="progress" aria-hidden="true"><span></span></div><div class="screen-body">
'''


def build_footer(state_abbr, state_name, state_slug, county_name, county_slug, city_name, city_slug, is_city):
    if is_city:
        cta_title = f"Check eligibility from {city_name}"
    else:
        cta_title = f"Start a packet for {county_name} County"
    cta_p = "The screening above is free to complete. Payment comes only after the program indicates that the tenant can continue." if is_city else "Your state and county are prefilled above. Check eligibility before proceeding to the $399 checkout."

    return f'''</div></div></form></div></section>
<section class="section"><div class="container"><div class="callout"><h2>{cta_title}</h2><p>{cta_p}</p><a class="btn btn-secondary" href="#eligibility">Check Eligibility</a></div></div></section>
<div class="sticky-mobile"><span>Start with 8 questions<br><small>No payment yet</small></span><a class="btn btn-primary" href="#eligibility">Check eligibility</a></div>
<footer class="footer"><div class="container"><div class="footer-grid"><div><img src="/assets/evictions-help-logo.png" alt="evictions.help"><p>AI-assisted self-help document preparation for residential tenants facing eviction. Flat fee: $399.</p></div><div><h3>Program</h3><div class="footer-links"><a href="/#included">Packet contents</a><a href="/#how-it-works">How it works</a><a href="/#states">Supported states</a><a href="/#faq">Frequently asked questions</a></div></div><div><h3>Important</h3><div class="footer-links"><a href="/terms/">Terms of use</a><a href="/privacy/">Privacy</a><a href="/disclaimer/">Legal disclaimer</a><a href="mailto:support@evictions.help">support@evictions.help</a></div></div></div><div class="footer-bottom">© 2026 evictions.help. Self-help document preparation. Not a law firm. Not legal advice. No outcome is guaranteed.</div></div></footer>
<script src="/assets/site.js" defer></script></body></html>'''


def build_packet_section():
    return '''<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Packet contents</span><h2>What a qualified tenant can prepare</h2></div><div class="cards"><article class="card"><div class="card-icon">✓</div><h3>Official court answer form</h3><p>Prepared with the case and party information collected during intake.</p></article><article class="card"><div class="card-icon">✓</div><h3>Fee-waiver application</h3><p>Included when the tenant provides the financial information required for preparation.</p></article><article class="card"><div class="card-icon">✓</div><h3>Emergency action plan</h3><p>A prioritized checklist for the next 24 hours and the next stage of the case.</p></article><article class="card"><div class="card-icon">✓</div><h3>Eviction-process timeline</h3><p>A state-oriented overview from notice through hearing and judgment.</p></article><article class="card"><div class="card-icon">✓</div><h3>Defenses explained</h3><p>Plain-language descriptions to help the tenant understand the selections made during intake.</p></article><article class="card"><div class="card-icon">✓</div><h3>Evidence guide</h3><p>A practical list of records, photographs, messages, receipts, and notices to organize.</p></article></div></div></section>'''


def generate_content_for(name, state_name, tier):
    """Generate LLM content for a city or county."""
    system = (
        "You are a local writer crafting natural, human-sounding website copy about US locations. "
        "Write as if you're a knowledgeable local, not a Wikipedia article. "
        "No markdown, no em dashes, no hashtags, no asterisks. "
        "Use plain paragraph text only. Sound like a person, not a bot."
    )
    if tier == 'city':
        user = (
            f"Write 2 short paragraphs about {name}, {state_name}.\n\n"
            f"Paragraph 1: What {name} is known for -- a landmark, industry, or cultural "
            f"characteristic that locals identify with. One or two sentences.\n\n"
            f"Paragraph 2: What tenants in {name} should understand about the local rental "
            f"market and where to turn for housing help. Two or three sentences. "
            f"Practical, grounded, not legal advice.\n\n"
            f"Return just the 2 paragraphs, separated by a blank line. No labels, no numbers."
        )
    else:
        user = (
            f"Write 2 short paragraphs about {name} County, {state_name}.\n\n"
            f"Paragraph 1: What makes {name} County distinct -- its largest city, "
            f"a notable landmark, or something people associate with the area. "
            f"One or two sentences. Sound local and natural.\n\n"
            f"Paragraph 2: What a renter in {name} County should know about finding rental "
            f"housing help or navigating the court system. Mention the county seat if relevant. "
            f"Two or three sentences. Practical, not legal advice.\n\n"
            f"Return just the 2 paragraphs, separated by a blank line. No labels, no numbers."
        )
    return llm_generate(system, user)


def build_county_page(county_name, state_abbr, state_slug, state_name, county_pop, cities_list):
    """Build a county page HTML."""
    county_slug = slugify(county_name) + '-county'

    # Check existing county dir for correct slug (handles 'parish' for LA)
    existing_slug = None
    state_dir = os.path.join(SEO_DIR, state_slug)
    if os.path.exists(state_dir):
        try:
            for d in os.listdir(state_dir):
                if d.replace('-county', '').replace('-', ' ').lower() == county_name.lower() or \
                   d.replace('-parish', '').replace('-', ' ').lower() == county_name.lower():
                    existing_slug = d
                    break
        except OSError:
            pass
    if existing_slug:
        county_slug = existing_slug

    # Generate content
    text = generate_content_for(county_name, state_name, 'county')
    if text:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    else:
        paragraphs = []
    if len(paragraphs) < 2:
        paragraphs = [
            f"{county_name} County is a community in {state_name} with a growing rental market.",
            f"Tenants in {county_name} County should contact local housing resources and legal aid for guidance on the eviction process.",
        ]
    content_p = '\n'.join(f'<p>{p}</p>' for p in paragraphs[:2])

    pop_display = f"{county_pop:,}" if county_pop else "residents"

    # Build cities list HTML
    cities_html = ""
    if cities_list:
        for c in cities_list:
            c_slug = slugify(c['city'])
            cities_html += f'<a class="location-link" href="/{state_slug}/{county_slug}/{c_slug}/">{c["city"]}<small>{c["population"]:,} residents</small></a>\n'
    else:
        cities_html = f'<a class="location-link" href="/{state_slug}/">All {state_name} locations<small>State directory</small></a>\n'

    head = build_header_and_hero(state_abbr, state_name, state_slug, county_name, county_slug, "", "", False)
    form = build_form_html(state_abbr, f"{county_name} County", "", f"mnt-data-evictions-help-seo-website-public-{state_slug}-{county_slug}-index-html")
    footer = build_footer(state_abbr, state_name, state_slug, county_name, county_slug, "", "", False)

    middle = f'''<section class="section"><div class="container">
{content_p}
</div></section>

<section class="section"><div class="container split"><div><span class="eyebrow">Local case organization</span><h2>Prepare with the correct local context</h2><p class="lede">{county_name} County is a community in {state_name} with an estimated {pop_display}.</p><p>Regional renter market</p><p>The eligibility form carries {county_name} County into checkout and intake so the program can preserve the tenant's location throughout document preparation.</p></div><div class="feature-list"><div class="feature"><i class="check">1</i><div><strong>Keep the court papers together</strong><span>Use the exact party names, case number, court, and hearing information shown on the filed documents.</span></div></div><div class="feature"><i class="check">2</i><div><strong>Document payments and notices</strong><span>Organize receipts, ledgers, repair requests, messages, photographs, and assistance applications.</span></div></div><div class="feature"><i class="check">3</i><div><strong>Verify local filing requirements</strong><span>Confirm deadlines, filing methods, service rules, and any required registry payment with the court or qualified legal help.</span></div></div></div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Communities in this directory</span><h2>City pages connected to {county_name} County</h2><p>These are among the largest communities selected for the city-page rollout.</p></div><div class="location-grid">{cities_html}</div></div></section>
{build_packet_section()}
<section class="section"><div class="container"><div class="section-intro"><span class="eyebrow">Statewide starting points</span><h2>Resources that may serve {county_name} County</h2><p>These statewide or regional portals are starting points, not guarantees of funding or representation. Confirm current eligibility and service areas.</p></div><div class="resource-list">{build_resource_html(state_abbr)}</div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Nearby directories</span><h2>Other {state_name} locations</h2></div><div class="location-grid"><a class="location-link" href="/{state_slug}/">All {state_name} locations<small>State directory</small></a></div></div></section>
'''

    # Insert form into head, then middle, then footer
    return head + form + middle + footer


def build_city_page(city_name, state_abbr, state_slug, state_name, county_name, county_slug, city_pop):
    city_slug = slugify(city_name)

    text = generate_content_for(city_name, state_name, 'city')
    if text:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    else:
        paragraphs = []
    if len(paragraphs) < 2:
        paragraphs = [
            f"{city_name} is a community in {county_name} County, {state_name}.",
            f"Tenants in {city_name} should reach out to local housing resources and legal aid organizations for guidance on the eviction process.",
        ]
    content_p = '\n'.join(f'<p>{p}</p>' for p in paragraphs[:2])

    pop_display = f"{city_pop:,}" if city_pop else "50,000+"

    head = build_header_and_hero(state_abbr, state_name, state_slug, county_name, county_slug, city_name, city_slug, True)
    form = build_form_html(state_abbr, f"{county_name} County", city_name, f"mnt-data-evictions-help-seo-website-public-{state_slug}-{county_slug}-{city_slug}-index-html")
    footer = build_footer(state_abbr, state_name, state_slug, county_name, county_slug, city_name, city_slug, True)

    middle = f'''<section class="section"><div class="container">
{content_p}
</div></section>

<section class="section"><div class="container split"><div><span class="eyebrow">{city_name} self-help preparation</span><h2>Your city, county, and state stay connected</h2><p class="lede">{city_name} is listed with {county_name} County in the site's local navigation and had an estimated 2024 population of {pop_display}.</p><p>The page does not claim that evictions are handled by a city-specific court. Instead, it carries the city and county into the eligibility and intake flow so the tenant can enter the court information shown on the actual papers.</p></div><div class="feature-list"><div class="feature"><i class="check">✓</i><div><strong>Location prefilled</strong><span>{city_name}, {county_name} County, {state_name} is preserved in the intake.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Case-specific questions</strong><span>The intake asks for the landlord, court, case number, dates, amount claimed, payments, defenses, and preferences.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Conditional documents</strong><span>Letters and motions are included only when the tenant's answers support them.</span></div></div></div></div></section>
{build_packet_section()}
<section class="section"><div class="container"><div class="section-intro"><span class="eyebrow">Resource starting points</span><h2>Housing and legal-information portals for {state_name}</h2></div><div class="resource-list">{build_resource_html(state_abbr)}</div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Continue exploring</span><h2>Related local pages</h2></div><div class="location-grid"><a class="location-link" href="/{state_slug}/">All {state_name} locations<small>State directory</small></a><a class="location-link" href="/{state_slug}/{county_slug}/">{county_name} County<small>County directory</small></a></div></div></section>
'''

    return head + form + middle + footer


# ── Main ───────────────────────────────────────────────────

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return {"done_counties": [], "done_cities": [], "cities_info": {}}

def save_progress(prog):
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(prog, f)
    except OSError:
        pass


def get_existing_county_slug(state_slug, county_name):
    """Return existing county directory slug if it exists."""
    state_dir = os.path.join(SEO_DIR, state_slug)
    if not os.path.exists(state_dir):
        return None
    norm = county_name.lower()
    try:
        for d in os.listdir(state_dir):
            base = d.replace('-county', '').replace('-parish', '').replace('-', ' ').lower()
            if base == norm:
                return d
    except OSError:
        pass
    return None


def main():
    parser = ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    print(f"LLM key present: {bool(LLM_API_KEY)}", flush=True)

    progress = load_progress() if args.resume else {"done_counties": [], "done_cities": [], "cities_info": {}}

    # Step 1: fetch all 50K+ cities
    print("Fetching Wikipedia city list...", flush=True)
    all_cities = fetch_cities_50k()
    print(f"Found {len(all_cities)} cities with 50K+ in our 20 states", flush=True)

    # Step 2: find existing city pages
    existing_cities = set()
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
                        existing_cities.add(f"{state_slug}/{county}/{city}")
        except OSError:
            continue

    # Step 3: identify missing cities
    missing = []
    for c in all_cities:
        norm = slugify(c['city'])
        if not any(ep.endswith('/' + norm) for ep in existing_cities):
            missing.append(c)

    print(f"Missing cities: {len(missing)}", flush=True)

    # Step 4: determine counties for missing cities (with progress caching)
    cities_by_county = {}  # (state_slug, county_name) -> [city dicts]
    for i, c in enumerate(missing):
        key = f"{c['state_slug']}|{c['city']}"
        if key in progress.get('cities_info', {}):
            county_name = progress['cities_info'][key].get('county')
            pop = progress['cities_info'][key].get('pop')
        else:
            print(f"[{i+1}/{len(missing)}] Resolving {c['city']}, {c['state_abbr']}...", flush=True)
            county_name, pop = get_county_and_pop(c['city'], c['state_abbr'])
            progress.setdefault('cities_info', {})[key] = {'county': county_name, 'pop': pop}
            save_progress(progress)
            time.sleep(2.0)

        if not county_name:
            print(f"  SKIP: no county for {c['city']}", flush=True)
            continue

        # Clean county name (strip "County, State" suffix)
        county_name = county_name.replace(' County', '').replace(', ' + STATE_ABBR_TO_NAME.get(c['state_abbr'], ''), '')
        c['county'] = county_name
        c['county_pop'] = pop or c['population']

        group_key = (c['state_slug'], county_name)
        cities_by_county.setdefault(group_key, []).append(c)
        print(f"  → {county_name} County (pop {pop or c['population']:,})", flush=True)

    if args.limit:
        # Limit total cities processed
        cities_by_county = {k: v[:args.limit] for k, v in list(cities_by_county.items())[:args.limit]}

    print(f"\nCounties needing pages or updates: {len(cities_by_county)}", flush=True)

    # Step 5: generate county pages + city pages
    county_count = 0
    city_count = 0

    for (state_slug, county_name), cities in sorted(cities_by_county.items()):
        state_abbr = {v: k for k, v in COVERED_STATES.items()}[state_slug]
        state_name = STATE_ABBR_TO_NAME[state_abbr]

        existing_slug = get_existing_county_slug(state_slug, county_name)
        county_slug = existing_slug or (slugify(county_name) + '-county')

        # Get county population (use max of city pops as fallback)
        county_pop = max((c.get('county_pop') or c['population'] for c in cities), default=None)

        if not existing_slug:
            # Need to create county page
            if args.dry_run:
                print(f"WOULD CREATE county: {state_slug}/{county_slug} ({len(cities)} cities)", flush=True)
            else:
                print(f"\nCreating county: {state_name} / {county_name} County", flush=True)
                html = build_county_page(county_name, state_abbr, state_slug, state_name, county_pop, cities)
                county_dir = os.path.join(SEO_DIR, state_slug, county_slug)
                try:
                    os.makedirs(county_dir, exist_ok=True)
                    with open(os.path.join(county_dir, 'index.html'), 'w', encoding='utf-8') as f:
                        f.write(html)
                    print(f"  ✓ County page created", flush=True)
                    county_count += 1
                except OSError as e:
                    print(f"  FAIL: {e}", flush=True)
                    continue
                time.sleep(1.5)
        else:
            # County exists - will update city links later
            pass

        # Generate city pages
        for c in cities:
            city_slug = slugify(c['city'])
            city_dir = os.path.join(SEO_DIR, state_slug, county_slug, city_slug)

            if os.path.exists(os.path.join(city_dir, 'index.html')):
                print(f"  SKIP (exists): {city_slug}", flush=True)
                continue

            if args.dry_run:
                print(f"WOULD CREATE city: {state_slug}/{county_slug}/{city_slug}", flush=True)
                continue

            print(f"  Creating city: {c['city']} ({c['population']:,})", flush=True)
            html = build_city_page(c['city'], state_abbr, state_slug, state_name, county_name, county_slug, c['population'])
            try:
                os.makedirs(city_dir, exist_ok=True)
                with open(os.path.join(city_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"    ✓ City page created", flush=True)
                city_count += 1
            except OSError as e:
                print(f"    FAIL: {e}", flush=True)
                continue
            time.sleep(1.5)

    print(f"\n{'='*60}", flush=True)
    print(f"Counties created: {county_count}", flush=True)
    print(f"Cities created: {city_count}", flush=True)


if __name__ == '__main__':
    main()
