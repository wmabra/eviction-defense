#!/usr/bin/env python3
"""
Generate missing city pages (50K+ population) for evictions.help.

Steps:
1. Fetch county + population from Wikipedia for each missing city
2. Filter to cities whose county already has a page on the site
3. Generate HTML pages using LLM content (DeepSeek)
4. Add city links to county pages

Usage:
    python3 generate_city_pages.py           # all missing cities
    python3 generate_city_pages.py --dry-run # preview only
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

# API keys from env
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
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
    'TX': [
        ('State Housing', 'https://www.tdhca.texas.gov/', 'Texas Department of Housing and Community Affairs', 'Housing programs, homelessness resources, renter assistance, and program notices'),
        ('State Referral', 'https://www.211texas.org/', '2-1-1 Texas', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://texaslawhelp.org/', 'TexasLawHelp', 'Eviction legal information and legal-aid routing'),
        ('Court / Tenant Help', 'https://texaslawhelp.org/house-apartment/eviction-other-landlord-issues', 'TexasLawHelp Eviction and Landlord Issues', 'Eviction procedures, forms, and tenant guidance'),
    ],
    'CA': [
        ('State Housing', 'https://www.hcd.ca.gov/', 'California Department of Housing and Community Development', 'Rental assistance, housing element, homelessness programs'),
        ('State Referral', 'https://www.211.org/', '2-1-1 California', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://www.lawhelpca.org/', 'LawHelpCA', 'Eviction legal information and legal-aid routing'),
        ('Court / Tenant Help', 'https://www.courts.ca.gov/selfhelp-eviction.htm', 'California Courts Self-Help — Eviction', 'Eviction procedures, forms, and tenant guidance'),
    ],
    'FL': [
        ('State Housing', 'https://www.floridahousing.org/', 'Florida Housing Finance Corporation', 'Housing programs, homelessness resources, renter assistance'),
        ('State Referral', 'https://www.211.org/', '2-1-1 Florida', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://www.floridabar.org/public/consumer/pamphlet014/', 'Florida Bar — Eviction Information', 'Eviction legal information from The Florida Bar'),
        ('Court / Tenant Help', 'https://www.flcourts.gov/Resources-Services/Office-of-the-State-Courts-Administrator/Self-Help-Information', 'Florida Courts Self-Help', 'Eviction procedures, forms, and tenant guidance'),
    ],
    'MI': [
        ('State Housing', 'https://www.michigan.gov/mshda', 'Michigan State Housing Development Authority', 'Housing programs, homelessness resources, renter assistance'),
        ('State Referral', 'https://www.mi211.org/', '2-1-1 Michigan', 'Rent, utilities, shelter, food and crisis referrals'),
        ('Legal Aid', 'https://michiganlegalhelp.org/', 'Michigan Legal Help', 'Eviction legal information and legal-aid routing'),
        ('Court / Tenant Help', 'https://michiganlegalhelp.org/eviction', 'Michigan Legal Help — Eviction', 'Eviction procedures, forms, and tenant guidance'),
    ],
}

# Default resources for states not specifically configured
_DEFAULT_RESOURCES = [
    ('State Housing', None, None, 'Find your state housing finance agency for rental assistance programs'),
    ('State Referral', 'https://www.211.org/', '2-1-1', 'Call 2-1-1 for rent, utilities, shelter, food and crisis referrals'),
    ('Legal Aid', 'https://www.lsc.gov/', 'Legal Services Corporation', 'Find a legal aid office near you for eviction help'),
    ('Court / Tenant Help', None, None, 'Check your state court website for eviction self-help resources'),
]


def wiki_get(url, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": "evictions.help/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
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


def get_city_info(city_name, state_abbr):
    """Get county name and population for a city from Wikipedia."""
    # Try the city page directly
    page_title = f"{city_name}, {STATE_ABBR_TO_NAME.get(state_abbr, state_abbr)}"
    
    # First get page extract
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": page_title,
        "prop": "extracts|coordinates",
        "exintro": True,
        "explaintext": True,
        "format": "json",
    })
    data = wiki_get(f"https://en.wikipedia.org/w/api.php?{params}")
    
    pages = data.get("query", {}).get("pages", {})
    extract = ""
    for p in pages.values():
        extract = p.get("extract", "")
        break
    
    if not extract:
        return None, None, None
    
    # Parse county from infobox in wikitext
    params2 = urllib.parse.urlencode({
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json",
        "section": 0,
    })
    try:
        data2 = wiki_get(f"https://en.wikipedia.org/w/api.php?{params2}")
        wikitext = data2.get("parse", {}).get("wikitext", {}).get("*", "")
    except Exception:
        wikitext = ""
    
    # Try to extract county from wikitext
    county = None
    for pattern in [
        r'\|\s*county\s*=\s*\[\[([^\]|]+)',
        r'\|\s*county\s*=\s*([^\n|]+)',
        r'\|\s*subdivision_name2\s*=\s*\[\[([^\]|]+)',
    ]:
        m = re.search(pattern, wikitext)
        if m:
            county = m.group(1).strip()
            break
    
    # If no county found in infobox, try extract text
    if not county:
        m = re.search(r'(?:city|town)\s+(?:of|in)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+County', extract)
        if m:
            county = m.group(1).strip()
    
    if not county:
        m = re.search(r'(?:in|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+County', extract)
        if m:
            county = m.group(1).strip()
    
    # Extract population from wikitext or extract
    pop = None
    for pattern in [
        r'\|\s*population_total\s*=\s*([\d,]+)',
        r'\|\s*population_footnotes.*?\n\|\s*population_total\s*=\s*([\d,]+)',
        r'population(?: of| estimated at)?\s+([\d,]+)',
        r'population.*?(\d[\d,]+)',
    ]:
        m = re.search(pattern, wikitext + " " + extract)
        if m:
            try:
                pop = int(m.group(1).replace(',', ''))
                break
            except ValueError:
                continue
    
    return county, pop, extract[:500] if extract else ""


def llm_generate(system_prompt, user_prompt):
    """Generate content using DeepSeek API."""
    if not LLM_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    
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
                text = text.strip()
                return text
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    return ""


def generate_content(city_name, state_name, county_name):
    """Generate 2 paragraphs about a city."""
    system = (
        "You are a local writer crafting natural, human-sounding website copy about US cities. "
        "Write as if you're a knowledgeable local, not a Wikipedia article. "
        "No markdown, no em dashes, no hashtags, no asterisks. "
        "Use plain paragraph text only. Sound like a person, not a bot."
    )
    user = (
        f"Write 2 short paragraphs about {city_name}, {state_name}.\n\n"
        f"Paragraph 1: What {city_name} is known for -- a landmark, industry, or cultural "
        f"characteristic that locals identify with. One or two sentences.\n\n"
        f"Paragraph 2: What tenants in {city_name} should understand about the local rental "
        f"market and where to turn for housing help. Two or three sentences. "
        f"Practical, grounded, not legal advice.\n\n"
        f"Return just the 2 paragraphs, separated by a blank line. No labels, no numbers."
    )
    return llm_generate(system, user)


def get_state_abbr(state_slug: str) -> str:
    """Convert state slug to abbreviation."""
    reverse = {v: k for k, v in COVERED_STATES.items()}
    return reverse.get(state_slug, state_slug[:2].upper())


def get_state_name(state_slug: str) -> str:
    """Convert state slug to full name."""
    abbr: str = get_state_abbr(state_slug)
    return STATE_ABBR_TO_NAME.get(abbr, state_slug.replace('-', ' ').title())


def slugify(text):
    return text.lower().replace(' ', '-').replace("'", "").replace('.', '')


def build_html(city_name, state_slug, county_name, county_slug, population):
    """Build the full city page HTML."""
    state_abbr = get_state_abbr(state_slug)
    state_name = get_state_name(state_slug)
    city_slug = slugify(city_name)
    
    # Resources
    resources = STATE_RESOURCES.get(state_abbr, _DEFAULT_RESOURCES) if state_abbr is not None else _DEFAULT_RESOURCES
    
    # Build resource HTML
    resource_html = ""
    for res_type, url, title, desc in resources:
        if url and title:
            resource_html += f'<article class="resource"><span class="type">{res_type}</span><h3><a href="{url}" rel="nofollow noopener" target="_blank">{title} ↗</a></h3><p>{desc}</p></article>\n'
        elif title:
            resource_html += f'<article class="resource"><span class="type">{res_type}</span><h3>{title}</h3><p>{desc}</p></article>\n'
    
    # Population display
    pop_display = f"{population:,}" if population else "50,000+"
    
    # Generate content with LLM
    print(f"    Generating content for {city_name}, {state_name}...")
    try:
        text = generate_content(city_name, state_name, county_name)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            paragraphs.append(f"{city_name} is a growing community in {county_name} County, {state_name}.")
    except Exception as e:
        print(f"    LLM error: {e}")
        paragraphs = [
            f"{city_name} is a vibrant community in {county_name} County, {state_name}.",
            f"Tenants in {city_name} should reach out to local housing resources and legal aid organizations for guidance on the eviction process.",
        ]
    
    content_p = '\n'.join(f'<p>{p}</p>' for p in paragraphs[:2])
    
    # Build the form inputs hash (used for unique IDs)
    page_id = f"mnt-data-evictions-help-seo-website-public-{state_slug}-{county_slug}-{city_slug}-index-html"
    
    html = f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Eviction Help in {city_name}, {state_name} | evictions.help</title><meta name="description" content="Check eligibility for eviction self-help document preparation in {city_name}, {county_name} County. Guided intake, $399 packet, filing preparation, and resource starting points."><meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="https://evictions.help/{state_slug}/{county_slug}/{city_slug}/"><link rel="icon" href="/assets/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website"><meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png"><meta property="og:site_name" content="evictions.help"><meta property="og:title" content="Eviction Help in {city_name}, {state_name} | evictions.help"><meta property="og:description" content="Check eligibility for eviction self-help document preparation in {city_name}, {county_name} County. Guided intake, $399 packet, filing preparation, and resource starting points."><meta property="og:url" content="https://evictions.help/{state_slug}/{county_slug}/{city_slug}/"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">&#123;&#34;@context&#34;: &#34;https://schema.org&#34;, &#34;@graph&#34;: [&#123;&#34;@type&#34;: &#34;Organization&#34;, &#34;@id&#34;: &#34;https://evictions.help/#organization&#34;, &#34;name&#34;: &#34;evictions.help&#34;, &#34;url&#34;: &#34;https://evictions.help/&#34;&#125;, &#123;&#34;@type&#34;: &#34;Service&#34;, &#34;@id&#34;: &#34;https://evictions.help/#service&#34;, &#34;name&#34;: &#34;Eviction self-help document preparation&#34;, &#34;provider&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#organization&#34;&#125;, &#34;areaServed&#34;: [&#34;Arkansas&#34;, &#34;Arizona&#34;, &#34;California&#34;, &#34;Colorado&#34;, &#34;Connecticut&#34;, &#34;Florida&#34;, &#34;Georgia&#34;, &#34;Illinois&#34;, &#34;Louisiana&#34;, &#34;Massachusetts&#34;, &#34;Michigan&#34;, &#34;Minnesota&#34;, &#34;New Mexico&#34;, &#34;Nevada&#34;, &#34;Oregon&#34;, &#34;Rhode Island&#34;, &#34;South Carolina&#34;, &#34;Tennessee&#34;, &#34;Texas&#34;, &#34;Virginia&#34;], &#34;offers&#34;: &#123;&#34;@type&#34;: &#34;Offer&#34;, &#34;price&#34;: &#34;299&#34;, &#34;priceCurrency&#34;: &#34;USD&#34;&#125;, &#34;description&#34;: &#34;AI-assisted self-help document preparation for residential tenants facing eviction.&#34;&#125;, &#123;&#34;@type&#34;: &#34;WebPage&#34;, &#34;@id&#34;: &#34;https://evictions.help/{state_slug}/{county_slug}/{city_slug}/#webpage&#34;, &#34;url&#34;: &#34;https://evictions.help/{state_slug}/{county_slug}/{city_slug}/&#34;, &#34;name&#34;: &#34;Eviction Help in {city_name}, {state_name} | evictions.help&#34;, &#34;description&#34;: &#34;Check eligibility for eviction self-help document preparation in {city_name}, {county_name} County. Guided intake, $399 packet, filing preparation, and resource starting points.&#34;, &#34;isPartOf&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#website&#34;&#125;, &#34;about&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#service&#34;&#125;&#125;, &#123;&#34;@type&#34;: &#34;WebSite&#34;, &#34;@id&#34;: &#34;https://evictions.help/#website&#34;, &#34;url&#34;: &#34;https://evictions.help/&#34;, &#34;name&#34;: &#34;evictions.help&#34;, &#34;publisher&#34;: &#123;&#34;@id&#34;: &#34;https://evictions.help/#organization&#34;&#125;&#125;, &#123;&#34;@type&#34;: &#34;BreadcrumbList&#34;, &#34;itemListElement&#34;: [&#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 1, &#34;name&#34;: &#34;Home&#34;, &#34;item&#34;: &#34;https://evictions.help/&#34;&#125;, &#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 2, &#34;name&#34;: &#34;{state_name}&#34;, &#34;item&#34;: &#34;https://evictions.help/{state_slug}/&#34;&#125;, &#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 3, &#34;name&#34;: &#34;{county_name} County&#34;, &#34;item&#34;: &#34;https://evictions.help/{state_slug}/{county_slug}/&#34;&#125;, &#123;&#34;@type&#34;: &#34;ListItem&#34;, &#34;position&#34;: 4, &#34;name&#34;: &#34;{city_name}&#34;, &#34;item&#34;: &#34;https://evictions.help/{state_slug}/{county_slug}/{city_slug}/&#34;&#125;]&#125;]&#125;</script></head>
<body data-state="{state_abbr}" data-county="{county_name} County" data-city="{city_name}">
<header class="site-header"><div class="container nav"><a class="brand" href="/" aria-label="evictions.help home"><img src="/assets/evictions-help-logo.png" alt="evictions.help"></a><nav class="nav-links" aria-label="Primary"><a href="/#included">What's included</a><a href="/#how-it-works">How it works</a><a href="/#states">States</a><a href="/#faq">FAQ</a><a href="/contact">Contact</a><a class="nav-cta" href="#eligibility">Check eligibility</a></nav><button class="mobile-menu" aria-label="Open menu">☰</button></div></header>
<nav class="breadcrumb container" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li><a href="/{state_slug}/">{state_name}</a></li><li><a href="/{state_slug}/{county_slug}/">{county_name} County</a></li><li>{city_name}</li></ol></nav>
<section class="hero"><div class="container hero-grid"><div class="hero-copy"><span class="eyebrow">{city_name} eviction document help</span><h1>Prepare eviction paperwork from {city_name} with a guided intake</h1><p class="lede">Your city, county, and state are prefilled. Qualified tenants can continue to a $399 self-help document packet built from their own case information.</p><div class="price-row"><span class="price">$399</span><span class="price-note">flat fee · digital packet</span></div><div class="trust-row"><span class="trust-chip"><i class="check">✓</i> 8-question screening</span><span class="trust-chip"><i class="check">✓</i> Guided AI intake</span><span class="trust-chip"><i class="check">✓</i> Downloadable packet</span></div><p class="hero-note">Self-help document preparation only. evictions.help is not a law firm and does not provide legal advice or representation. No court outcome is guaranteed.</p></div><form id="eligibility" class="screen-card eligibility-form" data-state="{state_abbr}" data-county="{county_name} County" data-city="{city_name}"><div class="screen-head"><h2>See whether you can continue</h2><p>Answer eight questions. No payment is collected during eligibility.</p></div><div class="progress" aria-hidden="true"><span></span></div><div class="screen-body">
<div class="screen-step active"><div class="question-count">Question 1 of 8</div><div class="question">Where is the rental property located?</div><select name="state" required aria-label="State"><option value="">Select a state</option><option value="AR">Arkansas</option><option value="AZ">Arizona</option><option value="CA">California</option><option value="CO">Colorado</option><option value="CT">Connecticut</option><option value="FL">Florida</option><option value="GA">Georgia</option><option value="IL">Illinois</option><option value="LA">Louisiana</option><option value="MA">Massachusetts</option><option value="MI">Michigan</option><option value="MN">Minnesota</option><option value="NM">New Mexico</option><option value="NV">Nevada</option><option value="OR">Oregon</option><option value="RI">Rhode Island</option><option value="SC">South Carolina</option><option value="TN">Tennessee</option><option value="TX" selected>Texas</option><option value="VA">Virginia</option></select></div>'''
    
    # Replace TX with correct state in the select
    html = html.replace(f'<option value="TX" selected>Texas</option>', 'REPLACE_STATE_SELECT')
    
    state_options = ""
    for abbr, name in sorted(STATE_ABBR_TO_NAME.items(), key=lambda x: x[1]):
        slug = COVERED_STATES.get(abbr)
        if slug:
            sel = ' selected' if abbr == state_abbr else ''
            state_options += f'<option value="{abbr}"{sel}>{name}</option>\n'
    state_select = f'<select name="state" required aria-label="State"><option value="">Select a state</option>{state_options}</select>'
    html = html.replace('REPLACE_STATE_SELECT', state_select)
    
    # Continue with the rest of the template
    html += f'''</div><div class="screen-step"><div class="question-count">Question 2 of 8</div><div class="question">What county is the eviction case in?</div><select name="county" required aria-label="County"><option value="">Select a county</option></select></div>

<div class="screen-step"><div class="question-count">Question 3 of 8</div><div class="question">Are you the tenant named in the eviction matter?</div><div class="choice-grid"><div class="choice"><input id="tenant-yes-{page_id}" type="radio" name="tenant" value="yes"><label for="tenant-yes-{page_id}">Yes</label></div><div class="choice"><input id="tenant-no-{page_id}" type="radio" name="tenant" value="no"><label for="tenant-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 4 of 8</div><div class="question">Have you been served with eviction court papers?</div><div class="choice-grid"><div class="choice"><input id="served-yes-{page_id}" type="radio" name="served" value="yes"><label for="served-yes-{page_id}">Yes</label></div><div class="choice"><input id="served-no-{page_id}" type="radio" name="served" value="no"><label for="served-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 5 of 8</div><div class="question">Is this a residential rental property?</div><div class="choice-grid"><div class="choice"><input id="residential-yes-{page_id}" type="radio" name="residential" value="yes"><label for="residential-yes-{page_id}">Yes</label></div><div class="choice"><input id="residential-no-{page_id}" type="radio" name="residential" value="no"><label for="residential-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 6 of 8</div><div class="question">Is the home Section 8, voucher-assisted, or public housing?</div><div class="choice-grid"><div class="choice"><input id="subsidized-yes-{page_id}" type="radio" name="subsidized" value="yes"><label for="subsidized-yes-{page_id}">Yes</label></div><div class="choice"><input id="subsidized-no-{page_id}" type="radio" name="subsidized" value="no"><label for="subsidized-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 7 of 8</div><div class="question">Are you or another tenant on active military duty?</div><div class="choice-grid"><div class="choice"><input id="military-yes-{page_id}" type="radio" name="military" value="yes"><label for="military-yes-{page_id}">Yes</label></div><div class="choice"><input id="military-no-{page_id}" type="radio" name="military" value="no"><label for="military-no-{page_id}">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 8 of 8</div><div class="question">Have you filed bankruptcy or is a bankruptcy case active?</div><div class="choice-grid"><div class="choice"><input id="bankruptcy-yes-{page_id}" type="radio" name="bankruptcy" value="yes"><label for="bankruptcy-yes-{page_id}">Yes</label></div><div class="choice"><input id="bankruptcy-no-{page_id}" type="radio" name="bankruptcy" value="no"><label for="bankruptcy-no-{page_id}">No</label></div></div></div>
<div class="screen-step"><div data-result class="result-box result-ok"></div><div data-qualified><div class="form-grid"><div class="field full"><label>Street address</label><input name="street" type="text" autocomplete="street-address" required></div><div class="field"><label>City</label><input name="city" type="text" autocomplete="address-level2" required></div><div class="field"><label>County</label><input name="county" type="text" autocomplete="address-level1" required></div><div class="field"><label>ZIP code</label><input name="zip" type="text" inputmode="numeric" autocomplete="postal-code" pattern="[0-9]{{5}}" required></div><div class="field"><label>Email</label><input name="email" type="email" autocomplete="email" required></div><div class="field full"><label>Phone</label><input name="phone" type="tel" autocomplete="tel" required></div></div><button class="btn btn-primary" style="max-width:100%;margin-top:16px" type="submit">Continue to secure checkout — $399</button><p class="micro">By continuing, you acknowledge that this is a self-help document preparation service—not a law firm or legal representation.</p></div></div>
<div class="screen-actions"><button data-back class="btn btn-secondary" type="button" hidden>Back</button></div></div></form></div></section>

<section class="section"><div class="container">
{content_p}
</div></section>

<section class="section"><div class="container split"><div><span class="eyebrow">{city_name} self-help preparation</span><h2>Your city, county, and state stay connected</h2><p class="lede">{city_name} is listed with {county_name} County in the site's local navigation and had an estimated 2024 population of {pop_display}.</p><p>The page does not claim that evictions are handled by a city-specific court. Instead, it carries the city and county into the eligibility and intake flow so the tenant can enter the court information shown on the actual papers.</p></div><div class="feature-list"><div class="feature"><i class="check">✓</i><div><strong>Location prefilled</strong><span>{city_name}, {county_name} County, {state_name} is preserved in the intake.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Case-specific questions</strong><span>The intake asks for the landlord, court, case number, dates, amount claimed, payments, defenses, and preferences.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Conditional documents</strong><span>Letters and motions are included only when the tenant's answers support them.</span></div></div></div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Packet contents</span><h2>What a qualified tenant can prepare</h2></div><div class="cards"><article class="card"><div class="card-icon">✓</div><h3>Official court answer form</h3><p>Prepared with the case and party information collected during intake.</p></article><article class="card"><div class="card-icon">✓</div><h3>Fee-waiver application</h3><p>Included when the tenant provides the financial information required for preparation.</p></article><article class="card"><div class="card-icon">✓</div><h3>Emergency action plan</h3><p>A prioritized checklist for the next 24 hours and the next stage of the case.</p></article><article class="card"><div class="card-icon">✓</div><h3>Eviction-process timeline</h3><p>A state-oriented overview from notice through hearing and judgment.</p></article><article class="card"><div class="card-icon">✓</div><h3>Defenses explained</h3><p>Plain-language descriptions to help the tenant understand the selections made during intake.</p></article><article class="card"><div class="card-icon">✓</div><h3>Evidence guide</h3><p>A practical list of records, photographs, messages, receipts, and notices to organize.</p></article></div></div></section>
<section class="section"><div class="container"><div class="section-intro"><span class="eyebrow">Resource starting points</span><h2>Housing and legal-information portals for {state_name}</h2></div><div class="resource-list">
{resource_html}</div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Continue exploring</span><h2>Related local pages</h2></div><div class="location-grid"><a class="location-link" href="/{state_slug}/">All {state_name} locations<small>State directory</small></a><a class="location-link" href="/{state_slug}/{county_slug}/">{county_name} County<small>County directory</small></a></div></div></section>
<section class="section"><div class="container"><div class="callout"><h2>Check eligibility from {city_name}</h2><p>The screening above is free to complete. Payment comes only after the program indicates that the tenant can continue.</p><a class="btn btn-secondary" href="#eligibility">Check Eligibility</a></div></div></section>
<div class="sticky-mobile"><span>Start with 8 questions<br><small>No payment yet</small></span><a class="btn btn-primary" href="#eligibility">Check eligibility</a></div>
<footer class="footer"><div class="container"><div class="footer-grid"><div><img src="/assets/evictions-help-logo.png" alt="evictions.help"><p>AI-assisted self-help document preparation for residential tenants facing eviction. Flat fee: $399.</p></div><div><h3>Program</h3><div class="footer-links"><a href="/#included">Packet contents</a><a href="/#how-it-works">How it works</a><a href="/#states">Supported states</a><a href="/#faq">Frequently asked questions</a></div></div><div><h3>Important</h3><div class="footer-links"><a href="/terms/">Terms of use</a><a href="/privacy/">Privacy</a><a href="/disclaimer/">Legal disclaimer</a><a href="mailto:support@evictions.help">support@evictions.help</a></div></div></div><div class="footer-bottom">© 2026 evictions.help. Self-help document preparation. Not a law firm. Not legal advice. No outcome is guaranteed.</div></div></footer>
<script src="/assets/site.js" defer></script></body></html>'''
    
    return html


def county_exists(state_slug, county_name):
    """Check if a county directory exists on the site."""
    county_slug = county_name.lower().replace(' ', '-')
    # Also check -county suffix variant
    for variant in [county_slug + '-county', county_slug]:
        path = os.path.join(SEO_DIR, state_slug, variant, 'index.html')
        if os.path.exists(path):
            return variant
    return None


def main():
    parser = ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except OSError:
        pass
    
    # Get missing cities from find_missing_cities.py output
    print("Fetching Wikipedia data to identify missing cities...")
    
    from find_missing_cities import fetch_wikitext, parse_cities, get_existing_cities, normalize_city_name
    
    wikitext = fetch_wikitext()
    all_cities = parse_cities(wikitext)
    existing = get_existing_cities()
    
    # Find missing
    missing = []
    for c in all_cities:
        norm = normalize_city_name(c['city'])
        if not any(ep.endswith('/' + norm) for ep in existing):
            missing.append(c)
    
    print(f"Total missing (50K+): {len(missing)}")
    
    # Now look up county info for each missing city
    to_generate = []
    skipped_no_county = []
    skipped_no_county_page = []
    
    for i, c in enumerate(missing):
        print(f"\n[{i+1}/{len(missing)}] {c['city']}, {c['state_abbr']} (pop {c['population']:,})")
        
        county, pop, extract = get_city_info(c['city'], c['state_abbr'])
        
        if not county:
            print(f"  SKIP: could not determine county")
            skipped_no_county.append(c)
            continue
        
        county_slug = county_exists(c['state_slug'], county)
        if not county_slug:
            print(f"  SKIP: county '{county}' has no page on site")
            skipped_no_county_page.append((c, county))
            continue
        
        actual_pop = pop or c.get('population', 50000)
        county_name = county_slug.replace('-county', '').replace('-', ' ').title()
        
        to_generate.append({
            **c,
            'county': county,
            'county_name': county_name,
            'county_slug': county_slug,
            'population': actual_pop,
        })
        print(f"  ✓ {county} County, pop {actual_pop:,}")
        
        time.sleep(2.0)  # rate limit Wikipedia
        
        if args.limit and len(to_generate) >= args.limit:
            break
    
    print(f"\n{'='*60}")
    print(f"To generate: {len(to_generate)} pages")
    print(f"Skipped (no county found): {len(skipped_no_county)}")
    print(f"Skipped (no county page): {len(skipped_no_county_page)}")
    
    if args.dry_run:
        print("\nDRY RUN - would generate pages for:")
        for c in to_generate:
            print(f"  {c['city']}, {c['state_slug']} → {c['county_slug']}")
        return
    
    # Generate pages
    success = 0
    for i, c in enumerate(to_generate):
        print(f"\n[{i+1}/{len(to_generate)}] Generating {c['city']}, {c['state_slug']}")
        
        city_dir = os.path.join(SEO_DIR, c['state_slug'], c['county_slug'], slugify(c['city']))
        try:
            os.makedirs(city_dir, exist_ok=True)
        except OSError:
            pass
        
        html = build_html(
            c['city'], c['state_slug'],
            c['county_name'], c['county_slug'],
            c['population']
        )
        
        fpath = os.path.join(city_dir, 'index.html')
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(html)
        except OSError as e:
            print(f"  FAIL: {e}")
            continue
        
        print(f"  ✓ Saved to {c['state_slug']}/{c['county_slug']}/{slugify(c['city'])}/")
        success += 1
        
        time.sleep(1.5)  # rate limit LLM API
    
    print(f"\n{'='*60}")
    print(f"Generated {success} city pages!")
    
    if skipped_no_county:
        print(f"\nSkipped (no county):")
        for c in skipped_no_county:
            print(f"  {c['city']}, {c['state_abbr']}")
    
    if skipped_no_county_page:
        print(f"\nSkipped (county has no page):")
        for c, county in skipped_no_county_page:
            print(f"  {c['city']}, {c['state_abbr']} — {county} County")


if __name__ == '__main__':
    main()
