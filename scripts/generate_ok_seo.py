#!/usr/bin/env python3
"""
Generate Oklahoma SEO pages: state page, all county pages, and 50K+ city pages.

Uses DeepSeek for location content. Run on the server (SEO_DIR = /opt/eviction-defense/seo).
"""
import os, json, time, re, urllib.request, urllib.parse

SEO_DIR = "/opt/eviction-defense/seo"
STATE_SLUG = "oklahoma"
STATE_NAME = "Oklahoma"
STATE_ABBR = "OK"

# Load DeepSeek key
for env_path in ["/opt/eviction-defense/.env"]:
    if os.path.exists(env_path):
        try:
            env_lines = open(env_path).read().splitlines()
        except OSError:
            env_lines = []
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
LLM_URL = "https://api.deepseek.com/v1/chat/completions"
LLM_MODEL = "deepseek-chat"

# All 114 MO counties + St. Louis City (independent city)
COUNTIES = [
    "Adair",
    "Alfalfa",
    "Atoka",
    "Beaver",
    "Beckham",
    "Blaine",
    "Bryan",
    "Caddo",
    "Canadian",
    "Carter",
    "Cherokee",
    "Choctaw",
    "Cimarron",
    "Cleveland",
    "Coal",
    "Comanche",
    "Cotton",
    "Craig",
    "Creek",
    "Custer",
    "Delaware",
    "Dewey",
    "Ellis",
    "Garfield",
    "Garvin",
    "Grady",
    "Grant",
    "Greer",
    "Harmon",
    "Harper",
    "Haskell",
    "Hughes",
    "Jackson",
    "Jefferson",
    "Johnston",
    "Kay",
    "Kingfisher",
    "Kiowa",
    "Latimer",
    "Le Flore",
    "Lincoln",
    "Logan",
    "Love",
    "Major",
    "Marshall",
    "Mayes",
    "McClain",
    "McCurtain",
    "McIntosh",
    "Murray",
    "Muskogee",
    "Noble",
    "Nowata",
    "Okfuskee",
    "Oklahoma",
    "Okmulgee",
    "Osage",
    "Ottawa",
    "Pawnee",
    "Payne",
    "Pittsburg",
    "Pontotoc",
    "Pottawatomie",
    "Pushmataha",
    "Roger Mills",
    "Rogers",
    "Seminole",
    "Sequoyah",
    "Stephens",
    "Texas",
    "Tillman",
    "Tulsa",
    "Wagoner",
    "Washington",
    "Washita",
    "Woods",
    "Woodward",
]

# 50K+ cities: (city, county)
CITIES = [("Oklahoma City", "Oklahoma"),
    ("Tulsa", "Tulsa"),
    ("Norman", "Cleveland"),
    ("Broken Arrow", "Tulsa"),
    ("Edmond", "Oklahoma"),
    ("Lawton", "Comanche"),
    ("Moore", "Cleveland"),
    ("Midwest City", "Oklahoma"),
    ("Enid", "Garfield"),
    ("Stillwater", "Payne"),
]

CITY_POP = {
    "Oklahoma City": 712919, "Tulsa": 415154, "Norman": 131010, "Broken Arrow": 122756, "Edmond": 99040, "Lawton": 90027, "Moore": 63845, "Midwest City": 58505, "Enid": 50519, "Stillwater": 50138,
}

def slugify(s):
    return s.lower().replace(' ', '-').replace("'", "").replace('.', '')

def llm(text_prompt):
    if not LLM_API_KEY:
        return None
    payload = {"model": LLM_MODEL, "messages": [
        {"role": "system", "content": "You are a local writer crafting natural website copy about Oklahoma locations. No markdown, no em dashes, no asterisks. Plain paragraphs only. Sound like a person."},
        {"role": "user", "content": text_prompt},
    ], "temperature": 0.8, "max_tokens": 400}
    req = urllib.request.Request(LLM_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.loads(r.read())
                t = body["choices"][0]["message"]["content"]
                t = t.replace("\u2014", " -- ").replace("\u2013", "-")
                t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
                return t.strip()
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2)
    return None

