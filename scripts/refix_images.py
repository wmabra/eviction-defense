#!/usr/bin/env python3
"""
Re-backfill images for problem pages flagged in QA review.
Better Wikimedia search queries to avoid document scans/book covers.
"""
import os, sys, json, time, re, hashlib, shutil
import urllib.request, urllib.parse, urllib.error
from pathlib import Path

SEO_DIR = "/opt/eviction-defense/seo"
ASSETS_DIR = os.path.join(SEO_DIR, "assets", "locations")
UA = "evictions.help/1.0 (https://evictions.help; support@evictions.help)"
WIKI_DELAY = 3.0
DOWNLOAD_DELAY = 1.5
THUMB_WIDTH = 800
BACKUP_DIR = "/opt/eviction-defense/seo_backup_fix"

PROBLEM_URLS = """
https://evictions.help/south-carolina/spartanburg-county/
https://evictions.help/south-carolina/lexington-county/
https://evictions.help/south-carolina/berkeley-county/
https://evictions.help/south-carolina/anderson-county/
https://evictions.help/south-carolina/dorchester-county/
https://evictions.help/south-carolina/florence-county/
https://evictions.help/south-carolina/pickens-county/
https://evictions.help/south-carolina/lancaster-county/
https://evictions.help/south-carolina/cherokee-county/
https://evictions.help/south-carolina/chester-county/
https://evictions.help/south-carolina/clarendon-county/
https://evictions.help/south-carolina/williamsburg-county/
https://evictions.help/south-carolina/edgefield-county/
https://evictions.help/south-carolina/marion-county/
https://evictions.help/south-carolina/dillon-county/
https://evictions.help/south-carolina/union-county/
https://evictions.help/south-carolina/fairfield-county/
https://evictions.help/south-carolina/saluda-county/
https://evictions.help/south-carolina/mccormick-county/
https://evictions.help/south-carolina/charleston-county/mount-pleasant/
https://evictions.help/south-carolina/york-county/rock-hill/
https://evictions.help/south-carolina/dorchester-county/summerville/
https://evictions.help/south-carolina/berkeley-county/goose-creek/
https://evictions.help/south-carolina/greenville-county/greer/
https://evictions.help/south-carolina/florence-county/florence/
https://evictions.help/south-carolina/horry-county/myrtle-beach/
https://evictions.help/south-carolina/spartanburg-county/spartanburg/
https://evictions.help/south-carolina/beaufort-county/hilton-head-island/
https://evictions.help/south-carolina/york-county/fort-mill/
https://evictions.help/south-carolina/beaufort-county/bluffton/
https://evictions.help/south-carolina/aiken-county/aiken/
https://evictions.help/south-carolina/greenville-county/mauldin/
https://evictions.help/south-carolina/horry-county/conway/
https://evictions.help/tennessee/carroll-county/
https://evictions.help/tennessee/henderson-county/
https://evictions.help/tennessee/hardin-county/
https://evictions.help/tennessee/macon-county/
https://evictions.help/tennessee/mcnairy-county/
https://evictions.help/tennessee/hardeman-county/
https://evictions.help/tennessee/lauderdale-county/
https://evictions.help/tennessee/dekalb-county/
https://evictions.help/tennessee/humphreys-county/
https://evictions.help/tennessee/polk-county/
https://evictions.help/tennessee/chester-county/
https://evictions.help/tennessee/unicoi-county/
https://evictions.help/tennessee/sequatchie-county/
https://evictions.help/tennessee/haywood-county/
https://evictions.help/tennessee/bledsoe-county/
https://evictions.help/tennessee/stewart-county/
https://evictions.help/tennessee/crockett-county/
https://evictions.help/tennessee/trousdale-county/
https://evictions.help/tennessee/perry-county/
https://evictions.help/tennessee/clay-county/
https://evictions.help/tennessee/pickett-county/
https://evictions.help/tennessee/tipton-county/
https://evictions.help/tennessee/loudon-county/
https://evictions.help/tennessee/dickson-county/
https://evictions.help/tennessee/carter-county/
https://evictions.help/tennessee/bedford-county/
https://evictions.help/tennessee/gibson-county/
https://evictions.help/tennessee/monroe-county/
https://evictions.help/tennessee/lawrence-county/
https://evictions.help/tennessee/cheatham-county/
https://evictions.help/tennessee/marshall-county/
https://evictions.help/tennessee/lincoln-county/
https://evictions.help/tennessee/dyer-county/
https://evictions.help/tennessee/rhea-county/
https://evictions.help/tennessee/weakley-county/
https://evictions.help/tennessee/claiborne-county/
https://evictions.help/tennessee/giles-county/
https://evictions.help/tennessee/obion-county/
https://evictions.help/tennessee/marion-county/
https://evictions.help/tennessee/greene-county/
https://evictions.help/tennessee/knox-county/
https://evictions.help/tennessee/hamilton-county/
https://evictions.help/tennessee/williamson-county/
https://evictions.help/tennessee/montgomery-county/
https://evictions.help/tennessee/sumner-county/
https://evictions.help/tennessee/sullivan-county/
https://evictions.help/tennessee/blount-county/
https://evictions.help/tennessee/putnam-county/
https://evictions.help/tennessee/shelby-county/memphis/
https://evictions.help/tennessee/montgomery-county/clarksville/
https://evictions.help/tennessee/rutherford-county/murfreesboro/
https://evictions.help/tennessee/williamson-county/franklin/
https://evictions.help/tennessee/washington-county/johnson-city/
https://evictions.help/tennessee/madison-county/jackson/
https://evictions.help/tennessee/sumner-county/hendersonville/
https://evictions.help/tennessee/rutherford-county/smyrna/
https://evictions.help/tennessee/sullivan-county/kingsport/
https://evictions.help/tennessee/shelby-county/bartlett/
https://evictions.help/tennessee/shelby-county/collierville/
https://evictions.help/tennessee/wilson-county/lebanon/
https://evictions.help/tennessee/maury-county/columbia/
https://evictions.help/tennessee/williamson-county/brentwood/
https://evictions.help/texas/bexar-county/
https://evictions.help/texas/tarrant-county/fort-worth/
https://evictions.help/texas/el-paso-county/el-paso/
https://evictions.help/texas/nueces-county/corpus-christi/
https://evictions.help/texas/collin-county/plano/
https://evictions.help/texas/lubbock-county/lubbock/
https://evictions.help/texas/dallas-county/irving/
https://evictions.help/texas/dallas-county/garland/
https://evictions.help/texas/collin-county/frisco/
https://evictions.help/texas/cameron-county/brownsville/
""".strip()

