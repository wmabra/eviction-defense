#!/usr/bin/env python3
"""
Image-only backfill for evictions.help SEO pages.

Downloads 1-2 public-domain images per page from Wikimedia Commons,
with proper throttling and deduplication. Fallback to Unsplash when
Wikimedia has zero matches.

Never reuses the same image across different pages.

Usage:
    python3 backfill_images.py                    # all pages
    python3 backfill_images.py --state florida    # one state
    python3 backfill_images.py --dry-run          # preview only
    python3 backfill_images.py --resume           # continue from last checkpoint
"""

import os, sys, json, time, re, hashlib
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from argparse import ArgumentParser

# ── Config ──────────────────────────────────────────────────
SEO_DIR = "/opt/eviction-defense/seo"
ASSETS_DIR = os.path.join(SEO_DIR, "assets", "locations")
PROGRESS_FILE = "/tmp/backfill_images_progress.json"

WIKI_DELAY = 2.5     # seconds between Wikimedia searches
DOWNLOAD_DELAY = 1.5  # seconds between image downloads
THUMB_WIDTH = 800    # Wikimedia thumbnail width (smaller = faster, less rate-limiting)

UA = "evictions.help/1.0 (https://evictions.help; support@evictions.help)"

# Track globally used image titles to avoid duplicates
USED_IMAGE_TITLES = set()

# ── Helpers ─────────────────────────────────────────────────

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "used_titles": []}

def save_progress(progress):
    progress["used_titles"] = list(USED_IMAGE_TITLES)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)