def content_paragraphs(name, kind):
    if kind == "city":
        prompt = f"Write 2 short paragraphs about {name}, Oklahoma. P1: what it's known for. P2: what renters should know about the local market and housing help. Return 2 paragraphs separated by a blank line."
    elif kind == "county":
        prompt = f"Write 2 short paragraphs about {name} County, Oklahoma. P1: what makes it distinct. P2: what a renter should know about rental housing help and the court system. Return 2 paragraphs separated by a blank line."
    else:
        prompt = f"Write 3 short paragraphs about Oklahoma for a tenant-eviction self-help website. P1: notable fact. P2: rental housing context. P3: practical eviction-process tip. Return 3 paragraphs separated by blank lines."
    t = llm(prompt)
    if not t:
        return [f"{name} is a community in Oklahoma."] * (3 if kind == "state" else 2)
    ps = [p.strip() for p in t.split("\n\n") if p.strip()]
    return ps[: (3 if kind == "state" else 2)]

def state_select_html():
    states = ["AR","CO","CT","GA","IL","KY","LA","MI","MN","MO","NM","OK","OR","RI","SC","TN","TX","VA"]
    names = {"AR":"Arkansas","CO":"Colorado","CT":"Connecticut","GA":"Georgia","IL":"Illinois","LA":"Louisiana","MI":"Michigan","MN":"Minnesota","KY":"Oklahoma","MO":"Missouri","OK":"Oklahoma","NM":"New Mexico","OR":"Oregon","RI":"Rhode Island","SC":"South Carolina","TN":"Tennessee","TX":"Texas","VA":"Virginia"}
    out = ""
    for s in states:
        sel = ' selected' if s == "OK" else ''
        out += f'<option value="{s}"{sel}>{names[s]}</option>'
    return out

def build_head(title, desc, canonical, breadcrumb, body_attrs):
    return f'''<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}"><meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="{canonical}"><link rel="icon" href="/assets/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><link rel="stylesheet" href="/assets/styles.css">
<meta property="og:type" content="website"><meta property="og:image" content="https://evictions.help/assets/evictions-help-logo.png"><meta property="og:site_name" content="evictions.help"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary_large_image">
</head><body {body_attrs}>
<header class="site-header"><div class="container nav"><a class="brand" href="/" aria-label="evictions.help home"><img src="/assets/evictions-help-logo.png" alt="evictions.help"></a><nav class="nav-links" aria-label="Primary"><a href="/#included">What's included</a><a href="/#how-it-works">How it works</a><a href="/#states">States</a><a href="/#faq">FAQ</a><a href="/contact">Contact</a><a class="nav-cta" href="#eligibility">Check eligibility</a></nav><button class="mobile-menu" aria-label="Open menu">☰</button></div></header>
<nav class="breadcrumb container" aria-label="Breadcrumb"><ol>{breadcrumb}</ol></nav>'''

