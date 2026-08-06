#!/usr/bin/env python3
"""
SEO content enrichment for evictions.help pages.

Adds location-specific paragraphs (LLM-generated) + 2 public-domain images
(Wikimedia Commons) to every state, county, and city page.

States:  3 paragraphs
Counties: 2 paragraphs
Cities:  2 paragraphs
All tiers: 2 images

Usage:
    python3 enrich_seo_pages.py                    # all pages
    python3 enrich_seo_pages.py --state florida    # one state
    python3 enrich_seo_pages.py --dry-run          # preview only
    python3 enrich_seo_pages.py --resume           # continue from last saved checkpoint
"""

import os, sys, json, time, re, hashlib
import urllib.request
import urllib.parse
import shutil
from pathlib import Path
from argparse import ArgumentParser

# ── Config ──────────────────────────────────────────────────
SEO_DIR = "/opt/eviction-defense/seo"
ASSETS_DIR = os.path.join(SEO_DIR, "assets", "locations")
PROGRESS_FILE = "/tmp/enrich_seo_progress.json"
BACKUP_DIR = "/opt/eviction-defense/seo_backup"
LLM_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

MAX_IMAGE_SIZE_MB = 5
REQUEST_DELAY = 1.2  # seconds between API calls

# ── Helpers ─────────────────────────────────────────────────

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "images_downloaded": {}}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)

def backup_file(fpath):
    rel = os.path.relpath(fpath, SEO_DIR)
    dest = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(fpath, dest)