def wiki_request(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def search_images(query: str, count: int = 6) -> list:
    """Search Wikimedia for images matching query."""
    params = urllib.parse.urlencode({
        "action": "query", "list": "search",
        "srsearch": query, "srnamespace": "6",
        "srlimit": count, "sroffset": 0,
        "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    try:
        data = wiki_request(url)
        return [hit["title"] for hit in data.get("query", {}).get("search", [])]
    except Exception as e:
        print(f"  Search failed: {e}")
        return []

def get_best_image_urls(titles: list, exclude_titles: set|None = None) -> list:
    """Get thumbnail URLs for image titles, filter out SVG/PDF/doc."""
    if exclude_titles is None:
        exclude_titles = set()  # type: ignore[assignment]
    
    results = []
    for title in titles:
        if title in exclude_titles:
            continue
        # Skip non-photo types
        lower = title.lower()
        if any(lower.endswith(x) for x in ('.svg', '.pdf', '.ogg', '.ogv', '.webm')):
            continue
        # Skip document/book covers
        bad_words = ['history of', 'watershed', 'environmental impact', 'biographical',
                     'embracing an account', 'IA_history', 'IA_CAT', '_IA_', 'cover of']
        if any(w in lower for w in bad_words):
            continue
        
        params = urllib.parse.urlencode({
            "action": "query", "titles": title,
            "prop": "imageinfo", "iiprop": "url",
            "iiurlwidth": THUMB_WIDTH, "format": "json",
        })
        try:
            data = wiki_request(f"https://commons.wikimedia.org/w/api.php?{params}")
            for page in data.get("query", {}).get("pages", {}).values():
                ii = page.get("imageinfo", [])
                if ii:
                    url = ii[0].get("thumburl") or ii[0].get("url")
                    if url:
                        results.append((str(title), str(url)))
        except Exception:
            continue
    return results

def download_image(url, dest_path):
    """Download image to dest_path."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(r.read())
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False

def url_to_path(url):
    """Convert evictions.help URL to filesystem path."""
    path = url.replace("https://evictions.help/", "").strip("/")
    return os.path.join(SEO_DIR, path)

def get_asset_dir(url):
    """Get the assets/locations directory path for this URL."""
    # e.g. evictions.help/south-carolina/anderson-county/ -> assets/locations/south_carolina/anderson
    path = url.replace("https://evictions.help/", "").strip("/").rstrip("/")
    parts = path.split("/")
    # Convert to asset path format
    state = parts[0].replace("-", "_")
    if len(parts) == 2:
        # County page: south-carolina/anderson-county -> south_carolina/anderson
        county = parts[1].replace("-county", "").replace("-", "_")
        return os.path.join(ASSETS_DIR, state, county)
    elif len(parts) == 3:
        # City page: south-carolina/anderson-county/city -> south_carolina/anderson/city
        county = parts[1].replace("-county", "").replace("-", "_")
        city = parts[2].replace("-", "_")
        return os.path.join(ASSETS_DIR, state, county, city)
    return None

def get_search_query(url):
    """Build a good search query for Wikimedia."""
    path = url.replace("https://evictions.help/", "").strip("/").rstrip("/")
    parts = path.split("/")
    state_map = {
        'south-carolina': 'South Carolina', 'tennessee': 'Tennessee', 'texas': 'Texas',
        'florida': 'Florida', 'california': 'California', 'arizona': 'Arizona',
        'arkansas': 'Arkansas', 'colorado': 'Colorado', 'connecticut': 'Connecticut',
        'georgia': 'Georgia', 'illinois': 'Illinois', 'louisiana': 'Louisiana',
        'massachusetts': 'Massachusetts', 'michigan': 'Michigan', 'minnesota': 'Minnesota',
        'nevada': 'Nevada', 'new-mexico': 'New Mexico', 'oregon': 'Oregon',
        'rhode-island': 'Rhode Island', 'virginia': 'Virginia',
    }
    state = state_map.get(parts[0], parts[0].replace("-", " ").title())
    
    if len(parts) == 2:
        # County
        county_name = parts[1].replace("-county", "").replace("-", " ").title()
        return f'"{county_name}" "{state}" courthouse OR downtown'
    elif len(parts) == 3:
        # City
        city_name = parts[2].replace("-", " ").title()
        return f'"{city_name}" "{state}" courthouse OR downtown OR aerial'
    return ""

def backup_html(fpath):
    """Backup HTML file before modifying."""
    rel = os.path.relpath(fpath, SEO_DIR)
    dest = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        shutil.copy2(fpath, dest)

def clear_old_images(asset_dir):
    """Remove old images from asset directory."""
    if not asset_dir or not os.path.exists(asset_dir):
        return
    try:
        for f in os.listdir(asset_dir):
            fpath = os.path.join(asset_dir, f)
            if os.path.isfile(fpath) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                os.remove(fpath)
    except OSError:
        pass

def get_existing_image_filenames(html_path):
    """Get list of image filenames currently in the HTML."""
    try:
        html = open(html_path).read()
        return re.findall(r'/assets/locations/([^"]+)', html)
    except Exception:
        return []

def update_html_images(html_path, new_image_paths):
    """Replace img src attributes in HTML with new images."""
    try:
        html = open(html_path).read()
    except OSError:
        print(f"  Cannot read HTML")
        return False
    
    existing = get_existing_image_filenames(html_path)
    
    if len(existing) < 2:
        print(f"  WARNING: only {len(existing)} img tags found in HTML")
        return False
    
    modified = html
    replaced = 0
    
    # Use exact img tag replacement within the local-images section
    for old_path in existing:
        if replaced >= len(new_image_paths):
            # Remove excess img tags (duplicates) - replace with empty
            old_full = f'/assets/locations/{old_path}'
            pattern = re.compile(
                r'<img src="' + re.escape(old_full) + r'"[^>]*>',
                re.IGNORECASE
            )
            if pattern.search(modified) and replaced >= len(existing) - (len(existing) - len(new_image_paths)):
                continue
        if replaced >= len(new_image_paths):
            break
        new_path = new_image_paths[replaced]
        old_full = f'/assets/locations/{old_path}'
        new_full = f'/assets/locations/{new_path}'
        if old_full in modified:
            modified = modified.replace(old_full, new_full, 1)
            replaced += 1
    
    # Update alt text only for location images
    url_parts = html_path.replace(SEO_DIR, "").strip("/").split("/")
    if len(url_parts) >= 2:
        if len(url_parts) == 2:
            loc_name = url_parts[1].replace("-county", "").replace("-", " ").title()
        else:
            loc_name = url_parts[-1].replace("-", " ").title()
        state = url_parts[0].replace("-", " ").title()
        new_alt = f"{loc_name}, {state}"
        # Only replace alt in location images, not logo
        for new_path in new_image_paths:
            new_full = f'/assets/locations/{new_path}'
            modified = modified.replace(
                f'src="{new_full}" alt="[^"]*"',
                f'src="{new_full}" alt="{new_alt}"'
            )
    
    if modified != html:
        try:
            os.makedirs(os.path.dirname(os.path.join(BACKUP_DIR, "x")), exist_ok=True)
            if os.path.exists(html_path):
                backup_html(html_path)
            with open(html_path, "w") as f:
                f.write(modified)
        except OSError as e:
            print(f"  Write failed: {e}")
            return False
        return True
    return False


def main():
    urls = [u.strip() for u in PROBLEM_URLS.split("\n") if u.strip()]
    print(f"Processing {len(urls)} problem pages...\n")
    
    success = 0
    skipped = 0
    failed = []
    
    for i, url in enumerate(urls):
        html_path = os.path.join(url_to_path(url), "index.html")
        asset_dir = get_asset_dir(url)
        if not asset_dir:
            print(f"[{i+1}/{len(urls)}] SKIP: {url} (bad path)")
            skipped += 1
            continue
        
        if not os.path.exists(html_path):
            print(f"[{i+1}/{len(urls)}] SKIP: {url} (no HTML)")
            skipped += 1
            continue
        
        print(f"[{i+1}/{len(urls)}] {url}")
        
        # Build search query
        query = get_search_query(url)
        print(f"  Searching: {query}")
        
        # Search for images
        titles = search_images(query, count=8)
        if len(titles) < 2:
            # Fallback: broader search
            print(f"  Only {len(titles)} results, trying broader search...")
            path = url.replace("https://evictions.help/", "").strip("/").rstrip("/")
            parts = path.split("/")
            if len(parts) >= 2:
                loc = parts[-1].replace("-county", "").replace("-", " ").title()
                titles2 = search_images(f'"{loc}" courthouse', count=4)
                titles.extend(titles2)
        
        time.sleep(WIKI_DELAY)
        
        # Get image URLs
        image_results = get_best_image_urls(titles)
        
        if len(image_results) < 2:
            print(f"  FAILED: only {len(image_results)} usable images found")
            failed.append((url, f"only {len(image_results)} images"))
            continue
        
        # Take the best 2
        selected = image_results[:2]
        print(f"  Found {len(selected)} images:")
        for title, img_url in selected:
            print(f"    - {title}")
        
        # Clear old images
        clear_old_images(asset_dir)
        
        # Download new images
        new_paths = []
        for title, img_url in selected:
            ext = os.path.splitext(title)[1] or ".jpg"
            safe_name = str(title).replace("File:", "").replace(" ", "_")[:100] + ext
            if not asset_dir:
                continue
            dest = os.path.join(str(asset_dir), safe_name)
            
            if download_image(img_url, dest):
                # Build relative path for HTML (relative to assets/locations/)
                rel_path = os.path.relpath(dest, ASSETS_DIR)
                new_paths.append(rel_path)
                time.sleep(DOWNLOAD_DELAY)
            else:
                print(f"  Failed to download: {title}")
        
        if len(new_paths) < 2:
            print(f"  FAILED: only downloaded {len(new_paths)} images")
            failed.append((url, f"only downloaded {len(new_paths)}"))
            continue
        
        # Update HTML
        if update_html_images(html_path, new_paths):
            print(f"  ✅ Updated HTML with {len(new_paths)} new images")
            success += 1
        else:
            print(f"  FAILED: could not update HTML")
            failed.append((url, "HTML update failed"))
    
    print(f"\n{'='*60}")
    print(f"DONE. {success} succeeded, {skipped} skipped, {len(failed)} failed.")
    if failed:
        print("\nFailed pages:")
        for url, reason in failed:
            print(f"  {url} — {reason}")


if __name__ == "__main__":
    main()