def build_hero(eyebrow, h1, lede, form_attrs):
    state_sel = state_select_html()
    return f'''<section class="hero"><div class="container hero-grid"><div class="hero-copy"><span class="eyebrow">{eyebrow}</span><h1>{h1}</h1><p class="lede">{lede}</p><div class="price-row"><span class="price">$399</span><span class="price-note">flat fee · digital packet</span></div><div class="trust-row"><span class="trust-chip"><i class="check">✓</i> 8-question screening</span><span class="trust-chip"><i class="check">✓</i> Guided AI intake</span><span class="trust-chip"><i class="check">✓</i> Downloadable packet</span></div><p class="hero-note">Self-help document preparation only. evictions.help is not a law firm and does not provide legal advice or representation. No court outcome is guaranteed.</p></div><form id="eligibility" class="screen-card eligibility-form" {form_attrs}><div class="screen-head"><h2>See whether you can continue</h2><p>Answer eight questions. No payment is collected during eligibility.</p></div><div class="progress" aria-hidden="true"><span></span></div><div class="screen-body">
<div class="screen-step active"><div class="question-count">Question 1 of 8</div><div class="question">Where is the rental property located?</div><select name="state" required aria-label="State"><option value="">Select a state</option>{state_sel}</select></div><div class="screen-step"><div class="question-count">Question 2 of 8</div><div class="question">What county is the eviction case in?</div><select name="county" required aria-label="County"><option value="">Select a county</option></select></div>
<div class="screen-step"><div class="question-count">Question 3 of 8</div><div class="question">Are you the tenant named in the eviction matter?</div><div class="choice-grid"><div class="choice"><input id="tenant-yes" type="radio" name="tenant" value="yes"><label for="tenant-yes">Yes</label></div><div class="choice"><input id="tenant-no" type="radio" name="tenant" value="no"><label for="tenant-no">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 4 of 8</div><div class="question">Have you been served with eviction court papers?</div><div class="choice-grid"><div class="choice"><input id="served-yes" type="radio" name="served" value="yes"><label for="served-yes">Yes</label></div><div class="choice"><input id="served-no" type="radio" name="served" value="no"><label for="served-no">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 5 of 8</div><div class="question">Is this a residential rental property?</div><div class="choice-grid"><div class="choice"><input id="residential-yes" type="radio" name="residential" value="yes"><label for="residential-yes">Yes</label></div><div class="choice"><input id="residential-no" type="radio" name="residential" value="no"><label for="residential-no">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 6 of 8</div><div class="question">Is the home Section 8, voucher-assisted, or public housing?</div><div class="choice-grid"><div class="choice"><input id="subsidized-yes" type="radio" name="subsidized" value="yes"><label for="subsidized-yes">Yes</label></div><div class="choice"><input id="subsidized-no" type="radio" name="subsidized" value="no"><label for="subsidized-no">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 7 of 8</div><div class="question">Are you or another tenant on active military duty?</div><div class="choice-grid"><div class="choice"><input id="military-yes" type="radio" name="military" value="yes"><label for="military-yes">Yes</label></div><div class="choice"><input id="military-no" type="radio" name="military" value="no"><label for="military-no">No</label></div></div></div><div class="screen-step"><div class="question-count">Question 8 of 8</div><div class="question">Have you filed bankruptcy or is a bankruptcy case active?</div><div class="choice-grid"><div class="choice"><input id="bankruptcy-yes" type="radio" name="bankruptcy" value="yes"><label for="bankruptcy-yes">Yes</label></div><div class="choice"><input id="bankruptcy-no" type="radio" name="bankruptcy" value="no"><label for="bankruptcy-no">No</label></div></div></div>
<div class="screen-step"><div data-result class="result-box result-ok"></div><div data-qualified><div class="form-grid"><div class="field full"><label>Street address</label><input name="street" type="text" autocomplete="street-address" required></div><div class="field"><label>City</label><input name="city" type="text" autocomplete="address-level2" required></div><div class="field"><label>County</label><input name="county" type="text" autocomplete="address-level1" required></div><div class="field"><label>ZIP code</label><input name="zip" type="text" inputmode="numeric" autocomplete="postal-code" pattern="[0-9]{{5}}" required></div><div class="field"><label>Email</label><input name="email" type="email" autocomplete="email" required></div><div class="field full"><label>Phone</label><input name="phone" type="tel" autocomplete="tel" required></div></div><button class="btn btn-primary" style="max-width:100%;margin-top:16px" type="submit">Continue to secure checkout — $399</button><p class="micro">By continuing, you acknowledge that this is a self-help document preparation service—not a law firm or legal representation.</p></div></div>
<div class="screen-actions"><button data-back class="btn btn-secondary" type="button" hidden>Back</button></div></div></form></div></section>'''