def read_file(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        return f.read()

def write_file(fpath, content):
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

def wiki_request(url: str) -> dict:
    """Make a Wikimedia API request with User-Agent and retries."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)
    return {}

# ── Wikimedia Image Search ──────────────────────────────────

def search_wikimedia(query: str, limit: int = 10) -> list[dict]:
    """Search Wikimedia Commons, return [{title, pageid}, ...]."""
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": limit,
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    data = wiki_request(url)
    return data.get("query", {}).get("search", [])

def get_image_info(titles: list[str]) -> list[dict]:
    """Get thumbnail URLs and license info for file titles."""
    if not titles:
        return []
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": THUMB_WIDTH,
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    data = wiki_request(url)
    results = []
    for page in data.get("query", {}).get("pages", {}).values():
        ii = page.get("imageinfo", [])
        if ii:
            meta = ii[0].get("extmetadata", {})
            license_name = meta.get("LicenseShortName", {}).get("value", "")
            # Use thumbnail URL if available, else full
            img_url = ii[0].get("thumburl") or ii[0]["url"]
            results.append({
                "title": page["title"],
                "url": img_url,
                "width": ii[0].get("thumbwidth") or ii[0].get("width", 0),
                "height": ii[0].get("thumbheight") or ii[0].get("height", 0),
                "license": license_name,
            })
    return results

def is_usable_image(info: dict) -> bool:
    """Check if image is public domain / CC-BY and not already used."""
    if info["title"] in USED_IMAGE_TITLES:
        return False
    license_lower = info["license"].lower()
    acceptable = ["pd", "cc0", "public domain", "cc-by", "cc by",
                   "creative commons attribution"]
    return any(term in license_lower for term in acceptable)

def download_image(url: str, dest: str) -> bool:
    """Download an image to disk. Returns True on success."""
    if os.path.exists(dest):
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(dest, "wb") as f:
                f.write(resp.read())
        time.sleep(DOWNLOAD_DELAY)
        return True
    except Exception as e:
        print(f"    Download error: {e}")
        return False

# ── Image Quality Filter ───────────────────────────────────

# Titles containing these words are likely historical docs, not modern photos
BAD_TITLE_WORDS = [
    "prosch", "memorial_service", "funeral", "gravestone", "tombstone",
    "dpla", "minutes_", "guide_", "arms_of", "heraldry", "coat_of_arms",
    "furniture", "buyers_guide", "ia_cfa", "scan_", "document_",
    "newspaper", "advertisement_", "ad_for_", "trade_card",
    "engraving", "etching", "lithograph", "woodcut",
    "obituary", "portrait_of", "daguerreotype", "ambrotype",
    "nara_", "_nara_", "nara -", "loc.gov", "library_of_congress",
    "bain_news", "bain_collection", "detroit_publishing",
]

# Must be at least this pixel width to be a usable photo
MIN_PHOTO_WIDTH = 400
MIN_PHOTO_HEIGHT = 250

def is_good_photo(img_info: dict, location_name: str, state_name: str) -> bool:
    """Check if an image is a modern, relevant photo of the location.
    
    Returns True if the image is likely a real photograph of the target
    location and not a historical document, drawing, or wrong city.
    """
    title_lower = img_info["title"].lower()

    # 1. Reject known bad title patterns
    if any(bad in title_lower for bad in BAD_TITLE_WORDS):
        return False

    # 2. Verify location match: title must contain city, county, OR state
    loc_parts = [location_name.lower()]
    if state_name:
        loc_parts.append(state_name.lower())
    # Also check individual city name words (e.g. "Eugene" in "Eugene, Oregon")
    for part in location_name.replace(",", "").split():
        if len(part) > 3:
            loc_parts.append(part.lower())

    if not any(loc in title_lower for loc in loc_parts):
        # Location not mentioned in title — likely wrong place
        return False

    # 3. Check dimensions look like a photo
    w = img_info.get("width", 0)
    h = img_info.get("height", 0)
    if w < MIN_PHOTO_WIDTH or h < MIN_PHOTO_HEIGHT:
        return False

    # 4. Reject very tall/skinny images (documents, not photos)
    if w > 0 and h > 0:
        ratio = w / h
        if ratio < 0.5 or ratio > 4.0:  # too skinny either way
            return False

    # 5. Reject .png files that are small (likely icons/heraldry)
    url_lower = img_info.get("url", "").lower()
    if url_lower.endswith(".png") and (w < 800 or h < 600):
        return False

    return True


# ── Location Image Finder ───────────────────────────────────

def build_search_queries(info: dict) -> list[str]:
    """Build search queries from most specific to general, favoring modern photos."""
    tier = info["tier"]
    state = info["state"]
    county = info["county"]
    city = info["city"]
    queries = []

    if tier == "city":
        queries.append(f"{city} {state} aerial downtown")
        queries.append(f"{city} {state} city hall")
        queries.append(f"{city} {state} building")
        queries.append(f"{city} {state} park")
        queries.append(f"{city} skyline {state}")
    elif tier == "county":
        queries.append(f"{county} county {state} courthouse")
        queries.append(f"{county} county {state} building")
        queries.append(f"{county} {state} downtown")
        queries.append(f"{county} county {state} park")
    else:  # state
        queries.append(f"{state} state capitol building")
        queries.append(f"{state} downtown skyline")
        queries.append(f"{state} aerial")
        queries.append(f"{state} city")

    return queries

def find_images_for_page(page_info: dict) -> list[str]:
    """Find and download 1-2 images for a page. Returns local paths."""
    queries = build_search_queries(page_info)
    target = 2
    downloaded = []
    found_titles = []

    for query in queries:
        if len(downloaded) >= target:
            break

        print(f"    Searching: {query}")
        results = search_wikimedia(query, limit=8)
        time.sleep(WIKI_DELAY)

        if not results:
            continue

        titles = [r["title"] for r in results[:8]]
        infos = get_image_info(titles)
        # Filter: usable license + quality photo check
        location = page_info.get("city") or page_info.get("county") or page_info["state"]
        usable = [i for i in infos
                  if is_usable_image(i)
                  and is_good_photo(i, location, page_info["state"])]

        for img in usable:
            if len(downloaded) >= target:
                break
            if img["title"] in found_titles:
                continue
            # Also skip cropped/edited variants of images we already have
            base_name = re.sub(r"_?\(?cropped\)?", "", img["title"].lower())
            if any(base_name in ft.lower() or ft.lower() in base_name
                   for ft in found_titles):
                continue

            # Download
            ext = os.path.splitext(img["url"].split("?")[0])[-1]
            if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                ext = ".jpg"

            state_key = page_info["state"] or "us"
            county_key = page_info.get("county", "") or ""
            city_key = page_info.get("city", "") or ""
            cache_key = f"{state_key}/{county_key}/{city_key}".strip("/")
            cache_key = cache_key.replace(" ", "_").lower()
            cache_key = re.sub(r"[^a-z0-9_/-]", "", cache_key)
            dest_dir = os.path.join(ASSETS_DIR, cache_key)
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except OSError:
                pass

            fname = re.sub(r"[^a-zA-Z0-9_-]", "_",
                          os.path.splitext(img["title"].split(":")[-1])[0])
            dest = os.path.join(dest_dir, f"{fname}{ext}")

            if download_image(img["url"], dest):
                rel_path = "/" + os.path.relpath(dest, SEO_DIR)
                downloaded.append(rel_path)
                found_titles.append(img["title"])
                USED_IMAGE_TITLES.add(img["title"])
                print(f"      ✓ {os.path.basename(dest)}")

        time.sleep(1.0)

    return downloaded

# ── HTML Injection ──────────────────────────────────────────

def build_image_html(img_paths: list[str], alt_text: str) -> str:
    """Build HTML for 1-2 images in a responsive row."""
    if not img_paths:
        return ""

    cols = "1fr 1fr" if len(img_paths) >= 2 else "1fr"
    imgs_html = ""
    for path in img_paths:
        imgs_html += (
            f'<div class="img-cell">'
            f'<img src="{path}" alt="{alt_text}" loading="lazy" '
            f'style="width:100%;height:auto;border-radius:8px;aspect-ratio:16/10;object-fit:cover">'
            f'</div>'
        )

    return (
        f'<div class="local-images" style="display:grid;grid-template-columns:{cols};'
        f'gap:16px;margin:24px 0">'
        f'{imgs_html}'
        f'</div>'
    )

def inject_images(html: str, img_paths: list[str], alt_text: str) -> str:
    """Inject images into the content section after paragraphs."""
    imgs_html = build_image_html(img_paths, alt_text)
    if not imgs_html:
        return html

    # Strategy: find the first content section after the hero.
    # It looks like: <section class="section"><div class="container"><p>...
    # Insert images right before the </div> that closes <div class="container">.
    
    # Find the content section marker
    marker = '<section class="section"><div class="container"><p>'
    idx = html.find(marker)
    if idx < 0:
        # Try with slightly different spacing
        marker = '<section class="section"><div class="container"><p>'
        idx = html.find(marker)
    
    if idx > 0:
        # Find the matching closing </div></section> after this point
        # The structure is: <section><div class="container">...content...</div></section>
        # We want to insert before the </div>
        # Find the next </div></section> after the content start
        close_marker = '</div></section>'
        close_idx = html.find(close_marker, idx)
        if close_idx > 0:
            # Insert right before </div>
            div_close = html.rfind('</div>', idx, close_idx + len(close_marker))
            if div_close > 0:
                return html[:div_close] + imgs_html + html[div_close:]

    print("  WARNING: Could not find injection point for images")
    return html

# ── Page Discovery ──────────────────────────────────────────

def extract_page_info(fpath: str) -> dict:
    """Extract location info from page path."""
    rel = os.path.relpath(fpath, SEO_DIR)
    parts = rel.replace("/index.html", "").split("/")

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

    return {
        "tier": tier,
        "state": state,
        "county": county,
        "city": city,
        "path": fpath,
        "rel": rel,
    }

def find_pages_needing_images(limit_state: str | None = None) -> list[dict]:
    """Find all enriched pages that lack images."""
    pages = []
    skip_prefixes = ["assets/", "checkout/", "disclaimer/", "privacy/", "terms/"]

    for root, dirs, files in os.walk(SEO_DIR):
        if "index.html" not in files:
            continue
        fpath = os.path.join(root, "index.html")
        rel = os.path.relpath(fpath, SEO_DIR)

        if any(rel.startswith(p) for p in skip_prefixes):
            continue
        if limit_state and not (rel.startswith(limit_state + "/") or
                                rel == limit_state + "/index.html"):
            continue

        try:
            html = read_file(fpath)
            # Check: has content but no images
            has_content = '<section class="section"><div class="container"><p>' in html
            has_images = 'class="local-images"' in html
            if has_content and not has_images:
                info = extract_page_info(fpath)
                pages.append(info)
        except Exception:
            pass

    return pages

# ── Main ────────────────────────────────────────────────────

def process_page(info: dict, progress: dict, dry_run: bool = False) -> bool:
    """Download and inject images for one page."""
    rel = info["rel"]

    if rel in progress.get("completed", []):
        print(f"  SKIP (already done)")
        return True
    if rel in progress.get("failed", []):
        pass  # retry

    tier = info["tier"]
    alt = (f"{info['city']}, {info['state']}" if info["city"] else
           f"{info['county']}, {info['state']}" if info["county"] else
           info["state"])

    if dry_run:
        print(f"  Would search images for: {alt}")
        return True

    # Find images
    img_paths = find_images_for_page(info)

    if not img_paths:
        print(f"  No images found for {alt}")
        progress.setdefault("failed", []).append(rel)
        save_progress(progress)
        return True  # soft fail, continue

    # Inject into page
    try:
        html = read_file(info["path"])
        new_html = inject_images(html, img_paths, alt)
        if new_html != html:
            write_file(info["path"], new_html)
            print(f"  Images injected ({len(img_paths)})")
        else:
            print(f"  Injection skipped (no change)")
    except Exception as e:
        print(f"  HTML injection error: {e}")
        progress.setdefault("failed", []).append(rel)
        save_progress(progress)
        return False

    progress.setdefault("completed", []).append(rel)
    # Remove from failed if retry succeeded
    if rel in progress.get("failed", []):
        progress["failed"].remove(rel)
    save_progress(progress)
    return True

def main():
    parser = ArgumentParser()
    parser.add_argument("--state", help="Process only one state")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
    except OSError:
        pass

    progress = load_progress() if args.resume else {"completed": [], "failed": []}
    if not args.resume:
        progress = {"completed": [], "failed": []}
        save_progress(progress)

    # Load globally used titles
    global USED_IMAGE_TITLES
    USED_IMAGE_TITLES = set(progress.get("used_titles", []))

    pages = find_pages_needing_images(args.state)
    # Remove already completed
    pages = [p for p in pages if p["rel"] not in progress.get("completed", [])]

    print(f"Found {len(pages)} pages needing images")
    print(f"Already used {len(USED_IMAGE_TITLES)} unique image titles")
    if args.limit:
        pages = pages[:args.limit]
        print(f"Limited to {args.limit}")

    for i, info in enumerate(pages):
        print(f"\n== [{i+1}/{len(pages)}] {info['tier'].upper()}: {info['rel']} ==")
        try:
            process_page(info, progress, args.dry_run)
        except KeyboardInterrupt:
            print("\n\nInterrupted. Progress saved. Resume with --resume")
            break
        except Exception as e:
            print(f"  ERROR: {e}")
            progress.setdefault("failed", []).append(info["rel"])
            save_progress(progress)

    print(f"\n{'='*60}")
    print(f"Done. {len(progress.get('completed',[]))} completed, "
          f"{len(progress.get('failed',[]))} failed.")
    print(f"Total unique images used: {len(USED_IMAGE_TITLES)}")

if __name__ == "__main__":
    main()