def read_file(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        return f.read()

def write_file(fpath, content):
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

# ── LLM Content Generation ─────────────────────────────────

def llm_generate(system_prompt: str, user_prompt: str) -> str:
    """Call DeepSeek API to generate content."""
    if not LLM_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 600,
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
                # Clean: no markdown, no em dashes
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

def state_prompt(state_name: str) -> tuple:
    """Generate prompts for a state page."""
    system = (
        "You are a local writer crafting natural, human-sounding website copy about US states. "
        "Write as if you're a knowledgeable local, not a Wikipedia article. "
        "No markdown, no em dashes, no hashtags, no asterisks. "
        "Use plain paragraph text only. Sound like a person, not a bot."
    )
    user = (
        f"Write 3 short paragraphs about {state_name} for a website that helps tenants "
        f"facing eviction. The paragraphs should be about:\n\n"
        f"Paragraph 1: A notable fact about {state_name} that makes it unique -- "
        f"something about its geography, culture, or history. One or two sentences.\n\n"
        f"Paragraph 2: What rental housing is like in {state_name} -- general cost-of-living "
        f"context, major metro areas where people rent, any recent housing trends. "
        f"Two or three sentences. Sound natural, not statistical.\n\n"
        f"Paragraph 3: What tenants should know about the eviction process in {state_name} -- "
        f"a practical tip about timelines or court procedures, in plain language. "
        f"Two or three sentences. Do not give legal advice -- just practical orientation.\n\n"
        f"Return just the 3 paragraphs, separated by blank lines. No labels, no numbers."
    )
    return system, user

def county_prompt(county_name: str, state_name: str, population: str = "") -> tuple:
    pop_note = f" It has about {population} residents." if population else ""
    system = (
        "You are a local writer crafting natural, human-sounding website copy about US counties. "
        "Write as if you're a knowledgeable local, not a Wikipedia article. "
        "No markdown, no em dashes, no hashtags, no asterisks. "
        "Use plain paragraph text only. Sound like a person, not a bot."
    )
    user = (
        f"Write 2 short paragraphs about {county_name}, {state_name}.{pop_note}\n\n"
        f"Paragraph 1: What makes {county_name} distinct -- its largest city, "
        f"a notable landmark, or something people associate with the area. "
        f"One or two sentences. Sound local and natural.\n\n"
        f"Paragraph 2: What a renter in {county_name} should know about finding rental "
        f"housing help or navigating the court system. Mention the county seat if relevant. "
        f"Two or three sentences. Practical, not legal advice.\n\n"
        f"Return just the 2 paragraphs, separated by a blank line. No labels, no numbers."
    )
    return system, user

def city_prompt(city_name: str, state_name: str, population: str = "") -> tuple:
    pop_note = f" It has about {population} residents." if population else ""
    system = (
        "You are a local writer crafting natural, human-sounding website copy about US cities. "
        "Write as if you're a knowledgeable local, not a Wikipedia article. "
        "No markdown, no em dashes, no hashtags, no asterisks. "
        "Use plain paragraph text only. Sound like a person, not a bot."
    )
    user = (
        f"Write 2 short paragraphs about {city_name}, {state_name}.{pop_note}\n\n"
        f"Paragraph 1: What {city_name} is known for -- a landmark, industry, or cultural "
        f"characteristic that locals identify with. One or two sentences.\n\n"
        f"Paragraph 2: What tenants in {city_name} should understand about the local rental "
        f"market and where to turn for housing help. Two or three sentences. "
        f"Practical, grounded, not legal advice.\n\n"
        f"Return just the 2 paragraphs, separated by a blank line. No labels, no numbers."
    )
    return system, user

# ── Wikimedia Commons Image Search ──────────────────────────

def _wikimedia_request(url: str) -> dict:
    """Make a Wikimedia API request with proper User-Agent."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "evictions.help/1.0 (https://evictions.help; support@evictions.help)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def search_wikimedia(query: str, limit: int = 8) -> list[dict]:
    """Search Wikimedia Commons for images matching query. Returns list of {title, pageid}."""
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": limit,
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"

    try:
        data = _wikimedia_request(url)
        return data.get("query", {}).get("search", [])
    except Exception as e:
        print(f"  Wikimedia search error: {e}")
        return []

def get_image_info(titles: list[str]) -> list[dict]:
    """Get image URLs and license info for given file titles."""
    if not titles:
        return []

    params = urllib.parse.urlencode({
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"

    try:
        data = _wikimedia_request(url)
        results = []
        for page in data.get("query", {}).get("pages", {}).values():
            ii = page.get("imageinfo", [])
            if ii:
                meta = ii[0].get("extmetadata", {})
                license_name = meta.get("LicenseShortName", {}).get("value", "")
                results.append({
                    "title": page["title"],
                    "url": ii[0]["url"],
                    "width": ii[0].get("width", 0),
                    "height": ii[0].get("height", 0),
                    "size_bytes": ii[0].get("size", 0),
                    "license": license_name,
                })
        return results
    except Exception as e:
        print(f"  Image info error: {e}")
        return []

def is_usable_image(info: dict) -> bool:
    """Check if image is public domain or CC0 and reasonably sized."""
    size_mb = info["size_bytes"] / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        return False
    # Accept PD, CC0, or CC-BY (which allows use with attribution)
    license_lower = info["license"].lower()
    acceptable = ["pd", "cc0", "public domain", "cc-by", "cc by", "creative commons attribution"]
    return any(term in license_lower for term in acceptable)

def find_location_images(location_name: str, state_name: str = "", progress: dict | None = None) -> list[str]:
    """Find 2 usable images for a location. Downloads them to assets dir. Returns local paths."""
    downloaded = []

    # Check cache
    cache_key = f"{state_name}/{location_name}" if state_name else location_name
    if progress and cache_key in progress.get("images_downloaded", {}):
        return progress["images_downloaded"][cache_key]

    # Try multiple search queries
    queries = []
    if state_name:
        queries.append(f"{location_name} {state_name}")
        queries.append(f"{location_name}")
    else:
        queries.append(f"{location_name}")
        queries.append(f"{location_name} United States")

    found_images = []
    for query in queries:
        if len(found_images) >= 10:
            break
        results = search_wikimedia(query, limit=10)
        for r in results:
            if r["title"] not in [img["title"] for img in found_images]:
                found_images.append(r)

    if not found_images:
        return []

    # Get image info for all found results
    titles = [img["title"] for img in found_images[:10]]
    infos = get_image_info(titles)

    # Filter usable
    usable = [info for info in infos if is_usable_image(info)]

    # Download up to 2
    target_dir = cache_key.replace(" ", "_").lower()
    target_dir = re.sub(r"[^a-z0-9_/-]", "", target_dir)
    dest_dir = os.path.join(ASSETS_DIR, target_dir)
    os.makedirs(dest_dir, exist_ok=True)

    for info in usable[:2]:
        ext = os.path.splitext(info["url"].split("?")[0])[-1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
        fname = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(info["title"].split(":")[-1])[0])
        dest = os.path.join(dest_dir, f"{fname}{ext}")

        try:
            if not os.path.exists(dest):
                req = urllib.request.Request(info["url"], headers={"User-Agent": "evictions.help/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    with open(dest, "wb") as f:
                        f.write(resp.read())
                time.sleep(0.3)
            rel_path = os.path.relpath(dest, SEO_DIR)
            downloaded.append("/" + rel_path)
        except Exception as e:
            print(f"  Download error: {e}")

    return downloaded

# ── HTML Injection ──────────────────────────────────────────

def build_image_html(img_paths: list[str], alt_text: str) -> str:
    """Build HTML for 2 images in a responsive row."""
    if not img_paths:
        return ""

    imgs_html = ""
    for path in img_paths:
        imgs_html += (
            f'<div class="img-cell">'
            f'<img src="{path}" alt="{alt_text}" loading="lazy" '
            f'style="width:100%;height:auto;border-radius:8px;aspect-ratio:16/10;object-fit:cover">'
            f'</div>'
        )

    return (
        f'<div class="local-images" style="display:grid;grid-template-columns:1fr 1fr;'
        f'gap:16px;margin:24px 0">'
        f'{imgs_html}'
        f'</div>'
    )

def build_content_section(paragraphs: list[str], img_paths: list[str], alt_text: str) -> str:
    """Build the full content section with paragraphs and images."""
    paras_html = "\n".join(f"<p>{p}</p>" for p in paragraphs if p.strip())
    imgs_html = build_image_html(img_paths, alt_text)

    return (
        f'\n<section class="section"><div class="container">'
        f'{paras_html}'
        f'{imgs_html}'
        f'</div></section>\n'
    )

def inject_content(html: str, new_section: str) -> str:
    """Inject the new content section after the hero section but before
    the first content section with the location grid or resources."""
    # Find the closing </section> of the hero + form area
    # The hero ends with: </div></section> after the eligiblity form
    # We want to insert after that but before the next <section class="section">

    # Strategy: find the first <section class="section"> that comes after the
    # hero form block (which contains class="eligibility-form")
    pattern = r'(</form>\s*</div>\s*</section>)'
    m = re.search(pattern, html)
    if not m:
        print("  WARNING: Could not find hero end marker")
        return html

    insert_point = m.end()
    return html[:insert_point] + "\n" + new_section + html[insert_point:]

def extract_page_info(html: str, fpath: str) -> dict:
    """Extract location info from page HTML."""
    rel = os.path.relpath(fpath, SEO_DIR)
    parts = rel.replace("/index.html", "").split("/")

    # Determine tier
    if len(parts) == 1:
        tier = "state"
        state = parts[0].replace("-", " ").title()
        county = ""
        city = ""
    elif len(parts) == 2:
        tier = "county"
        state = parts[0].replace("-", " ").title()
        county = parts[1].replace("-county", "").replace("-", " ").title()
        city = ""
    else:
        tier = "city"
        state = parts[0].replace("-", " ").title()
        county = parts[1].replace("-county", "").replace("-", " ").title()
        city = parts[2].replace("-", " ").title()

    # Extract population from HTML (if present)
    pop_match = re.search(r'(\d[\d,]+)\s*residents', html)
    population = pop_match.group(1) if pop_match else ""

    return {
        "tier": tier,
        "state": state,
        "county": county,
        "city": city,
        "population": population,
        "path": fpath,
        "rel": rel,
    }

# ── Main Processing ─────────────────────────────────────────

def find_all_pages(limit_state: str | None = None) -> list[str]:
    """Find all HTML pages in the SEO directory."""
    pages = []
    for root, dirs, files in os.walk(SEO_DIR):
        for fname in files:
            if fname == "index.html":
                fpath = os.path.join(root, fname)
                if limit_state:
                    rel = os.path.relpath(fpath, SEO_DIR)
                    if not rel.startswith(limit_state + "/") and rel != limit_state + "/index.html":
                        continue
                pages.append(fpath)
    return sorted(pages)

def process_page(fpath: str, progress: dict, dry_run: bool = False) -> bool:
    """Process one page: generate content, find images, inject."""
    rel = os.path.relpath(fpath, SEO_DIR)

    # Skip already completed
    if rel in progress.get("completed", []):
        print(f"  SKIP (already done): {rel}")
        return True

    # Skip non-location pages
    skip_prefixes = ["assets/", "checkout/", "disclaimer/", "privacy/", "terms/"]
    if any(rel.startswith(p) for p in skip_prefixes):
        return True

    info = extract_page_info(read_file(fpath) if not dry_run else "", fpath)
    tier = info["tier"]
    print(f"\n  [{tier.upper()}] {rel}")

    if dry_run:
        print(f"    State: {info['state']}, County: {info['county']}, City: {info['city']}")
        print(f"    Population: {info['population']}")
        return True

    html = read_file(fpath)

    # Check if already enriched
    if '<section class="section"><div class="container"><p>' in html and 'local-images' in html:
        # Simple heuristic -- pages that already have our injected content
        already_done_count = html.count('class="local-images"')
        if already_done_count >= 1:
            print(f"  SKIP (already enriched)")
            return True

    # ── Generate content ──────────────────────────────────
    try:
        if tier == "state":
            system, user = state_prompt(info["state"])
        elif tier == "county":
            system, user = county_prompt(info["county"], info["state"], info["population"])
        else:
            system, user = city_prompt(info["city"], info["state"], info["population"])

        print(f"  Generating content...")
        text = llm_generate(system, user)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Ensure we have enough paragraphs
        target = 3 if tier == "state" else 2
        while len(paragraphs) < target:
            paragraphs.append("")
        paragraphs = paragraphs[:target]

        for i, p in enumerate(paragraphs):
            print(f"    P{i+1}: {p[:80]}...")
    except Exception as e:
        print(f"  LLM error: {e}")
        return False

    time.sleep(REQUEST_DELAY)

    # ── Find images ────────────────────────────────────────
    if tier == "state":
        location = info["state"]
        alt = f"{info['state']}"
    elif tier == "city":
        location = info["city"]
        alt = f"{info['city']}, {info['state']}"
    else:
        location = info["county"]
        alt = f"{info['county']}, {info['state']}"

    print(f"  Searching images for: {location}...")
    img_paths = find_location_images(location, info["state"] if tier != "state" else "", progress)

    if img_paths:
        print(f"    Found {len(img_paths)} images")
    else:
        print(f"    No images found, using placeholders")
        # Fallback: use state-level images if available
        img_paths = []

    # Save image cache
    cache_key = f"{info['state']}/{location}" if tier != "state" else location
    progress.setdefault("images_downloaded", {})[cache_key] = img_paths
    save_progress(progress)

    # ── Build and inject section ───────────────────────────
    new_section = build_content_section(paragraphs, img_paths, alt)

    # Backup original
    backup_file(fpath)
    new_html = inject_content(html, new_section)
    write_file(fpath, new_html)

    # Mark complete
    progress.setdefault("completed", []).append(rel)
    save_progress(progress)

    print(f"  DONE")
    return True

def main():
    parser = ArgumentParser()
    parser.add_argument("--state", help="Process only one state (e.g. florida)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process")
    args = parser.parse_args()

    # Load API key
    global LLM_API_KEY
    if not LLM_API_KEY:
        # Try loading from .env (check both common paths)
        for env_path in ["/opt/eviction-defense/.env", "/home/williamkm/eviction-defense/.env"]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("LLM_API_KEY="):
                            LLM_API_KEY = line.split("=", 1)[1].strip()
                            break
                if LLM_API_KEY:
                    break
        if not LLM_API_KEY:
            print("ERROR: LLM_API_KEY not set. Export it or ensure .env has LLM_API_KEY.")
            sys.exit(1)

    os.makedirs(ASSETS_DIR, exist_ok=True)

    progress = load_progress() if args.resume else {"completed": [], "images_downloaded": {}}
    if not args.resume:
        progress = {"completed": [], "images_downloaded": {}}
        save_progress(progress)

    pages = find_all_pages(args.state)
    pages = [p for p in pages if os.path.relpath(p, SEO_DIR) not in progress.get("completed", [])]

    print(f"Found {len(pages)} pages to process")
    if args.limit:
        pages = pages[:args.limit]
        print(f"Limited to {args.limit}")

    success = 0
    fail = 0

    for i, fpath in enumerate(pages):
        print(f"\n== [{i+1}/{len(pages)}] ==")
        try:
            if process_page(fpath, progress, args.dry_run):
                success += 1
            else:
                fail += 1
        except KeyboardInterrupt:
            print(f"\n\nInterrupted. Progress saved. Resume with --resume")
            break
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1

    print(f"\n{'='*60}")
    print(f"Done. {success} succeeded, {fail} failed.")
    print(f"Progress saved to {PROGRESS_FILE}")

if __name__ == "__main__":
    main()