def build_footer():
    return f'''<div class="sticky-mobile"><span>Start with 8 questions<br><small>No payment yet</small></span><a class="btn btn-primary" href="#eligibility">Check eligibility</a></div>
<footer class="footer"><div class="container"><div class="footer-grid"><div><img src="/assets/evictions-help-logo.png" alt="evictions.help"><p>AI-assisted self-help document preparation for residential tenants facing eviction. Flat fee: $399.</p></div><div><h3>Program</h3><div class="footer-links"><a href="/#included">Packet contents</a><a href="/#how-it-works">How it works</a><a href="/#states">Supported states</a><a href="/#faq">Frequently asked questions</a></div></div><div><h3>Important</h3><div class="footer-links"><a href="/terms/">Terms of use</a><a href="/privacy/">Privacy</a><a href="/disclaimer/">Legal disclaimer</a><a href="mailto:support@evictions.help">support@evictions.help</a></div></div></div><div class="footer-bottom">© 2026 evictions.help. Self-help document preparation. Not a law firm. Not legal advice.</div></div></footer>
<script src="/assets/site.js" defer></script></body></html>'''

def build_county_page(name, cities_in_county):
    slug = slugify(name) + "-county"
    paras = content_paragraphs(name, "county")
    content = "\n".join(f"<p>{p}</p>" for p in paras)
    cities_html = ""
    for cname, ccounty in CITIES:
        if ccounty == name:
            cs = slugify(cname)
            pop = CITY_POP[cname]
            cities_html += f'<a class="location-link" href="/{STATE_SLUG}/{slug}/{cs}/">{cname}<small>{pop:,} residents</small></a>\n'
    if not cities_html:
        cities_html = f'<a class="location-link" href="/{STATE_SLUG}/">All Oklahoma locations<small>State directory</small></a>\n'

    head = build_head(
        f"Eviction Help in {name} County, Oklahoma | evictions.help",
        f"Check eligibility for eviction self-help document preparation in {name} County, Oklahoma.",
        f"https://evictions.help/{STATE_SLUG}/{slug}/",
        f'<li><a href="/">Home</a></li><li><a href="/{STATE_SLUG}/">Oklahoma</a></li><li>{name} County</li>',
        f'data-state="OK" data-county="{name} County" data-city=""'
    )
    hero = build_hero(
        f"{name} County eviction document help",
        f"Eviction paperwork help for tenants in {name} County",
        f"Start with eight questions. Your Oklahoma and {name} County location is carried into the guided intake and $399 document packet workflow.",
        f'data-state="OK" data-county="{name} County" data-city=""'
    )
    middle = f'''<section class="section"><div class="container">
{content}
</div></section>
<section class="section"><div class="container split"><div><span class="eyebrow">Local case organization</span><h2>Prepare with the correct local context</h2><p class="lede">{name} County is a community in Oklahoma. The eligibility form carries {name} County into checkout and intake.</p></div><div class="feature-list"><div class="feature"><i class="check">1</i><div><strong>Keep the court papers together</strong><span>Use the exact party names, case number, court, and hearing information shown on the filed documents.</span></div></div><div class="feature"><i class="check">2</i><div><strong>Document payments and notices</strong><span>Organize receipts, ledgers, repair requests, messages, photographs, and assistance applications.</span></div></div><div class="feature"><i class="check">3</i><div><strong>Verify local filing requirements</strong><span>Confirm deadlines, filing methods, and service rules with the court or qualified legal help.</span></div></div></div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Communities in this directory</span><h2>City pages connected to {name} County</h2></div><div class="location-grid">{cities_html}</div></div></section>
<section class="section"><div class="container"><div class="section-intro"><span class="eyebrow">Statewide starting points</span><h2>Resources that may serve {name} County</h2><p>These statewide or regional portals are starting points, not guarantees of funding or representation.</p></div><div class="resource-list"><article class="resource"><span class="type">Referral</span><h3><a href="https://www.211.org/" rel="nofollow noopener" target="_blank">2-1-1 Oklahoma ↗</a></h3><p>Rent, utilities, shelter, food and crisis referrals. Dial 211.</p></article><article class="resource"><span class="type">Tenant Help</span><h3><a href="https://motenanthelp.org/" rel="nofollow noopener" target="_blank">Oklahoma Tenant Help ↗</a></h3><p>Free tenant resource and eviction document engine.</p></article><article class="resource"><span class="type">Legal Aid</span><h3><a href="https://www.lsmo.org/" rel="nofollow noopener" target="_blank">Legal Services of Oklahoma ↗</a></h3><p>Statewide legal-aid network for low-income tenants.</p></article></div></div></section>
<section class="section"><div class="container"><div class="callout"><h2>Start a packet for {name} County</h2><p>Your state and county are prefilled above. Check eligibility before proceeding to the $399 checkout.</p><a class="btn btn-secondary" href="#eligibility">Check eligibility</a></div></div></section>'''
    return head + hero + middle + build_footer()

def build_city_page(cname, ccounty):
    cslug = slugify(cname)
    county_slug = slugify(ccounty) + "-county"
    paras = content_paragraphs(cname, "city")
    content = "\n".join(f"<p>{p}</p>" for p in paras)
    pop = CITY_POP.get(cname, 50000)

    head = build_head(
        f"Eviction Help in {cname}, Oklahoma | evictions.help",
        f"Check eligibility for eviction self-help document preparation in {cname}, {ccounty} County.",
        f"https://evictions.help/{STATE_SLUG}/{county_slug}/{cslug}/",
        f'<li><a href="/">Home</a></li><li><a href="/{STATE_SLUG}/">Oklahoma</a></li><li><a href="/{STATE_SLUG}/{county_slug}/">{ccounty} County</a></li><li>{cname}</li>',
        f'data-state="OK" data-county="{ccounty} County" data-city="{cname}"'
    )
    hero = build_hero(
        f"{cname} eviction document help",
        f"Prepare eviction paperwork from {cname} with a guided intake",
        "Your city, county, and state are prefilled. Qualified tenants can continue to a $399 self-help document packet built from their own case information.",
        f'data-state="OK" data-county="{ccounty} County" data-city="{cname}"'
    )
    middle = f'''<section class="section"><div class="container">
{content}
</div></section>
<section class="section"><div class="container split"><div><span class="eyebrow">{cname} self-help preparation</span><h2>Your city, county, and state stay connected</h2><p class="lede">{cname} is listed with {ccounty} County in the site's local navigation and had an estimated 2024 population of {pop:,}.</p><p>The page does not claim that evictions are handled by a city-specific court. It carries the city and county into the eligibility and intake flow.</p></div><div class="feature-list"><div class="feature"><i class="check">✓</i><div><strong>Location prefilled</strong><span>{cname}, {ccounty} County, Oklahoma is preserved in the intake.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Case-specific questions</strong><span>The intake asks for the landlord, court, case number, dates, amount claimed, payments, defenses, and preferences.</span></div></div><div class="feature"><i class="check">✓</i><div><strong>Conditional documents</strong><span>Letters and motions are included only when the tenant's answers support them.</span></div></div></div></div></section>
<section class="section"><div class="container"><div class="section-intro"><span class="eyebrow">Resource starting points</span><h2>Housing and legal-information portals for Oklahoma</h2></div><div class="resource-list"><article class="resource"><span class="type">Referral</span><h3><a href="https://www.211.org/" rel="nofollow noopener" target="_blank">2-1-1 Oklahoma ↗</a></h3><p>Rent, utilities, shelter, food and crisis referrals.</p></article><article class="resource"><span class="type">Tenant Help</span><h3><a href="https://motenanthelp.org/" rel="nofollow noopener" target="_blank">Oklahoma Tenant Help ↗</a></h3><p>Free tenant resource and eviction document engine.</p></article><article class="resource"><span class="type">Legal Aid</span><h3><a href="https://www.lsmo.org/" rel="nofollow noopener" target="_blank">Legal Services of Oklahoma ↗</a></h3><p>Statewide legal-aid network.</p></article></div></div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Continue exploring</span><h2>Related local pages</h2></div><div class="location-grid"><a class="location-link" href="/{STATE_SLUG}/">All Oklahoma locations<small>State directory</small></a><a class="location-link" href="/{STATE_SLUG}/{county_slug}/">{ccounty} County<small>County directory</small></a></div></div></section>
<section class="section"><div class="container"><div class="callout"><h2>Check eligibility from {cname}</h2><p>The screening above is free to complete. Payment comes only after the program indicates that the tenant can continue.</p><a class="btn btn-secondary" href="#eligibility">Check Eligibility</a></div></div></section>'''
    return head + hero + middle + build_footer()

def main():
    state_dir = os.path.join(SEO_DIR, STATE_SLUG)
    try:
        os.makedirs(state_dir, exist_ok=True)
    except OSError:
        pass

    # 1. State page
    print("Generating Oklahoma state page...", flush=True)
    paras = content_paragraphs("Oklahoma", "state")
    content = "\n".join(f"<p>{p}</p>" for p in paras)
    county_links = "".join(f'<a class="location-link" href="/{STATE_SLUG}/{slugify(c)}-county/">{c} County<small>County directory</small></a>\n' for c in sorted(COUNTIES)[:30])
    state_html = build_head(
        "Eviction Help in Oklahoma | evictions.help",
        "Check eligibility for eviction self-help document preparation across Oklahoma counties and cities.",
        f"https://evictions.help/{STATE_SLUG}/",
        '<li><a href="/">Home</a></li><li>Oklahoma</li>',
        'data-state="OK" data-county="" data-city=""'
    ) + build_hero(
        "Oklahoma eviction document help",
        "Eviction paperwork help for tenants in Oklahoma",
        "Start with eight questions. Your Oklahoma location is carried into the guided intake and $399 document packet workflow.",
        'data-state="OK" data-county="" data-city=""'
    ) + f'''<section class="section"><div class="container">{content}</div></section>
<section class="section section-soft"><div class="container"><div class="section-intro"><span class="eyebrow">Counties</span><h2>Oklahoma county directories</h2></div><div class="location-grid">{county_links}</div></div></section>
<section class="section"><div class="container"><div class="callout"><h2>Start a packet for Oklahoma</h2><p>Check eligibility before proceeding to the $399 checkout.</p><a class="btn btn-secondary" href="#eligibility">Check eligibility</a></div></div></section>''' + build_footer()
    try:
        with open(os.path.join(state_dir, "index.html"), "w") as f:
            f.write(state_html)
    except OSError as e:
        print(f"  ERROR writing state page: {e}")
    print("  ✓ state page", flush=True)

    # 2. County pages
    for i, county in enumerate(COUNTIES):
        cslug = slugify(county) + "-county"
        cdir = os.path.join(state_dir, cslug)
        try:
            os.makedirs(cdir, exist_ok=True)
        except OSError:
            pass
        html = build_county_page(county, [c for c, _ in CITIES if _ == county])
        try:
            with open(os.path.join(cdir, "index.html"), "w") as f:
                f.write(html)
        except OSError as e:
            print(f"  ERROR writing {county}: {e}")
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{len(COUNTIES)} county pages", flush=True)
        time.sleep(1.0)

    # 3. City pages
    for cname, ccounty in CITIES:
        county_slug = slugify(ccounty) + "-county"
        cslug = slugify(cname)
        cdir = os.path.join(state_dir, county_slug, cslug)
        try:
            os.makedirs(cdir, exist_ok=True)
        except OSError:
            pass
        html = build_city_page(cname, ccounty)
        try:
            with open(os.path.join(cdir, "index.html"), "w") as f:
                f.write(html)
        except OSError as e:
            print(f"  ERROR writing {cname}: {e}")
        print(f"  city: {cname}", flush=True)
        time.sleep(1.0)

    print(f"\nDone. Generated: 1 state + {len(COUNTIES)} counties + {len(CITIES)} cities", flush=True)

if __name__ == "__main__":
    main()
